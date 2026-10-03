"""7. Retrieval strategy -- hybrid retrieval.

Three channels are queried independently, then fused:

1. **Semantic**  -- embedding cosine similarity over the whole corpus.
2. **Keyword**   -- Okapi BM25 over passage text and metadata.
3. **Metadata**  -- explicit parva / character / theme matching (used both as
   a filter for the other two channels and, when they come back thin, as a
   fallback so the pipeline never answers with nothing by accident).

Fusion uses a weighted sum of channel scores (each channel is already
normalised to 0..1) -- a simple, explainable alternative to Reciprocal Rank
Fusion that keeps the "retrieval_debug" payload honest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import Passage, Source
from ..embeddings import get_embedder
from ..index import get_keyword_index
from ..schemas import EvidencePassage
from ..vectorstore import get_vector_store
from .expansion import ExpandedQuery

W_SEMANTIC = 0.55
W_KEYWORD = 0.35
W_METADATA = 0.10


@dataclass
class PassageMeta:
    id: str
    source_id: str
    parva: str
    section: str
    chapter: str | None
    verse_range: str
    speaker: str
    listener: str
    characters: list[str]
    events: list[str]
    themes: list[str]
    keywords: list[str]
    original_text: str
    translation: str
    summary: str
    text_type: str
    source_reference: str
    is_primary_text: bool
    verification_status: str
    source_title: str

    def blob(self) -> str:
        return " ".join(
            [
                self.parva, self.section, self.chapter or "", self.verse_range,
                self.speaker, self.listener, " ".join(self.characters),
                " ".join(self.themes), " ".join(self.keywords),
                " ".join(self.events), self.source_reference,
                self.summary, self.translation, self.original_text,
            ]
        ).lower()


@dataclass
class RetrievalResult:
    passages: list[EvidencePassage] = field(default_factory=list)
    debug: dict = field(default_factory=dict)


class HybridRetriever:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory
        self._meta: dict[str, PassageMeta] | None = None
        self._order: list[str] = []

    # ------------------------------------------------------------------ #
    def invalidate(self) -> None:
        self._meta = None
        get_keyword_index().invalidate()

    def _load(self) -> dict[str, PassageMeta]:
        if self._meta is not None:
            return self._meta
        db: Session = self._session_factory()
        try:
            rows = db.query(Passage, Source).join(Source, Passage.source_id == Source.id).all()
        finally:
            db.close()
        meta: dict[str, PassageMeta] = {}
        order: list[str] = []
        for p, s in rows:
            meta[p.id] = PassageMeta(
                id=p.id,
                source_id=p.source_id,
                parva=p.parva,
                section=p.section,
                chapter=p.chapter,
                verse_range=p.verse_range,
                speaker=p.speaker,
                listener=p.listener,
                characters=list(p.characters or []),
                events=list(p.events or []),
                themes=list(p.themes or []),
                keywords=list(p.keywords or []),
                original_text=p.original_text,
                translation=p.translation,
                summary=p.summary,
                text_type=p.text_type,
                source_reference=p.source_reference,
                is_primary_text=p.is_primary_text,
                verification_status=p.verification_status,
                source_title=s.title,
            )
            order.append(p.id)
        self._meta = meta
        self._order = order
        get_keyword_index().load(self._session_factory)
        return meta

    # ------------------------------------------------------------------ #
    def _metadata_matches(self, meta: PassageMeta, q: ExpandedQuery) -> float:
        score = 0.0
        if q.theme_filters:
            hits = len(set(q.theme_filters) & set(meta.themes))
            score += 0.6 * hits / len(q.theme_filters)
        if q.character_filters:
            low_chars = {c.lower() for c in meta.characters} | {
                (meta.speaker or "").lower(), (meta.listener or "").lower()
            }
            hits = sum(1 for c in q.character_filters if c.lower() in low_chars)
            score += 0.3 * hits / len(q.character_filters)
        if q.parva_hint and q.parva_hint.lower() in meta.parva.lower():
            score += 0.1
        return min(score, 1.0)

    def _allowed_ids(self, meta: dict[str, PassageMeta], q: ExpandedQuery) -> set[str] | None:
        """Metadata filter. Only applied when it does not empty the corpus."""
        if not (q.theme_filters or q.character_filters):
            return None
        keep: set[str] = set()
        for pid, m in meta.items():
            if self._metadata_matches(m, q) > 0:
                keep.add(pid)
        return keep if len(keep) >= max(3, int(0.05 * len(meta))) else None

    # ------------------------------------------------------------------ #
    def retrieve(self, query: str, expanded: ExpandedQuery) -> RetrievalResult:
        meta = self._load()
        if not meta:
            return RetrievalResult(debug={"corpus_size": 0, "note": "empty corpus"})

        allowed = self._allowed_ids(meta, expanded)

        # --- semantic channel -------------------------------------------- #
        semantic: list[tuple[str, float]] = []
        embedder = get_embedder()
        try:
            vec = embedder.embed_query(expanded.semantic_query or query)
            semantic = get_vector_store().search(
                vec, settings.retrieval_candidates, allowed_ids=allowed
            )
        except Exception as exc:  # pragma: no cover - provider outage
            semantic = []
            semantic_error = f"{type(exc).__name__}: {exc}"
        else:
            semantic_error = ""
        semantic = [(p, s) for p, s in semantic if s >= settings.min_semantic_score]

        # --- keyword channel --------------------------------------------- #
        terms = list(dict.fromkeys([*expanded.lexical_terms, *expanded.entity_terms]))
        keyword = get_keyword_index().search(
            terms, settings.retrieval_candidates, allowed_ids=allowed
        )

        # --- metadata channel -------------------------------------------- #
        metadata_scores: list[tuple[str, float]] = []
        for pid, m in meta.items():
            if allowed is not None and pid not in allowed:
                continue
            s = self._metadata_matches(m, expanded)
            if s > 0:
                metadata_scores.append((pid, s))
        metadata_scores.sort(key=lambda t: -t[1])
        metadata_scores = metadata_scores[: settings.retrieval_candidates]

        # --- fuse --------------------------------------------------------- #
        sem_d = dict(semantic)
        key_d = dict(keyword)
        meta_d = dict(metadata_scores)
        all_ids = set(sem_d) | set(key_d) | set(meta_d)

        fused: list[tuple[str, float, dict]] = []
        for pid in all_ids:
            parts = {
                "semantic": sem_d.get(pid, 0.0),
                "keyword": key_d.get(pid, 0.0),
                "metadata": meta_d.get(pid, 0.0),
            }
            score = (
                W_SEMANTIC * parts["semantic"]
                + W_KEYWORD * parts["keyword"]
                + W_METADATA * parts["metadata"]
            )
            channels = [name for name, v in parts.items() if v > 0]
            fused.append((pid, score, {**parts, "channel": "+".join(channels) or "none"}))

        fused.sort(key=lambda t: -t[1])
        fused = fused[: settings.retrieval_top_k * 2]

        passages: list[EvidencePassage] = []
        for pid, score, parts in fused:
            m = meta[pid]
            passages.append(
                EvidencePassage(
                    id=pid,
                    parva=m.parva,
                    section=m.section,
                    chapter=m.chapter,
                    reference=m.source_reference,
                    speaker=m.speaker,
                    listener=m.listener,
                    characters=m.characters,
                    themes=m.themes,
                    context=m.summary,
                    quote=m.translation or m.original_text,
                    summary=m.summary,
                    original_text=m.original_text,
                    text_type=m.text_type,
                    source_title=m.source_title,
                    verification_status=m.verification_status,
                    is_primary_text=m.is_primary_text,
                    relevance=round(score, 4),
                    semantic_score=round(parts["semantic"], 4),
                    keyword_score=round(parts["keyword"], 4),
                    source=parts["channel"],
                )
            )

        debug = {
            "corpus_size": len(meta),
            "filter_applied": allowed is not None,
            "filtered_pool": len(allowed) if allowed is not None else len(meta),
            "semantic_hits": len(semantic),
            "keyword_hits": len(keyword),
            "metadata_hits": len(metadata_scores),
            "fused": len(all_ids),
            "returned": len(passages),
            "filter_themes": expanded.theme_filters,
            "filter_characters": expanded.character_filters,
        }
        if semantic_error:
            debug["semantic_error"] = semantic_error
        return RetrievalResult(passages=passages, debug=debug)
