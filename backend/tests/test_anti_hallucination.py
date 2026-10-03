"""20. Anti-hallucination test suite.

These tests fail if the system starts inventing quotations, chapter numbers,
references or teachings -- or if it stops refusing questions the corpus cannot
support.
"""

from __future__ import annotations

import pytest

from app.eval.checks import citation_validity, distinction_present, quotation_invention_rate
from app.rag.guardrails import grounding_check
from app.schemas import EvidencePassage


def _ev(pid: str = "abc", ref: str = "Sabha Parva — the great dice game",
        quote: str = "Yudhishthira continued to throw the dice.",
        summary: str = "The dice game in the assembly hall.") -> EvidencePassage:
    return EvidencePassage(
        id=pid, parva="Sabha Parva", reference=ref, quote=quote, summary=summary,
        source_reference=ref, text_type="prose",
    )


# --------------------------------------------------------------------------- #
# grounding_check
# --------------------------------------------------------------------------- #
def test_grounding_allows_evidence_backed_reference():
    e = _ev()
    answer = "The Sabha Parva records the dice game."
    assert grounding_check(answer, [e])["clean"] is True


def test_grounding_flags_invented_chapter_number():
    e = _ev()
    answer = "See Book 47, Chapter 12 of the Sabha Parva for the details."
    result = grounding_check(answer, [e])
    assert result["clean"] is False
    assert result["unsupported_references"]


def test_grounding_flags_invented_sanskrit():
    e = _ev()
    answer = "The verse runs \u0928ार्ती नार्तिर ने स्रायम है, a line I composed myself."
    result = grounding_check(answer, [e])
    assert result["clean"] is False
    assert result["unsupported_sanskrit"], "unattributed Devanagari must be flagged"


def test_grounding_flags_unsourced_long_quotation():
    e = _ev()
    answer = "Vyasa writes, “and then the king resolved to give away everything he owned”."
    result = grounding_check(answer, [e])
    assert result["unsupported_quotes"] or result["clean"] is False


def test_grounding_accepts_quotation_taken_from_evidence():
    e = _ev()
    answer = 'The passage records that "Yudhishthira continued to throw the dice."'
    assert grounding_check(answer, [e])["clean"] is True


# --------------------------------------------------------------------------- #
# citation verification
# --------------------------------------------------------------------------- #
def test_citation_must_exist_in_evidence():
    real = _ev(pid="real")
    fake = _ev(pid="made-up-id", ref="Udyoga Parva — invented")
    from app.schemas import GuidanceResponse

    reply = GuidanceResponse(primary_text=[real, fake])
    result = citation_validity(reply, [real], {"real": real.source_reference})
    assert result["fabricated"] is True
    assert result["missing"] == ["made-up-id"]


def test_citation_reference_must_match_database():
    real = _ev(pid="real")
    tampered = real.model_copy(update={"reference": "Udyoga Parva, Chapter 999"})
    from app.schemas import GuidanceResponse

    reply = GuidanceResponse(primary_text=[tampered])
    result = citation_validity(
        reply, [real], {"real": real.source_reference}
    )
    assert result["fabricated"] is True
    assert result["invalid"]


def test_unsupported_claim_is_not_assigned_to_top_passage():
    from app.rag.attributor import build_evidence_set
    from app.rag.generation import _attributed

    attributed = _attributed("A claim about cryptocurrency markets.", build_evidence_set([_ev()]))
    assert attributed.support_level == "unsupported"
    assert attributed.supporting_passages == []


# --------------------------------------------------------------------------- #
# end-to-end: canary questions must be refused
# --------------------------------------------------------------------------- #
# Questions whose subject matter is entirely absent from the corpus: the
# answerability gate must refuse all of them.
CANARIES_REFUSED = [
    "What does the Mahabharata say about cryptocurrency trading strategies?",
    "What is the correct dosage of paracetamol according to the Mahabharata?",
    "What does the Mahabharata say about React useEffect cleanup functions?",
    # Substring collision canary: "controller" contains "control", which used
    # to fire the ``self-control`` theme and so passed the answerability anchor
    # for a question the corpus cannot possibly support.
    "What does the Mahabharata say about configuring a Kubernetes ingress controller?",
]

# Questions that name real entities but assert something the corpus does not
# contain. These may retrieve relevant passages, but must never confirm the
# fabricated premise or invent the chapter/verse it asserts.
CANARIES_NO_FABRICATION = [
    "Quote the Sanskrit verse where Yudhishthira explains tax policy in the 47th "
    "chapter of the Virata Parva.",
    "In which chapter of the Sabha Parva does Krishna discuss stock markets?",
]

CANARIES = CANARIES_REFUSED


# --------------------------------------------------------------------------- #
# asserted locators must be corroborated by the evidence
# --------------------------------------------------------------------------- #
def test_locator_assertion_without_corroboration_is_refused(pipeline):
    """A recognised entity (Yudhishthira, Virata Parva) must never be enough
    to confirm an invented chapter number."""
    reply = pipeline.run(
        "Quote the Sanskrit verse where Yudhishthira explains tax policy in the "
        "47th chapter of the Virata Parva.",
        mode="source_explorer",
    ).response
    assert reply.support_level == "insufficient_evidence"
    assert reply.primary_text == []


def test_locator_regex_extracts_asserted_numbers():
    from app.rag.evidence import asserted_locators

    assert asserted_locators("the 47th chapter of the Virata Parva") == ["47"]
    assert asserted_locators("chapter 12 of the Sabha Parva") == ["12"]
    assert asserted_locators("Bhagavad Gita verse 2.47") == ["2.47"]
    assert asserted_locators("What does the text say about duty?") == []


