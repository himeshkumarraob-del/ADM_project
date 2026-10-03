"""Structured evidence set + claim-level attribution (Phase 2, Parts 7-8).

The template generator previously reasoned from ``evidence[0]`` alone. This
module gives it a bounded, structured *evidence set*:

.. code-block:: json

    {
      "evidence_id": "ev_001",
      "passage_id": "p_042",
      "reference": {"parva": "Sauptika Parva", "section": "..."},
      "relevance_score": 0.91,
      "text": "..."
    }

and a *claim attribution* step: each textual claim the generator emits lists
the passages that actually support it. A claim with no supporting passage is
downgraded from the answer rather than cited anyway -- retrieval alone never
justifies a citation (Part 8: "Do NOT cite a passage merely because it was
retrieved").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..knowledge.taxonomy import CHARACTERS, THEMES
from ..schemas import EvidencePassage

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")

# Generic scaffolding vocabulary that appears in generated prose without being
# claim content (mirrors eval.checks._INTERPRETIVE_VOCAB).
_SCHEME_WORDS = {
    "this", "that", "these", "those", "text", "passage", "episode", "reading",
    "interpretation", "situation", "your", "the", "and", "with", "from",
    "mahabharata", "parva", "source", "evidence", "principle", "applied",
    "applying", "suggests", "records", "shows", "teaches", "support",
}


@dataclass
class EvidenceItem:
    """One bounded, structured evidence unit handed to the generator."""

    evidence_id: str
    passage_id: str
    parva: str
    section: str
    reference: str
    relevance_score: float
    text: str            # quote if the passage carries one, else the summary
    is_quotation: bool   # True only when text_type is verse/prose (a real quote)
    characters: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "passage_id": self.passage_id,
            "reference": {"parva": self.parva, "section": self.section},
            "relevance_score": self.relevance_score,
            "text": self.text,
            "is_quotation": self.is_quotation,
        }


@dataclass
class AttributedClaim:
    """A textual claim plus the passages that actually support it.

    ``claim_type`` is the Phase-3 three-way distinction:

    ``textual``         directly supported by the retrieved passage
    ``interpretation``  a reasoned reading of what the episode illustrates
    ``application``     a bridge from the principle to the user's situation

    The last two are never rendered as quotations or direct teachings.
    """

    claim: str
    supporting_passages: list[str]          # passage ids
    support_level: str                      # primary_text | interpretive | unsupported
    claim_type: str = "textual"             # textual | interpretation | application


def build_evidence_set(
    passages: list[EvidencePassage], max_items: int = 4
) -> list[EvidenceItem]:
    """Bound the evidence to at most ``max_items`` distinct, relevant units."""
    items: list[EvidenceItem] = []
    seen: set[str] = set()
    for i, p in enumerate(passages, 1):
        key = f"{p.parva}|{p.section}".lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(
            EvidenceItem(
                evidence_id=f"ev_{i:03d}",
                passage_id=p.id,
                parva=p.parva,
                section=p.section,
                reference=p.source_reference or p.parva,
                relevance_score=round(p.relevance, 4),
                text=(p.quote or p.summary or "").strip(),
                is_quotation=bool(p.quote) and p.text_type in {"verse", "prose"},
                characters=list(p.characters or []),
                themes=list(p.themes or []),
            )
        )
        if len(items) >= max_items:
            break
    return items


# --------------------------------------------------------------------------- #
# Claim attribution
# --------------------------------------------------------------------------- #
def _content_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for w in _WORD.findall(text.lower()):
        if len(w) >= 5 and w not in _SCHEME_WORDS:
            terms.add(w)
            if len(w) > 5:
                terms.add(w.rstrip("s"))
    return terms


def _passage_terms(item: EvidenceItem) -> set[str]:
    blob = " ".join(
        [item.text, item.parva, item.section, " ".join(item.characters),
         " ".join(item.themes)]
    )
    terms = _content_terms(blob)
    for slug in item.themes:
        terms |= {part for part in slug.replace("-", " ").split() if len(part) >= 5}
    for c in CHARACTERS:
        if c["slug"] in {x.lower() for x in item.characters}:
            terms.add(c["name"].lower())
    return terms


def attribute_claim(claim: str, evidence: list[EvidenceItem]) -> AttributedClaim:
    """Map a claim onto the passages whose content actually overlaps it.

    A passage supports a claim when a meaningful share of the claim's
    content words (and any named characters/themes) appear in that passage's
    text or metadata. Claims with zero support are reported as ``unsupported``
    -- the caller decides to drop or qualify them, never to cite anyway.
    """
    claim_terms = _content_terms(claim)
    if not claim_terms:
        return AttributedClaim(claim=claim, supporting_passages=[], support_level="unsupported")

    support_ratio = 0.34  # a third of distinctive claim terms must overlap
    supporting: list[str] = []
    best_ratio = 0.0
    for item in evidence:
        pterms = _passage_terms(item)
        if not pterms:
            continue
        overlap = claim_terms & pterms
        ratio = len(overlap) / max(1, len(claim_terms))
        best_ratio = max(best_ratio, ratio)
        if ratio >= support_ratio:
            supporting.append(item.passage_id)

    if supporting:
        return AttributedClaim(claim, supporting, "primary_text")
    if best_ratio > 0:
        return AttributedClaim(claim, [], "interpretive")
    return AttributedClaim(claim, [], "unsupported")


def _principle_terms(text: str) -> set[str]:
    """Theme/character vocabulary used by principle sentences."""
    terms: set[str] = set()
    low = text.lower()
    for t in THEMES:
        head = t["slug"].replace("-", " ")
        if head in low or t["name"].lower() in low:
            terms |= {w for w in head.split() if len(w) >= 5}
    for c in CHARACTERS:
        if c["name"].lower() in low:
            terms.add(c["name"].lower())
    return terms


def attribute_principle(principle: str, evidence: list[EvidenceItem]) -> AttributedClaim:
    """Principle sentences are interpretive by design: they must trace to at
    least one passage's theme/character vocabulary, else they are flagged."""
    terms = _principle_terms(principle)
    if not terms:
        return AttributedClaim(principle, [], "unsupported")
    supporting: list[str] = []
    for item in evidence:
        pterms = _passage_terms(item)
        if terms & pterms:
            supporting.append(item.passage_id)
    if supporting:
        return AttributedClaim(principle, supporting, "interpretive")
    return AttributedClaim(principle, [], "unsupported")
