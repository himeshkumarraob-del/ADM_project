"""20. Anti-hallucination and faithfulness checks.

Pure functions over (question, generated response, evidence). Used by the
evaluation runner and importable directly from the test suite.
"""

from __future__ import annotations

import re

from ..rag.guardrails import grounding_check
from ..rag.citations import citation_validity
from ..schemas import EvidencePassage, GuidanceResponse

_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]{3,}")

# Words that are legitimately present in an interpretation without being in
# the source (connectives, labelling vocabulary, common analytical terms).
_INTERPRETIVE_VOCAB = {
    "this", "that", "these", "those", "here", "there", "text", "passage",
    "episode", "interpretation", "reading", "situation", "user", "your",
    "mahabharata", "parva", "evidence", "principle", "source", "chapter",
    "situation", "applied", "applying", "suggest", "suggests", "may", "might",
    "emphasis", "emphasises", "emphasizes", "shown", "shows", "records",
    "situation", "situation", "question", "answer", "support", "claim",
}


def quotation_invention_rate(reply: GuidanceResponse,
                              evidence: list[EvidencePassage]) -> dict:
    """How much quotation/citation-shaped text is not backed by evidence."""
    blob = " ".join(
        [reply.episode, reply.interpretation, reply.application]
        + [p.stance for p in reply.perspectives]
    )
    g = grounding_check(blob, evidence)
    return {
        "unsupported_references": g["unsupported_references"],
        "unsupported_quotes": g["unsupported_quotes"],
        "unsupported_sanskrit": g["unsupported_sanskrit"],
        "clean": g["clean"],
        "invented": not g["clean"],
    }


def faithfulness(reply: GuidanceResponse, evidence: list[EvidencePassage]) -> dict:
    """Lexical grounding of the generated prose in the evidence pack.

    Proxy metric: the share of distinctive content words in the interpretation
    and application that are traceable to the evidence, the taxonomy vocabulary
    or the user's own query terms. It is a *proxy* -- deliberately reported as
    one -- and is used for regression detection rather than as a score shown to
    users.
    """
    evidence_words = set()
    for p in evidence:
        blob = " ".join([p.summary, p.quote, p.original_text, p.parva, p.section,
                         " ".join(p.characters), " ".join(p.themes)])
        evidence_words |= {w.lower() for w in _WORD.findall(blob)}

    def coverage(text: str, extra: set[str]) -> float:
        words = {w.lower() for w in _WORD.findall(text)}
        if not words:
            return 1.0
        known = evidence_words | _INTERPRETIVE_VOCAB | extra
        hit = sum(1 for w in words if w in known or w.rstrip("s") in known)
        return round(hit / len(words), 3)

    interp = coverage(reply.interpretation, set())
    applic = coverage(reply.application, set())
    return {
        "interpretation_coverage": interp,
        "application_coverage": applic,
        "mean_coverage": round((interp + applic) / 2, 3),
    }


def distinction_present(reply: GuidanceResponse) -> dict:
    """Is the text-vs-interpretation layering actually there?"""
    interp = reply.interpretation.lower()
    markers_textual = ["textual evidence", "the retrieved passage", "reads",
                       "records", "the passage", "source"]
    markers_interp = ["interpretation", "can be read", "can be interpreted",
                      "suggests", "this episode can"]
    has_textual = any(m in interp for m in markers_textual)
    has_interp = any(m in interp for m in markers_interp)
    return {
        "textual_layer": has_textual,
        "interpretation_layer": has_interp,
        "distinction_present": has_textual and has_interp,
    }


def absolute_moral_command(reply: GuidanceResponse) -> dict:
    """Detect imperatives that attribute a rule to the Mahabharata."""
    patterns = [
        r"the mahabharata (clearly )?(says|commands|states) you must",
        r"the mahabharata (clearly )?(says|commands|states) that you must",
        r"vyasa (says|commands) you must",
        r"you must (do|stop|leave|forgive|take revenge)",
    ]
    blob = " ".join([reply.interpretation, reply.application])
    hits = [p for p in patterns if re.search(p, blob, re.I)]
    return {"violations": hits, "ok": not hits}


def supports_claim(reply: GuidanceResponse) -> bool:
    """insufficient_evidence must be reported when there is no evidence."""
    if reply.support_level == "insufficient_evidence":
        return True
    return bool(reply.primary_text)
