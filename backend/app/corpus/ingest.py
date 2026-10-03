"""Corpus ingestion.

Reads the structured corpus (``backend/data/corpus/*.json``), upserts sources,
passages, characters and themes, builds embeddings and refreshes the keyword
index.

Design notes
------------
* Content is de-duplicated with ``sha256(source_reference + text)`` so a re-run
  is idempotent and an edited passage is recognised as new.
* Ingestion never silently overwrites a **verified** passage: a changed
  verified passage is re-marked ``unverified`` so a human re-checks it
  (§19 — "mark passages as verified" is an explicit human act).
* ``embeddings`` are rebuilt for new/changed passages only; a full rebuild is
  available through :func:`rebuild_embeddings`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from ..db.models import Character, Embedding, Passage, PassageTheme, Source, Theme, new_id, utcnow
from ..embeddings import get_embedder
from ..index import get_keyword_index
from ..knowledge.taxonomy import CHARACTERS, THEMES
from ..rag.pipeline import get_pipeline
from ..rag.taxonomy import is_canonical_parva, validate_passage_metadata
from ..vectorstore import get_vector_store

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "corpus"


def content_hash(reference: str, text: str) -> str:
    blob = (reference or "").strip() + "\u0000" + _norm_text(text)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _prose(item: dict) -> str:
    """The text portion of a passage dict, normalised."""
    return _norm_text(" ".join(
        str(item.get(k, "") or "")
        for k in ("original_text", "translation", "summary")
    ))


@dataclass
class IngestReport:
    sources_upserted: int = 0
    passages_created: int = 0
    passages_updated: int = 0
    passages_skipped: int = 0
    passages_flagged_unverified: int = 0
    validation_issues: int = 0
    issues_by_reference: dict[str, list[str]] = field(default_factory=dict)
    embeddings_built: int = 0
    themes: int = 0
    characters: int = 0
    stale_removed: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


# --------------------------------------------------------------------------- #
# Taxonomy upsert
# --------------------------------------------------------------------------- #
def upsert_taxonomy(db: Session) -> tuple[int, int]:
    tcount = 0
    for t in THEMES:
        row = db.query(Theme).filter(Theme.slug == t["slug"]).one_or_none()
        if row is None:
            db.add(Theme(slug=t["slug"], name=t["name"], kind=t["kind"],
                         description=t["description"]))
            tcount += 1
        else:
            row.name = t["name"]
            row.kind = t["kind"]
            row.description = t["description"]
    ccount = 0
    for c in CHARACTERS:
        row = db.query(Character).filter(Character.slug == c["slug"]).one_or_none()
        if row is None:
            db.add(Character(slug=c["slug"], name=c["name"], aliases=c["aliases"],
                             role=c["role"], description=c["description"],
                             primary_themes=c["primary_themes"]))
            ccount += 1
        else:
            row.name = c["name"]
            row.aliases = c["aliases"]
            row.role = c["role"]
            row.description = c["description"]
            row.primary_themes = c["primary_themes"]
    return tcount, ccount


def _default_source(db: Session) -> Source:
    src = db.query(Source).filter(Source.title == "The Mahabharata of Krishna Dwaipayana Vyasa").one_or_none()
    if src is None:
        src = Source(
            id=new_id(),
            title="The Mahabharata of Krishna Dwaipayana Vyasa",
            author="Maharishi Veda Vyasa",
            translator="Public-domain English translations and editorial summaries "
                       "(see passage-level provenance)",
            edition="Digital working corpus",
            language="en",
            source_type="primary_text",
            is_primary=True,
            notes="Seed corpus. Every passage carries a verification_status; only "
                  "passages marked 'verified' may support a strong textual claim.",
        )
        db.add(src)
        db.flush()
    return src


# --------------------------------------------------------------------------- #
# Passage upsert
# --------------------------------------------------------------------------- #
def upsert_passage(db: Session, src: Source, item: dict, report: IngestReport) -> Passage | None:
    ref = (item.get("source_reference") or "").strip()
    if not ref:
        report.errors.append(f"missing source_reference: {item.get('parva', '?')}")
        return None

    # ---------------- automated validation (Phase 2, Part 5) ------------- #
    # A passage that fails canonical validation is still ingested -- the data
    # is never silently dropped -- but it can never be ingested as `verified`.
    # It lands as `needs_review` and waits for a human.
    issues = validate_passage_metadata(item)
    if issues:
        report.validation_issues += 1
        report.issues_by_reference[ref] = issues
        if (item.get("verification_status") or "").lower() == "verified":
            item = dict(item)
            item["verification_status"] = "needs_review"
            item["verification_note"] = (
                "Automated validation flagged: " + "; ".join(issues)
            )

    text = " ".join(
        str(item.get(k, "") or "") for k in ("original_text", "translation", "summary")
    )
    ch = content_hash(ref, text)

    existing = (
        db.query(Passage)
        .filter(Passage.source_reference == ref, Passage.content_hash == ch)
        .one_or_none()
    )
    if existing is not None:
        # The hash deliberately covers reference + prose only, so a metadata
        # edit (parva/section retyped during canonicalisation) leaves the hash
        # matching while the stored provenance drifts. Sync it in place,
        # otherwise a non-canonical parva survives re-ingestion forever.
        drifted = False
        for field_name in ("section", "characters", "themes", "keywords",
                           "events", "text_type", "speaker", "listener"):
            new_val = item.get(field_name)
            if new_val is None:
                continue
            if isinstance(new_val, list):
                new_val = list(new_val)
            if getattr(existing, field_name) != new_val:
                setattr(existing, field_name, new_val)
                drifted = True
        # ``parva`` is the field that matters most for provenance: a
        # non-canonical value here would keep surfacing in retrieval.
        new_parva = (item.get("parva") or "").strip()
        if new_parva and existing.parva != new_parva:
            existing.parva = new_parva
            drifted = True
        new_chapter = str(item["chapter"]) if item.get("chapter") else None
        if existing.chapter != new_chapter:
            existing.chapter = new_chapter
            drifted = True
        if drifted:
            report.passages_updated += 1
            _sync_passage_themes(db, existing)
            existing.embedding_status = "pending"
        else:
            report.passages_skipped += 1
        return existing

    # A reference with the same id but different text => edited content.
    stale = db.query(Passage).filter(Passage.source_reference == ref).all()
    for old in stale:
        if old.verification_status == "verified":
            old.verification_status = "unverified"
            old.verification_note = (
                "Content changed after verification; re-check required."
            )
            old.verified_at = None
            report.passages_flagged_unverified += 1
        db.delete(old)

    passage = Passage(
        id=new_id(),
        source_id=src.id,
        parva=item.get("parva", ""),
        section=item.get("section", ""),
        chapter=str(item["chapter"]) if item.get("chapter") else None,
        verse_range=item.get("verse_range", ""),
        speaker=item.get("speaker", ""),
        listener=item.get("listener", ""),
        characters=list(item.get("characters", []) or []),
        events=list(item.get("events", []) or []),
        themes=list(item.get("themes", []) or []),
        keywords=list(item.get("keywords", []) or []),
        original_text=item.get("original_text", ""),
        translation=item.get("translation", ""),
        summary=item.get("summary", ""),
        text_type=item.get("text_type", "summary"),
        language=item.get("language", "en"),
        source_reference=ref,
        content_hash=ch,
        verification_status=item.get("verification_status", "unverified"),
        verification_note=item.get("verification_note", ""),
        is_primary_text=bool(item.get("is_primary_text", True)),
        embedding_status="pending",
    )
    db.add(passage)
    db.flush()
    report.passages_created += 1
    _sync_passage_themes(db, passage)
    return passage


def _sync_passage_themes(db: Session, passage: Passage) -> None:
    db.query(PassageTheme).filter(PassageTheme.passage_id == passage.id).delete()
    for slug in set(passage.themes or []):
        db.add(PassageTheme(passage_id=passage.id, theme_slug=slug))


def _embedding_text(p: Passage) -> str:
    return " ".join(
        [
            p.parva, p.section, p.chapter or "", p.verse_range,
            p.speaker, p.listener,
            " ".join(p.characters or []),
            " ".join(p.themes or []),
            " ".join(p.keywords or []),
            " ".join(p.events or []),
            p.source_reference,
            p.summary, p.translation, p.original_text,
        ]
    ).strip()


# --------------------------------------------------------------------------- #
# Embeddings
# --------------------------------------------------------------------------- #
def build_embeddings(db: Session, passage_ids: list[str] | None = None) -> int:
    embedder = get_embedder()
    store = get_vector_store()
    q = db.query(Passage)
    if passage_ids is not None:
        if not passage_ids:
            return 0
        q = q.filter(Passage.id.in_(passage_ids))
    rows = q.all()
    built = 0
    batch: list[tuple[str, list[float]]] = []
    for i in range(0, len(rows), 32):
        chunk = rows[i : i + 32]
        vectors = embedder.embed([_embedding_text(p) for p in chunk])
        for p, vec in zip(chunk, vectors):
            batch.append((p.id, vec))
            p.embedding_status = "indexed"
            built += 1
        store.upsert(batch)
        batch = []
    return built


def rebuild_embeddings(db: Session) -> int:
    store = get_vector_store()
    store.clear_provider()
    db.query(Embedding).delete()
    db.commit()
    return build_embeddings(db)


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
def ingest_corpus(path: Path | None = None, rebuild: bool = False) -> IngestReport:
    path = path or CORPUS_DIR
    report = IngestReport()
    db: Session = _session()
    try:
        upsert_taxonomy(db)
        report.themes, report.characters = len(THEMES), len(CHARACTERS)
        src = _default_source(db)

        # (section, prose) -> source_reference exactly as the corpus states it,
        # used after the loop to find rows a reference rename orphaned.
        declared: dict[tuple[str, str], str] = {}

        files: list[Path] = []
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = sorted(path.glob("**/*.json"))
        else:
            report.errors.append(f"corpus path not found: {path}")
            return report

        for fp in files:
            if fp.name == "manifest.json":
                continue
            try:
                payload = json.loads(fp.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"{fp.name}: {exc}")
                continue
            items = payload.get("passages") if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                report.errors.append(f"{fp.name}: expected a list of passages")
                continue
            per_source: dict[str, Source] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                ref = (item.get("source_reference") or "").strip()
                if ref:
                    # Record what the corpus declares, so a row left behind by
                    # a reference rename can be recognised afterwards.
                    key = ((item.get("section") or "").strip(), _prose(item))
                    declared.setdefault(key, ref)
                title = item.pop("source_title", None)
                if title:
                    s = db.query(Source).filter(Source.title == title).one_or_none()
                    if s is None:
                        s = Source(id=new_id(), title=title, source_type="primary_text",
                                   is_primary=True, language="en")
                        db.add(s)
                        db.flush()
                    per_source[title] = s
                source = per_source.get("", src)
                upsert_passage(db, source, item, report)

        report.stale_removed = _prune_stale_twins(db, declared)

        db.commit()

        # index
        if rebuild:
            report.embeddings_built = rebuild_embeddings(db)
        else:
            pending = [
                p.id for p in db.query(Passage).filter(Passage.embedding_status == "pending")
            ]
            report.embeddings_built = build_embeddings(db, pending)
        db.commit()
        get_keyword_index().invalidate()
        get_pipeline().invalidate()
        return report
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _row_prose(row: Passage) -> str:
    return _norm_text(" ".join([row.original_text or "", row.translation or "",
                                row.summary or ""]))


def _prune_stale_twins(db: Session, declared: dict[tuple[str, str], str]) -> int:
    """Remove rows orphaned by a ``source_reference`` rename.

    Renaming a reference changes the content hash, so the upsert creates a new
    row while the stale lookup -- keyed on the *new* reference -- never finds
    the pre-rename row. The old row then survives forever, duplicating the
    passage under superseded provenance (this is how "Gadra Parva" outlived
    its canonicalisation to "Sauptika Parva").

    ``declared`` maps ``(section, prose) -> source_reference`` exactly as the
    corpus now states it. A stored row is stale only when all hold:

    * the corpus declares the same section *and* prose under a **different**
      reference (so a replacement row already exists);
    * the row's own parva is not canonical -- i.e. it predates a
      canonicalisation pass rather than being a passage a human added.

    Admin-created passages are untouched: their section/prose pair is either
    absent from the corpus or carries a canonical parva.
    """
    if not declared:
        return 0

    stale = [
        row
        for row in db.query(Passage).all()
        if ((row.section or "").strip(), _row_prose(row)) in declared
        and declared[((row.section or "").strip(), _row_prose(row))]
        != row.source_reference
        and not is_canonical_parva(row.parva)
    ]
    if not stale:
        return 0

    stale_ids = [row.id for row in stale]
    # Drop embeddings on the *same* session: opening the vector store's own
    # session here would deadlock SQLite against this open write transaction.
    db.query(Embedding).filter(Embedding.passage_id.in_(stale_ids)).delete(
        synchronize_session=False
    )
    for row in stale:
        db.delete(row)
    db.flush()
    # Clears only the in-memory vector cache (no DB session), so retrieval
    # cannot keep serving embeddings for rows we just removed.
    get_vector_store().invalidate()
    return len(stale)


def _session() -> Session:
    from ..db.session import SessionLocal

    return SessionLocal()
