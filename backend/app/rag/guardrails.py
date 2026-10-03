"""17. Safety + grounding guardrails.

* :func:`safety_notices`  -- detects crisis / medical / legal / financial
  framing and returns a notice that is rendered above the answer.
* :func:`grounding_check` -- scans a generated answer for quotation-shaped
  strings (Sanskrit verses, `Book X, Chapter Y` citations) that are not backed
  by the retrieved evidence, and reports them so the answer can be downgraded
  or refused.
* :func:`language_banner` -- for non-English output, records that the source
  shown is a translation of the original rather than the original itself.
"""

from __future__ import annotations

import re

from ..knowledge.taxonomy import CRISIS_TERMS, PROFESSIONAL_DISCLAIMER_TOPICS
from ..schemas import EvidencePassage, SafetyNotice

CRISIS_MESSAGE = (
    "What you are describing sounds serious and immediate. The Mahabharata has "
    "much to say about grief, despair and duty, but it cannot help you the way "
    "a trained person can. Please contact your local emergency number, a "
    "crisis line, or someone you trust right now. I can still explore the "
    "textual themes with you afterwards if that would help."
)

_PROFESSIONAL_MESSAGE = {
    "medical": ("This system explores the Mahabharata; it does not provide medical or "
                "mental-health advice. Please consult a qualified professional about "
                "health decisions."),
    "legal": ("This system explores the Mahabharata; it does not provide legal advice. "
              "Please consult a qualified lawyer about your situation."),
    "financial": ("This system explores the Mahabharata; it does not provide financial "
                  "advice. Please consult a qualified financial professional."),
}

GENERAL_DISCLAIMER = (
    "This is a source-grounded exploration of the Mahabharata, not professional advice."
)


def safety_notices(text: str) -> list[SafetyNotice]:
    low = text.lower()
    notices: list[SafetyNotice] = []
    if any(t in low for t in CRISIS_TERMS):
        notices.append(SafetyNotice(kind="crisis", message=CRISIS_MESSAGE))
        return notices  # a crisis notice supersedes the rest
    for kind, terms in PROFESSIONAL_DISCLAIMER_TOPICS.items():
        if kind == "crisis":
            continue
        if any(t in low for t in terms):
            msg = _PROFESSIONAL_MESSAGE.get(kind)
            if msg:
                notices.append(SafetyNotice(kind=kind, message=msg))  # type: ignore[arg-type]
    if not notices:
        notices.append(SafetyNotice(kind="general", message=GENERAL_DISCLAIMER))
    return notices


# --------------------------------------------------------------------------- #
# Grounding check
# --------------------------------------------------------------------------- #
_SANSKRIT_LINE = re.compile(r"[\u0900-\u097F]{4,}")           # Devanagari run
_DANDED_QUOTE = re.compile(r"[“\u201c][^”\u201d]{25,}[”\u201d]")
_REFERENCE = re.compile(
    r"\b(?:book|parva|adhy[aā]ya|chapter|section|verse|canto)\s+\d+"
    r"(?:\.\d+)?(?:\s*\(\s*[A-Z][A-Za-z ]+Parva\s*\))?",
    re.I,
)
_CITED_REFS: dict[str, list[str]] = {}


def register_evidence_refs(passages: list[EvidencePassage]) -> None:
    """Record which reference strings are legitimately in evidence."""
    for p in passages:
        refs = _CITED_REFS.setdefault(p.id, [])
        for token in _tokens(p.reference):
            if token not in refs:
                refs.append(token)


def _tokens(ref: str) -> list[str]:
    return [r for r in re.split(r"\s*[;/,]\s*", ref) if r.strip()]


def grounding_check(answer: str, evidence: list[EvidencePassage]) -> dict:
    """Return the unsupported quotation/citation shapes found in ``answer``."""
    allowed_refs: set[str] = set()
    allowed_text: list[str] = []
    for p in evidence:
        for t in _tokens(p.reference):
            allowed_refs.add(t.strip().lower())
        allowed_refs.add(p.parva.strip().lower())
        for chunk in (p.quote, p.original_text, p.summary):
            if chunk and len(chunk) > 40:
                allowed_text.append(chunk.strip().lower())

    unsupported_refs: list[str] = []
    for match in _REFERENCE.findall(answer):
        token = match.strip().lower()
        backed = (
            token in allowed_refs
            or any(allowed in token or token in allowed for allowed in allowed_refs)
            or any(token in blob for blob in allowed_text)
        )
        if not backed:
            unsupported_refs.append(match.strip())

    unsupported_quotes: list[str] = []
    for match in _DANDED_QUOTE.findall(answer):
        inner = match.strip('“”" ').lower()
        if not any(inner[:80] in blob or blob[:80] in inner for blob in allowed_text):
            unsupported_quotes.append(match[:140])

    devanagari = [m for m in _SANSKRIT_LINE.findall(answer) if len(m) >= 6]
    unsupported_sanskrit = [
        s for s in devanagari if not any(s[:20] in (p.original_text or "") for p in evidence)
    ]

    return {
        "unsupported_references": unsupported_refs,
        "unsupported_quotes": unsupported_quotes,
        "unsupported_sanskrit": unsupported_sanskrit,
        "clean": not (unsupported_refs or unsupported_quotes or unsupported_sanskrit),
    }


def language_banner(language: str) -> str:
    if language == "en":
        return ""
    return (
        "The source text is in its original language; the wording shown here is a "
        "translation. Where a translation is displayed it is labelled as such and "
        "never replaces the original."
    )
