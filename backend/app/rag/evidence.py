"""Evidence validation and support-level classification.

Two jobs:

1. **Validate** -- decide whether the retrieved set is good enough to support
   *any* claim. Rejected / non-primary sources are dropped from the evidence
   set entirely (they remain searchable in the Source Explorer, where the
   verification badge is shown to the user).

2. **Classify** -- assign one of the four documented support levels:

   * ``strong_textual_support`` -- a verified, primary-text passage scored at
     or above ``STRONG_SUPPORT_THRESHOLD``.
   * ``interpretive``          -- good evidence, but the link to the user's
     situation is a reading, not a statement in the text.
   * ``modern_application``    -- thin evidence; only the *application* layer
     is carrying the answer.
   * ``insufficient_evidence`` -- nothing reliable enough. The pipeline must
     say so explicitly instead of inventing a passage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import settings
from ..schemas import EvidencePassage, SituationAnalysis

INSUFFICIENT_NOTE = (
    "I could not find a sufficiently direct passage in the source material "
    "to support this conclusion."
)

# Minimum share of the query's distinctive vocabulary that must be traceable
# to the retrieved evidence before the system considers the question answerable.
COVERAGE_THRESHOLD = 0.40

# Structural words: they occur in almost every question and tell us nothing
# about whether the corpus actually covers the subject.
_GENERIC_TERMS = {
    "mahabharata", "parva", "chapter", "chapters", "verse", "verses", "book",
    "books", "sanskrit", "quote", "quotes", "quoting", "says", "said",
    "saying", "according", "correct", "explain", "explains", "explaining",
    "discuss", "discusses", "discussion", "meaning", "episode", "episodes",
    "story", "stories", "source", "sources", "text", "texts", "really",
    "actually", "original", "translation", "please", "tell", "asking",
    "asked", "question", "teach", "teaches", "teaching", "shows", "shown",
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]+")

# A question may *assert* a location in the text -- "the 47th chapter of the
# Virata Parva", "verse 2.47", "Adhyaya 12".  Every such assertion must be
# corroborated by the retrieved evidence; otherwise the system is being asked
# to confirm an invented locator and must refuse.
_LOCATOR_RE = re.compile(
    r"\b(?:chapter|verse|adhyaya|adhy[aā]ya|section|book)\s+(?:no\.?\s*)?"
    r"(\d{1,3}(?:\.\d{1,3})?)"
    r"|(\d{1,3}(?:\.\d{1,3})?)(?:st|nd|rd|th)\s+"
    r"(?:chapter|verse|adhyaya|adhy[aā]ya|section|book)\b",
    re.I,
)


def asserted_locators(query: str) -> list[str]:
    """Chapter/verse numbers the question claims exist (e.g. ``47``, ``2.47``)."""
    out: list[str] = []
    for m in _LOCATOR_RE.finditer(query):
        n = m.group(1) or m.group(2)
        if n and n not in out:
            out.append(n)
    return out


def locators_supported(query: str, evidence: list[EvidencePassage]) -> bool:
    """True when every locator the question asserts is corroborated by at
    least one retrieved passage (or when the question asserts none).

    A locator such as ``47`` must appear as its own number -- it will not be
    satisfied by ``Bhagavad Gita 2.47``, and vice versa.
    """
    locs = asserted_locators(query)
    if not locs:
        return True
    if not evidence:
        return False
    blob = " | ".join(
        part
        for p in evidence
        for part in (p.chapter or "", p.source_reference, p.section, p.parva)
        if part
    )
    for loc in locs:
        if "." in loc:
            pat = re.compile(rf"(?<!\d){re.escape(loc)}(?!\d)")
        else:
            pat = re.compile(rf"(?<![\d.]){re.escape(loc)}(?![\d.])")
        if not pat.search(blob):
            return False
    return True

# Ordinary English that appears in nearly every question and therefore says
# nothing about whether the corpus covers the subject.
_STOP_TERMS = {
    "what", "which", "where", "when", "while", "with", "whose", "whom",
    "that", "this", "these", "those", "there", "here", "then", "than",
    "does", "doing", "done", "did", "have", "having", "has", "had",
    "will", "would", "could", "should", "shall", "might", "may", "must",
    "about", "into", "from", "over", "under", "after", "before", "because",
    "been", "being", "were", "was", "are", "its", "it's", "their", "there",
    "them", "they", "your", "yours", "ours", "mine", "more", "most",
    "very", "just", "even", "also", "some", "any", "all", "one", "two",
}


def distinctive_terms(query: str) -> list[str]:
    """Content words that could distinguish an answerable question from a
    subject the corpus has never heard of."""
    out: list[str] = []
    for w in _WORD_RE.findall(query.lower()):
        if len(w) < 4 or w in _GENERIC_TERMS or w in _STOP_TERMS:
            continue
        if w not in out:
            out.append(w)
    return out


def _term_matches(term: str, blob: str) -> bool:
    if term in blob:
        return True
    # crude but effective stem/probe match: "promises" -> "promis"
    if len(term) > 6 and term[:6] in blob:
        return True
    return False


def evidence_coverage(query: str, evidence: list[EvidencePassage]) -> float:
    """Fraction of the query's distinctive vocabulary found in the evidence."""
    terms = distinctive_terms(query)
    if not terms or not evidence:
        return 0.0
    parts: list[str] = []
    for p in evidence:
        parts.extend(
            [
                p.parva, p.section, p.source_reference, p.summary, p.quote,
                p.original_text, p.speaker, p.listener,
                " ".join(p.characters), " ".join(p.themes),
            ]
        )
    blob = " ".join(parts).lower()
    if not blob.strip():
        return 0.0
    hits = sum(1 for t in terms if _term_matches(t, blob))
    return round(hits / len(terms), 3)


