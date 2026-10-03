"""Citation validation shared by the live pipeline and evaluation runner."""

from __future__ import annotations

from ..schemas import EvidencePassage, GuidanceResponse


def citation_validity(
    reply: GuidanceResponse,
    evidence: list[EvidencePassage],
    all_reference_by_id: dict[str, str],
) -> dict:
    """Every cited passage must be retrieved and retain its stored reference."""
    valid, invalid, missing = [], [], []
    evidence_ids = {p.id for p in evidence}
    for p in reply.primary_text:
        if p.id not in evidence_ids:
            missing.append(p.id)
            continue
        db_ref = all_reference_by_id.get(p.id)
        if db_ref and p.reference and db_ref.strip().lower() != p.reference.strip().lower():
            invalid.append({"id": p.id, "cited": p.reference, "stored": db_ref})
        else:
            valid.append(p.id)
    for src in reply.sources:
        if src.strip() and not any(src.strip() == (p.source_reference or "").strip() for p in evidence):
            invalid.append({"source": src})
    return {"valid": valid, "invalid": invalid, "missing": missing,
            "fabricated": bool(missing or invalid)}