def test_locator_supported_when_evidence_contains_it():
    from app.rag.evidence import locators_supported

    supported = _ev(pid="g", ref="Bhagavad Gita 2.47 (Bhishma Parva, Adhyaya 26)",
                    quote="You have a right to the work itself.")
    assert locators_supported("What does verse 2.47 say?", [supported]) is True
    # "2.47" must not satisfy an asserted chapter 47
    assert locators_supported("Chapter 47 of the Bhishma Parva?", [supported]) is False


@pytest.mark.parametrize("question", CANARIES_REFUSED)
def test_unanswerable_questions_are_refused(pipeline, question):
    result = pipeline.run(question, mode="source_explorer")
    reply = result.response
    assert reply.support_level == "insufficient_evidence", (
        f"expected refusal for: {question!r} got {reply.support_level}"
    )
    assert reply.primary_text == []
    assert reply.sources == []
    assert "could not find a sufficiently direct passage" in reply.evidence_note or (
        "not enough textual evidence" in reply.interpretation
    ), "refusal must use the documented wording"


@pytest.mark.parametrize("question", CANARIES_REFUSED + CANARIES_NO_FABRICATION)
def test_no_fabricated_chapter_or_verse_reference(pipeline, question):
    reply = pipeline.run(question, mode="source_explorer").response
    blob = " ".join([reply.episode, reply.interpretation, reply.application])
    assert not re_search_reference(blob), f"fabricated reference in answer: {blob!r}"


@pytest.mark.parametrize("question", CANARIES_NO_FABRICATION)
def test_fabricated_premise_is_never_confirmed(pipeline, question):
    result = pipeline.run(question, mode="source_explorer")
    reply, evidence = result.response, result.evidence
    if not evidence:
        return
    inv = quotation_invention_rate(reply, evidence)
    assert inv["clean"], f"invented material: {inv}"
    # the asserted chapter number must not appear anywhere in the answer
    assert "chapter 47" not in " ".join(
        [reply.episode, reply.interpretation, reply.application]
    ).lower()
    # and the sources must all be passages that actually exist
    stored = {p.source_reference for p in evidence}
    for src in reply.sources:
        assert any(src == s or src in s for s in stored), f"unknown source: {src!r}"


def re_search_reference(text: str) -> bool:
    import re

    return bool(re.search(r"\b(chapter|adhy[aā]ya|verse|book)\s+\d+", text, re.I))


# --------------------------------------------------------------------------- #
# end-to-end: no invented material in a normal answer
# --------------------------------------------------------------------------- #
REAL_QUESTIONS = [
    "What happens in the dice game of the Mahabharata?",
    "Why did Karna remain loyal to Duryodhana?",
    "I worked hard but someone else got the credit. Should I give up?",
    "Should I stay silent when my friend is doing something wrong?",
    "My friend betrayed me and I want revenge. What should I do?",
]


@pytest.mark.parametrize("question", REAL_QUESTIONS)
def test_answer_is_fully_grounded(pipeline, question):
    result = pipeline.run(question, mode="situation_advice")
    reply, evidence = result.response, result.evidence
    assert evidence, f"no evidence retrieved for {question!r}"
    assert reply.support_level != "insufficient_evidence"

    inv = quotation_invention_rate(reply, evidence)
    assert inv["clean"], f"invented material: {inv}"

    cite = citation_validity(reply, evidence, {p.id: p.source_reference for p in evidence})
    assert not cite["fabricated"], f"fabricated citation: {cite}"

    # every response must carry sources
    assert reply.sources, "response has no sources"


@pytest.mark.parametrize("question", REAL_QUESTIONS)
def test_answer_distinguishes_text_from_interpretation(pipeline, question):
    reply = pipeline.run(question, mode="situation_advice").response
    dist = distinction_present(reply)
    assert dist["distinction_present"], (
        f"missing textual/interpretation layering for {question!r}: {dist}"
    )


@pytest.mark.parametrize("question", REAL_QUESTIONS)
def test_no_absolute_moral_commands(pipeline, question):
    from app.eval.checks import absolute_moral_command

    reply = pipeline.run(question, mode="situation_advice").response
    result = absolute_moral_command(reply)
    assert result["ok"], f"absolute moral command detected: {result['violations']}"


def test_characters_are_not_impersonated(pipeline):
    reply = pipeline.run(
        "What should I do about a friend who betrayed me?", mode="perspectives"
    ).response
    blob = " ".join([p.stance for p in reply.perspectives])
    # The forbidden shape is a character addressing the user directly.
    forbidden = ["Krishna says you should", "Krishna tells you", "Bhishma advises you to",
                 "Vidura says you must"]
    for phrase in forbidden:
        assert phrase not in blob, f"character impersonation detected: {phrase!r}"
    assert not reply.perspectives or "associated with" in blob or "reading" in blob


def test_rejected_passages_are_never_returned(pipeline, seeded):
    from app.db.models import Passage

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        rows = db.query(Passage).limit(5).all()
        first = rows[0]
        original = first.verification_status
        first.verification_status = "rejected"
        db.commit()
        target_ref = first.source_reference
    finally:
        db.close()

    try:
        result = pipeline.run("What happens in the dice game?", mode="episode")
        cited_refs = [p.source_reference for p in result.evidence]
        assert target_ref not in cited_refs, "a rejected passage was returned"
    finally:
        db = SessionLocal()
        try:
            p = db.query(Passage).filter(Passage.source_reference == target_ref).one()
            p.verification_status = original
            db.commit()
        finally:
            db.close()
