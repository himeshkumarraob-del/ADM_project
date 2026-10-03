"""Corpus integrity + health.

One module that both the admin API (Corpus Health dashboard) and the integrity
tests call, so the numbers shown to an admin are the numbers the tests assert
on. Everything is computed from the live database — no hardcoded statistics.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..db.models import Passage, Source
from .taxonomy import (
    VALID_VERIFICATION_STATUSES,
    canonical_character_slugs,
    canonical_theme_slugs,
    is_canonical_parva,
    validate_passage_metadata,
)


def _passage_to_item(p: Passage) -> dict:
    """Model -> dict shape that ``validate_passage_metadata`` expects."""
    return {
        "parva": p.parva,
        "section": p.section,
        "chapter": p.chapter,
        "speaker": p.speaker,
        "characters": list(p.characters or []),
        "themes": list(p.themes or []),
        "summary": p.summary,
        "translation": p.translation,
        "original_text": p.original_text,
        "source_reference": p.source_reference,
        "verification_status": p.verification_status,
    }


def corpus_health(db: Session) -> dict:
    """Compute the full corpus-health report from the database."""
    rows: list[Passage] = db.query(Passage).all()
    total = len(rows)

    by_status = {"verified": 0, "unverified": 0, "needs_review": 0, "rejected": 0}
    non_canonical_parvas: list[dict] = []
    missing_metadata: list[dict] = []
    invalid_status: list[dict] = []
    broken_references: list[dict] = []
    unknown_characters: list[dict] = []
    unknown_themes: list[dict] = []
    missing_original_text = 0
    missing_translation = 0

    seen_refs: dict[str, str] = {}
    duplicate_references: list[dict] = []

    valid_source_ids = {s.id for s in db.query(Source.id).all()}

    for p in rows:
        status = (p.verification_status or "").lower()
        if status in by_status:
            by_status[status] += 1
        else:
            invalid_status.append({"id": p.id, "reference": p.source_reference, "status": status})

        if status in {"verified", "needs_review"} or status not in VALID_VERIFICATION_STATUSES:
            pass  # status counted above

        if not is_canonical_parva(p.parva):
            non_canonical_parvas.append({"id": p.id, "reference": p.source_reference, "parva": p.parva})

        issues = validate_passage_metadata(_passage_to_item(p))
        meta_issues = [i for i in issues if i.startswith("missing required field")]
        if meta_issues:
            missing_metadata.append({"id": p.id, "reference": p.source_reference, "issues": meta_issues})
        ref_issues = [i for i in issues if i.startswith("broken reference")]
        if ref_issues:
            broken_references.append({"id": p.id, "reference": p.source_reference, "issues": ref_issues})
        char_issues = [i for i in issues if i.startswith("characters outside taxonomy")]
        if char_issues:
            unknown_characters.append({"id": p.id, "reference": p.source_reference, "issues": char_issues})
        theme_issues = [i for i in issues if i.startswith("themes outside taxonomy")]
        if theme_issues:
            unknown_themes.append({"id": p.id, "reference": p.source_reference, "issues": theme_issues})

        if p.source_id not in valid_source_ids:
            broken_references.append(
                {"id": p.id, "reference": p.source_reference, "issues": ["source_id does not resolve"]}
            )
        if not (p.original_text or "").strip():
            missing_original_text += 1
        if not (p.translation or "").strip():
            missing_translation += 1

        ref = (p.source_reference or "").strip().lower()
        if ref in seen_refs:
            duplicate_references.append(
                {"ids": [seen_refs[ref], p.id], "reference": p.source_reference}
            )
        else:
            seen_refs[ref] = p.id

    # canonical parva coverage over the 18
    from .taxonomy import CANONICAL_PARVAS

    present_parvas = {p.parva for p in rows if is_canonical_parva(p.parva)}
    parva_coverage = {
        "canonical_parvas": len(CANONICAL_PARVAS),
        "represented": len(present_parvas),
        "missing": [pv for pv in CANONICAL_PARVAS if pv not in present_parvas],
    }

    return {
        "total_passages": total,
        "verified": by_status["verified"],
        "unverified": by_status["unverified"],
        "needs_review": by_status["needs_review"],
        "rejected": by_status["rejected"],
        "invalid_status_count": len(invalid_status),
        "invalid_status": invalid_status,
        "canonical_parva_coverage": parva_coverage,
        "non_canonical_parvas": non_canonical_parvas,
        "missing_metadata": missing_metadata,
        "duplicate_references": duplicate_references,
        "broken_references": broken_references,
        "unknown_characters": unknown_characters,
        "unknown_themes": unknown_themes,
        "missing_original_text": missing_original_text,
        "missing_translation": missing_translation,
        "healthy": bool(
            total
            and not non_canonical_parvas
            and not missing_metadata
            and not duplicate_references
            and not broken_references
            and not invalid_status
            and not unknown_characters
            and not unknown_themes
        ),
    }
