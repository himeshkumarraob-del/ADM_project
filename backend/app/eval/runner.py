"""20. Evaluation runner.

Executes every question in ``dataset.jsonl`` through the real pipeline and
reports:

* retrieval relevance (did the corpus surface anything, and did it match the
  expected themes / expected reference families?)
* source & citation accuracy (ids exist, references match the database)
* hallucination rate (quotation-/citation-shaped text not backed by evidence)
* answer faithfulness (lexical grounding proxy, reported as a proxy)
* text / interpretation distinction present
* safety-notice coverage
* canary behaviour: questions with no support must be refused

Run it with ``python -m scripts.run_eval`` or ``POST /api/eval/run``.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import settings
from ..db.session import SessionLocal
from ..db.models import Passage
from ..rag.pipeline import GuidancePipeline, get_pipeline
from .checks import (
    absolute_moral_command,
    citation_validity,
    distinction_present,
    faithfulness,
    quotation_invention_rate,
    supports_claim,
)

DATASET = Path(__file__).resolve().parent / "dataset.jsonl"


def _load_dataset(name: str) -> list[dict]:
    if name == "default" or not name.endswith(".jsonl"):
        path = DATASET
    else:
        path = Path(name)
    if not path.exists():
        raise FileNotFoundError(f"evaluation dataset not found: {path}")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def run_evaluation(dataset: str = "default",
                   pipeline: GuidancePipeline | None = None,
                   language: str = "en") -> dict:
    items = _load_dataset(dataset)
    pipe = pipeline or get_pipeline()

    db = SessionLocal()
    try:
        ref_by_id = {p.id: p.source_reference for p in db.query(Passage).all()}
    finally:
        db.close()

    results = []
    tallies = {
        "total": 0,
        "retrieval_nonempty": 0,
        "retrieval_expected_theme_hit": 0,
        "retrieval_expected_reference_hit": 0,
        "refused_when_expected": 0,
        "refusal_incorrect": 0,
        "clean_grounding": 0,
        "citation_clean": 0,
        "distinction_present": 0,
        "no_absolute_commands": 0,
        "safety_notice_present": 0,
        "faithfulness_sum": 0.0,
        "faithfulness_n": 0,
        "distinction_denominator": 0,
    }

    for item in items:
        reply = pipe.run(
            query=item["question"],
            mode=item.get("mode", "situation_advice"),
            language=language,
            character=item.get("character"),
            include_perspectives=(item.get("mode") == "perspectives"),
        ).response
        evidence = reply.primary_text

        expected_themes = set(item.get("expect_themes", []))
        got_themes = set(reply.analysis.themes) | {t for p in evidence for t in p.themes}
        theme_hit = (not expected_themes) or bool(expected_themes & got_themes)

        refs = " | ".join(
            [reply.episode_reference or ""] + list(reply.sources)
        ).lower()
        expected_refs = item.get("expect_reference_any", [])
        ref_hit = (not expected_refs) or any(
            r.lower() in refs for r in expected_refs
        )

        expect = item.get("expect_support", "any_non_empty")
        refused = reply.support_level == "insufficient_evidence"
        if expect == "insufficient":
            refusal_ok = refused
        elif expect == "interpretive_or_strong":
            refusal_ok = (not refused) and reply.support_level in {
                "interpretive", "strong_textual_support"
            }
        else:
            refusal_ok = not refused

        if evidence:
            tallies["retrieval_nonempty"] += 1
        if theme_hit:
            tallies["retrieval_expected_theme_hit"] += 1
        if ref_hit:
            tallies["retrieval_expected_reference_hit"] += 1
        if expect == "insufficient" and refused:
            tallies["refused_when_expected"] += 1
        if expect != "insufficient" and refused:
            tallies["refusal_incorrect"] += 1

        inv = quotation_invention_rate(reply, evidence)
        if inv["clean"]:
            tallies["clean_grounding"] += 1

        cite = citation_validity(reply, evidence, ref_by_id)
        if not cite["fabricated"]:
            tallies["citation_clean"] += 1

        # Refusals carry no textual/interpretation layering by design; the
        # distinction metric is defined over answered questions only.
        dist = distinction_present(reply)
        if not refused:
            tallies["distinction_denominator"] += 1
            if dist["distinction_present"]:
                tallies["distinction_present"] += 1

        cmd = absolute_moral_command(reply)
        if cmd["ok"]:
            tallies["no_absolute_commands"] += 1

        want_notice = item.get("expect_safety_notice")
        kinds = {n.kind for n in reply.safety_notices}
        if want_notice:
            if want_notice in kinds:
                tallies["safety_notice_present"] += 1
        else:
            tallies["safety_notice_present"] += 1

        faith = faithfulness(reply, evidence)
        if reply.support_level != "insufficient_evidence":
            tallies["faithfulness_sum"] += faith["mean_coverage"]
            tallies["faithfulness_n"] += 1

        results.append(
            {
                "id": item["id"],
                "question": item["question"],
                "support_level": reply.support_level,
                "expected": expect,
                "retrieved": len(evidence),
                "top_reference": evidence[0].source_reference if evidence else None,
                "theme_hit": theme_hit,
                "reference_hit": ref_hit,
                "refusal_ok": refusal_ok,
                "grounding_clean": inv["clean"],
                "invented": inv,
                "citations": cite,
                "distinction": dist,
                "absolute_command": cmd,
                "faithfulness": faith,
                "safety_notices": sorted(kinds),
            }
        )

    n = max(1, len(items))
    n_canary = sum(1 for i in items if i.get("expect_support") == "insufficient")
    metrics = {
        "questions": len(items),
        "retrieval_coverage": round(tallies["retrieval_nonempty"] / n, 3),
        "theme_relevance_rate": round(tallies["retrieval_expected_theme_hit"] / n, 3),
        "reference_relevance_rate": round(tallies["retrieval_expected_reference_hit"] / n, 3),
        "refusal_accuracy": round(tallies["refused_when_expected"] / n_canary, 3)
        if n_canary
        else None,
        "incorrect_refusals": tallies["refusal_incorrect"],
        "hallucination_rate": round(1 - tallies["clean_grounding"] / n, 3),
        "citation_accuracy": round(tallies["citation_clean"] / n, 3),
        "text_interpretation_distinction_rate": round(
            tallies["distinction_present"]
            / max(1, tallies["distinction_denominator"]),
            3,
        ),
        "no_absolute_commands_rate": round(tallies["no_absolute_commands"] / n, 3),
        "safety_notice_rate": round(tallies["safety_notice_present"] / n, 3),
        "answer_faithfulness_proxy": (
            round(tallies["faithfulness_sum"] / tallies["faithfulness_n"], 3)
            if tallies["faithfulness_n"]
            else None
        ),
        "generator": pipe.generator.name,
        "analyst": pipe.analyst.name,
        "embedding_provider": settings.embedding_provider,
    }
    return {
        "dataset": dataset,
        "generator": pipe.generator.name,
        "metrics": metrics,
        "results": results,
        "disclaimer": (
            "faithfulness is a lexical-grounding proxy used for regression "
            "detection; it is not shown to users as a confidence score."
        ),
    }
