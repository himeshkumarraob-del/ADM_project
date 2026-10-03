"""Evidence validation, support levels and safety notices."""

from __future__ import annotations

from app.rag.evidence import INSUFFICIENT_NOTE, validate_evidence
from app.rag.guardrails import safety_notices
from app.schemas import EvidencePassage, SituationAnalysis


def _passage(**kw) -> EvidencePassage:
    base = dict(
        id="p1", parva="Sabha Parva", source_reference="Sabha Parva — test",
        summary="A summary of the episode.", quote="", verification_status="verified",
        is_primary_text=True, relevance=0.9, text_type="summary",
    )
    base.update(kw)
    return EvidencePassage(**base)


def test_strong_support_requires_verified_primary_source_text():
    analysis = SituationAnalysis(values=["dharma"], themes=["dharma"])
    ev = validate_evidence([_passage(text_type="prose", quote="A verified translation.")], analysis)
    assert ev.support_level == "strong_textual_support"
    assert ev.note == ""


def test_editorial_summary_cannot_claim_strong_textual_support():
    analysis = SituationAnalysis(values=["dharma"], themes=["dharma"])
    ev = validate_evidence([_passage()], analysis)
    assert ev.support_level == "interpretive"


def test_unverified_passage_cannot_claim_strong_support():
    analysis = SituationAnalysis(values=["dharma"], themes=["dharma"])
    ev = validate_evidence([_passage(verification_status="unverified")], analysis)
    assert ev.support_level == "interpretive"
    assert "interpretation" in ev.note


def test_non_primary_source_cannot_claim_strong_support():
    analysis = SituationAnalysis(values=["dharma"], themes=["dharma"])
    ev = validate_evidence([_passage(is_primary_text=False)], analysis)
    assert ev.support_level == "interpretive"


def test_low_relevance_is_insufficient():
    analysis = SituationAnalysis()
    ev = validate_evidence([_passage(relevance=0.001)], analysis)
    assert ev.support_level == "insufficient_evidence"


def test_rejected_passages_are_dropped():
    analysis = SituationAnalysis(values=["dharma"], themes=["dharma"])
    ev = validate_evidence(
        [_passage(verification_status="rejected"), _passage(id="p2", relevance=0.6)],
        analysis,
    )
    assert "p1" in ev.dropped
    assert all(p.id != "p1" for p in ev.passages)
    assert ev.usable


def test_no_passages_gives_documented_refusal():
    analysis = SituationAnalysis()
    ev = validate_evidence([], analysis)
    assert ev.support_level == "insufficient_evidence"
    assert ev.note == INSUFFICIENT_NOTE
    assert ev.usable is False


# --------------------------------------------------------------------------- #
def test_crisis_message_supersedes_other_notices():
    notices = safety_notices("I don't want to live anymore, I want to end my life")
    assert notices[0].kind == "crisis"
    assert "emergency" in notices[0].message.lower()
    assert all(n.kind != "general" for n in notices)


def test_medical_disclaimer_present_for_health_questions():
    notices = safety_notices("I was diagnosed with a serious illness, what should I do")
    assert any(n.kind == "medical" for n in notices)


def test_legal_and_financial_disclaimers():
    assert any(n.kind == "legal" for n in safety_notices("My partner wants to sue me"))
    assert any(n.kind == "financial" for n in safety_notices("Should I invest in stocks"))


def test_general_disclaimer_by_default():
    notices = safety_notices("Should I help a friend who keeps asking for money?")
    assert notices and notices[0].kind == "general"


# --------------------------------------------------------------------------- #
def test_perspectives_attribute_rather_than_impersonate():
    from app.rag.generation import _perspectives_for

    analysis = SituationAnalysis(entities=["krishna", "vidura"], values=["duty"])
    evidence = [
        _passage(id="a", characters=["Krishna"], speaker="Krishna", listener="Arjuna",
                 source_reference="Bhagavad Gita 2.47 (Bhishma Parva)"),
        _passage(id="b", characters=["Vidura"], speaker="Vidura",
                 listener="Dhritarashtra", parva="Shanti Parva",
                 source_reference="Shanti Parva — Vidura Niti"),
    ]
    perspectives = _perspectives_for(analysis, evidence, "perspectives")
    assert perspectives, "expected at least one perspective"
    for p in perspectives:
        assert p.stance
        assert "associated with" in p.stance or "reading" in p.stance
        assert p.passage_ids, "perspective is not backed by a passage"
        assert "interpretation" in p.basis.lower()