@dataclass
class EvidenceSet:
    passages: list[EvidencePassage]
    support_level: str
    note: str
    dropped: list[str]

    @property
    def usable(self) -> bool:
        return bool(self.passages)


def validate_evidence(
    passages: list[EvidencePassage],
    analysis: SituationAnalysis,
) -> EvidenceSet:
    dropped: list[str] = []
    kept: list[EvidencePassage] = []
    for p in passages:
        if p.verification_status == "rejected":
            dropped.append(p.id)
            continue
        if not p.summary and not p.quote:
            dropped.append(p.id)
            continue
        if settings.require_primary_text_for_strong_support:
            # non-primary sources can still be shown, but only as corroboration
            kept.append(p)
        else:
            kept.append(p)

    if not kept:
        return EvidenceSet(
            passages=[],
            support_level="insufficient_evidence",
            note=INSUFFICIENT_NOTE,
            dropped=dropped,
        )

    top = kept[0]
    strong_candidate = is_strong_textual_evidence(top)

    if strong_candidate:
        level = "strong_textual_support"
        note = ""
    elif top.relevance >= settings.min_relevance_cut:
        level = "interpretive"
        note = (
            "The passages below are relevant to the themes at issue, but the link "
            "between them and your situation is an interpretation rather than a "
            "statement made in the text."
        )
    else:
        level = "insufficient_evidence"
        note = INSUFFICIENT_NOTE

    return EvidenceSet(passages=kept, support_level=level, note=note, dropped=dropped)


def is_strong_textual_evidence(passage: EvidencePassage) -> bool:
    """Whether a passage can support a direct textual claim.

    Editorial summaries are useful episode context, but not quotations or
    source translation evidence, so they cannot earn the strongest label.
    """
    return bool(
        passage.verification_status == "verified"
        and passage.is_primary_text
        and passage.text_type in {"verse", "prose"}
        and (passage.quote or passage.original_text)
        and passage.relevance >= settings.strong_support_threshold
    )


def enforce_citation_support(
    cited_ids: list[str],
    evidence: list[EvidencePassage],
    requested_level: str,
) -> tuple[list[EvidencePassage], str, list[str]]:
    """Drop citations that are not backed by retrieved evidence.

    Returns (kept_passages, corrected_support_level, fabricated_ids).
    A citation can only reference a passage that was actually retrieved; any
    other id is treated as a fabrication attempt and reported.
    """
    by_id = {p.id: p for p in evidence}
    kept: list[EvidencePassage] = []
    fabricated: list[str] = []
    seen: set[str] = set()
    for pid in cited_ids:
        if pid in seen:
            continue
        seen.add(pid)
        if pid in by_id:
            kept.append(by_id[pid])
        else:
            fabricated.append(pid)

    level = requested_level
    if fabricated or not kept:
        level = "insufficient_evidence" if not kept else requested_level
    return kept, level, fabricated
