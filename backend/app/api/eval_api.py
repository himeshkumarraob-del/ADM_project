"""20. Evaluation endpoints.

Runs the offline evaluation suite: retrieval relevance, citation accuracy,
hallucination rate, answer faithfulness, and whether the text/interpretation
distinction is actually present in the output.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.models import EvalRun
from ..db.session import get_db
from ..eval.runner import run_evaluation

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run")
def run(dataset: str = "default", db: Session = Depends(get_db)) -> dict:
    try:
        results = run_evaluation(dataset=dataset)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    run_row = EvalRun(dataset=dataset, generator=results.get("generator", ""), results=results)
    db.add(run_row)
    db.commit()
    results["run_id"] = run_row.id
    return results


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), limit: int = 20) -> list[dict]:
    rows = db.query(EvalRun).order_by(EvalRun.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id, "dataset": r.dataset, "generator": r.generator,
            "created_at": r.created_at.isoformat(),
            "metrics": r.results.get("metrics", {}),
        }
        for r in rows
    ]


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    row = db.get(EvalRun, run_id)
    if row is None:
        raise HTTPException(404, "Run not found")
    return {
        "id": row.id, "dataset": row.dataset, "generator": row.generator,
        "created_at": row.created_at.isoformat(), "results": row.results,
    }
