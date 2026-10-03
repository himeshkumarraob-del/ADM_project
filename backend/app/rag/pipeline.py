"""End-to-end RAG pipeline.

    User Query
      -> Intent / mode selection
      -> Situation extraction (6.)
      -> Query expansion
      -> Hybrid retrieval (7.)   semantic + keyword + metadata
      -> Re-ranking
      -> Evidence validation     (drops rejected sources, classifies support)
      -> LLM / template reasoning
      -> Citation verification   (ids must exist in the evidence pack)
      -> Safety notices          (17.)
      -> Structured response     (8.)

Every stage is individually testable and degrades to a deterministic
implementation when no external model is configured.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..config import settings
from ..db.session import SessionLocal
from ..i18n import get_messages
from .analysis import get_analyst
from .evidence import (
    COVERAGE_THRESHOLD,
    EvidenceSet,
    evidence_coverage,
    locators_supported,
    validate_evidence,
)
from .citations import citation_validity
from .expansion import expand
from .generation import get_generator
from .guardrails import language_banner, safety_notices
from .rerank import rerank
from .retrieval import HybridRetriever
from ..schemas import EvidencePassage, GuidanceResponse, SituationAnalysis


@dataclass
class PipelineResult:
    response: GuidanceResponse
    evidence: list[EvidencePassage] = field(default_factory=list)
    analysis: SituationAnalysis = field(default_factory=SituationAnalysis)
    fabricated_ids: list[str] = field(default_factory=list)


class GuidancePipeline:
    """Application-scoped singleton (see :func:`get_pipeline`)."""

    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory or SessionLocal
        self.retriever = HybridRetriever(self._session_factory)
        self.analyst = get_analyst()
        self.generator = get_generator()

    def invalidate(self) -> None:
        self.retriever.invalidate()

    # ------------------------------------------------------------------ #
    def run(
        self,
        query: str,
        mode: str = "situation_advice",
        language: str = "en",
        character: str | None = None,
        include_perspectives: bool | None = None,
    ) -> PipelineResult:
        msgs = get_messages(language)
        analysis = self.analyst.analyze(query, mode, character)

        if include_perspectives is None:
            include_perspectives = mode == "perspectives"
        if character and mode == "character_wisdom" and character not in analysis.entities:
            analysis.entities.insert(0, character)

        # ---------------- retrieval ------------------------------------- #
        expanded = expand(analysis, query, character)
        retrieval = self.retriever.retrieve(query, expanded)
        ranked = rerank(retrieval.passages, analysis, query)
        ev: EvidenceSet = validate_evidence(ranked, analysis)

        # ---------------- answerability gate ----------------------------- #
        # The system may only answer when the corpus actually has something to
        # say. Three signals count: a recognised theme, a known character or a
        # conflict pattern; or enough of the question's distinctive vocabulary
        # to be traceable to the retrieved evidence. If none of them hold, the
        # answer is a refusal -- never an improvised one.
        #
        # Independently, any chapter/verse locator the question *asserts*
        # ("the 47th chapter of the Virata Parva") must be corroborated by the
        # retrieved passages -- a recognised entity never licenses confirming
        # an invented reference.
        coverage = evidence_coverage(query, ranked)
        anchor = bool(
            analysis.themes
            or analysis.entities
            or analysis.conflict
            or coverage >= COVERAGE_THRESHOLD
        ) and locators_supported(query, ranked)
        if not anchor and mode != "daily_reflection":
            ev = EvidenceSet(
                passages=[],
                support_level="insufficient_evidence",
                note=msgs["insufficient"],
                dropped=[p.id for p in ranked],
            )
            ranked = []

        # ---------------- mode-specific shaping -------------------------- #
        mode_note = ""
        if mode == "source_explorer" and anchor:
            ranked = ranked or retrieval.passages[: settings.rerank_top_k]
            ev = validate_evidence(ranked, analysis)
            mode_note = (
                "Source Explorer returns the passages that match your terms; "
                "verification status is shown on each card."
            )
        elif mode == "daily_reflection":
            daily = self._daily_reflection(language)
            if daily is not None:
                ranked = [daily]
                ev = validate_evidence(ranked, analysis)

        # ---------------- generation ------------------------------------- #
        if ev.usable:
            response = self.generator.generate(
                analysis,
                ev.passages,
                query,
                mode,
                language,
                character=character,
                include_perspectives=include_perspectives,
            )
        else:
            response = self.generator.generate(
                analysis, [], query, mode, language,
                character=character, include_perspectives=include_perspectives,
            )
            response.support_level = "insufficient_evidence"
            response.evidence_note = ev.note or msgs["insufficient"]

        # ---------------- evidence bookkeeping --------------------------- #
        if ev.usable and response.support_level != "insufficient_evidence":
            response.support_level = ev.support_level if response.generator == "template" else (
                response.support_level
            )
            if not response.evidence_note and ev.note:
                response.evidence_note = ev.note

        if not response.sources:
            response.sources = [
                p.source_reference or p.parva
                for p in response.primary_text
                if p.source_reference or p.parva
            ]

        # Remove any citation not present in the retrieved pack or whose
        # reference differs from the stored passage reference.
        reference_by_id = {p.id: p.source_reference for p in ev.passages}
        citation_check = citation_validity(response, ev.passages, reference_by_id)
        if citation_check["fabricated"]:
            valid_ids = set(citation_check["valid"])
            response.primary_text = [p for p in response.primary_text if p.id in valid_ids]
            response.sources = [
                p.source_reference or p.parva
                for p in response.primary_text
                if p.source_reference or p.parva
            ]
            if not response.primary_text:
                response.support_level = "insufficient_evidence"
                response.evidence_note = msgs["insufficient"]

        # ---------------- safety (17.) ------------------------------------ #
        notices = safety_notices(query)
        banner = language_banner(language)
        if banner:
            from ..schemas import SafetyNotice

            notices.append(SafetyNotice(kind="general", message=banner))
        response.safety_notices = notices

        # ---------------- debug ------------------------------------------- #
        response.retrieval_debug.update(retrieval.debug)
        response.retrieval_debug.update(
            {
                "mode": mode,
                "analyst": self.analyst.name,
                "generator": self.generator.name,
                "evidence_dropped": ev.dropped,
                "support_level": response.support_level,
                "candidates_before_rerank": len(retrieval.passages),
                "evidence_count": len(ev.passages),
                "anchor": anchor,
                "answerability_coverage": coverage,
                "citation_validation": citation_check,
            }
        )
        if mode_note:
            response.retrieval_debug["mode_note"] = mode_note

        return PipelineResult(
            response=response,
            evidence=ev.passages,
            analysis=analysis,
        )

    # ------------------------------------------------------------------ #
    def search(
        self,
        query: str,
        language: str = "en",  # noqa: ARG002 - kept for API symmetry
        limit: int = 20,
    ) -> list[EvidencePassage]:
        """Direct corpus search for the Source Explorer (no answer generation)."""
        analysis = self.analyst.analyze(query, "source_explorer")
        expanded = expand(analysis, query)
        retrieval = self.retriever.retrieve(query, expanded)
        return retrieval.passages[:limit]

    def _daily_reflection(self, language: str) -> EvidencePassage | None:
        """Deterministic passage-of-the-day from *verified* primary text."""
        from ..db.models import Passage

        db: Session = self._session_factory()
        try:
            rows = (
                db.query(Passage)
                .filter(Passage.verification_status == "verified")
                .filter(Passage.is_primary_text.is_(True))
                .all()
            )
        finally:
            db.close()
        if not rows:
            return None
        today = _dt.date.today().isoformat()
        seed = f"{settings.reflection_seed}:{today}".encode()
        digest = int.from_bytes(hashlib.sha256(seed).digest()[:8], "big")
        rows.sort(key=lambda p: p.id)
        chosen = rows[digest % len(rows)]

        meta = self.retriever._load().get(chosen.id)
        if meta is None:
            return None
        return EvidencePassage(
            id=meta.id,
            parva=meta.parva,
            section=meta.section,
            chapter=meta.chapter,
            reference=meta.source_reference,
            speaker=meta.speaker,
            listener=meta.listener,
            characters=meta.characters,
            themes=meta.themes,
            context=meta.summary,
            quote=meta.translation or meta.original_text,
            summary=meta.summary,
            original_text=meta.original_text,
            text_type=meta.text_type,
            source_title=meta.source_title,
            verification_status=meta.verification_status,
            is_primary_text=meta.is_primary_text,
            relevance=1.0,
            semantic_score=1.0,
            keyword_score=1.0,
            source="daily",
        )


_pipeline: GuidancePipeline | None = None


def get_pipeline() -> GuidancePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = GuidancePipeline()
    return _pipeline


def reset_pipeline() -> None:
    global _pipeline
    _pipeline = None
