"""20. Evaluation suite tests."""

from __future__ import annotations

from app.eval.runner import run_evaluation


def test_evaluation_runs_and_reports_metrics(pipeline, seeded):
    results = run_evaluation(pipeline=pipeline)
    metrics = results["metrics"]

    assert metrics["questions"] >= 10
    # No fabricated quotations or references anywhere in the suite.
    assert metrics["hallucination_rate"] == 0.0, metrics
    # Every citation must resolve to a stored passage with a matching reference.
    assert metrics["citation_accuracy"] == 1.0, metrics
    # Absolute moral commands must never appear.
    assert metrics["no_absolute_commands_rate"] == 1.0, metrics
    # The text / interpretation layering must be present in essentially every
    # non-refusal answer.
    assert metrics["text_interpretation_distinction_rate"] >= 0.9, metrics
    # Safety notices are attached to every answer.
    assert metrics["safety_notice_rate"] == 1.0, metrics
    # Retrieval must actually surface material for the answerable questions.
    assert metrics["retrieval_coverage"] >= 0.7, metrics
    assert metrics["theme_relevance_rate"] >= 0.6, metrics
    # Canary questions with no support in the corpus must be refused.
    canaries = [r for r in results["results"]
                if r["expected"] == "insufficient"]
    assert canaries, "dataset must contain canary questions"
    for c in canaries:
        assert c["support_level"] == "insufficient_evidence", c
        assert c["refusal_ok"], c


def test_evaluation_is_deterministic(pipeline):
    first = run_evaluation(pipeline=pipeline)["metrics"]
    second = run_evaluation(pipeline=pipeline)["metrics"]
    assert first == second, "evaluation must be reproducible"


def test_faithfulness_is_reported_as_a_proxy(pipeline):
    results = run_evaluation(pipeline=pipeline)
    assert "proxy" in results["disclaimer"]
    value = results["metrics"]["answer_faithfulness_proxy"]
    assert value is None or 0.0 <= value <= 1.0
