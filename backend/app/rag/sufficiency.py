"""Evidence sufficiency (Phase 2, Part 9).

Decides, *before generation*, whether the retrieved evidence can actually
answer the user's specific question:

* ``SUFFICIENT``   -- enough distinct, relevant passages to answer directly.
* ``PARTIAL``      -- relevant evidence exists but is thin (one passage, or
  relevance barely above the cut); the answer may proceed but must be
  qualified (this maps onto the existing ``interpretive`` behaviour).
* ``INSUFFICIENT`` -- nothing usable; the pipeline must refuse through the
  existing answerability/coverage logic (which this module never weakens --
  it only adds an independent check *after* the gate has already run).

The verdict is attached to ``retrieval_debug`` and consumed by the eval
runner to separate retrieval failure from generation failure.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import settings
from ..schemas import EvidencePassage, SituationAnalysis

SUFFICIENT = "SUFFICIENT"
PARTIAL = "PARTIAL"
INSUFFICIENT = "INSUFFICIENT"


@dataclass
class SufficiencyVerdict:
    level: str                    # SUFFICIENT | PARTIAL | INSUFFICIENT
    usable_passages: int
    top_relevance: float
    reason: str

    def as_debug(self) -> dict:
        return {
            "evidence_sufficiency": self.level,
            "usable_passages": self.usable_passages,
            "top_relevance": self.top_relevance,
            "reason": self.reason,
        }


def _distinct_relevant(passages: list[EvidencePassage]) -> list[EvidencePassage]:
    """Relevant passages that are genuinely distinct (not near-duplicate
    scenes from the same section)."""
    out: list[EvidencePassage] = []
    seen_sections: set[str] = set()
    for p in sorted(passages, key=lambda x: -x.relevance):
        if p.relevance < settings.min_relevance_cut:
            continue
        key = (p.parva, p.section).lower() if isinstance((p.parva, p.section), tuple) else \
            f"{p.parva}|{p.section}".lower()
        if key in seen_sections:
            continue
        seen_sections.add(key)
        out.append(p)
    return out


def assess_sufficiency(
    passages: list[EvidencePassage],
    analysis: SituationAnalysis,
) -> SufficiencyVerdict:
    usable = _distinct_relevant(passages)
    if not usable:
        return SufficiencyVerdict(
            INSUFFICIENT, 0, 0.0,
            "no passage clears the minimum relevance cut",
        )

    top = usable[0]
    n = len(usable)

    # Enough to answer directly: at least two distinct relevant passages, or
    # one passage that is *strongly* relevant (well above the strong-support
    # threshold) -- that is the multi-passage-aware version of "the corpus has
    # something to say about exactly this".
    if n >= 2 or top.relevance >= settings.strong_support_threshold * 1.35:
        return SufficiencyVerdict(
            SUFFICIENT, n, top.relevance,
            f"{n} distinct relevant passage(s); top relevance {top.relevance:.3f}",
        )

    if top.relevance >= settings.min_relevance_cut:
        return SufficiencyVerdict(
            PARTIAL, n, top.relevance,
            "only one marginally relevant passage; answer must stay qualified",
        )

    return SufficiencyVerdict(
        INSUFFICIENT, 0, top.relevance, "evidence below the relevance cut"
    )
