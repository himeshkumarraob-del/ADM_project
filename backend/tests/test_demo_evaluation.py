"""Test suite for the 23 demo evaluation scenarios."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.eval.checks import (
    absolute_moral_command,
    citation_validity,
    distinction_present,
    quotation_invention_rate,
)
from app.rag.expansion import expand
from app.db.session import SessionLocal
from app.db.models import Passage

SCENARIOS_PATH = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "demo_scenarios.json"


@pytest.fixture(scope="module")
def scenarios():
    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_demo_scenarios_exist_and_cover_required_topics(scenarios):
    assert len(scenarios) >= 20
    topics = {s["topic"] for s in scenarios}
    assert any("Duty" in t for t in topics)
    assert any("Revenge" in t for t in topics)
    assert any("Loyalty" in t for t in topics)
    assert any("Anger" in t for t in topics)
    assert any("Leadership" in t for t in topics)
    assert any("Karna Parva" in t for t in topics)
    assert any("Shalya Parva" in t for t in topics)


def test_missing_parva_and_out_of_domain_canaries_refuse(pipeline, scenarios):
    canaries = [s for s in scenarios if s.get("insufficient_evidence_expected")]
    assert len(canaries) >= 3
    for c in canaries:
        res = pipeline.run(query=c["query"], mode=c.get("mode", "source_explorer"), language="en").response
        assert res.support_level == "insufficient_evidence", f"Failed to refuse canary: {c['id']} ({c['topic']})"
        assert len(res.primary_text) == 0


def test_answerable_scenarios_retrieve_relevant_parvas_and_citations(pipeline, scenarios):
    db = SessionLocal()
    try:
        ref_by_id = {p.id: p.source_reference for p in db.query(Passage).all()}
    finally:
        db.close()

    answerable = [s for s in scenarios if not s.get("insufficient_evidence_expected")]
    for s in answerable:
        res = pipeline.run(query=s["query"], mode=s.get("mode", "situation_advice"), language="en").response
        assert res.support_level != "insufficient_evidence", f"Incorrectly refused valid query: {s['id']}"
        assert len(res.primary_text) > 0

        # Citations must be clean
        cite = citation_validity(res, res.primary_text, ref_by_id)
        assert not cite["fabricated"], f"Fabricated citations in {s['id']}: {cite}"

        # Grounding check must be clean
        inv = quotation_invention_rate(res, res.primary_text)
        assert inv["clean"], f"Unclean grounding in {s['id']}: {inv}"

        # No absolute moral commands
        cmd = absolute_moral_command(res)
        assert cmd["ok"], f"Absolute moral command detected in {s['id']}: {cmd}"

        # Text vs interpretation distinction
        dist = distinction_present(res)
        assert dist["distinction_present"], f"Missing text/interpretation distinction in {s['id']}"
