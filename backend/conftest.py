"""Pytest bootstrap.

The environment must be configured *before* any ``app.*`` module is imported,
because ``app.config`` snapshots settings at import time. This file therefore
only sets ``os.environ`` and exposes fixtures; it does not import the app.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

_TMP = Path(tempfile.mkdtemp(prefix="mhwisdom_test_"))

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "STORAGE_BACKEND": "local",
        "SQLITE_PATH": str(_TMP / "test.db"),
        "EMBEDDING_PROVIDER": "local",
        "LLM_PROVIDER": "none",
        "GENERATOR": "template",
        "ANALYST": "rule",
        "AUTH_REQUIRED": "false",
        "CORS_ORIGINS": "http://localhost:3000",
        "LOG_LEVEL": "WARNING",
    }
)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def seeded():
    """Initialise the schema and ingest the seed corpus once per session."""
    from app.corpus.ingest import ingest_corpus
    from app.db.models import Character, Passage, Source, Theme
    from app.db.session import init_db, session_scope
    from app.security import ensure_admin_user

    init_db()
    report = ingest_corpus()
    with session_scope() as db:
        ensure_admin_user(db)
        counts = {
            "passages": db.query(Passage).count(),
            "sources": db.query(Source).count(),
            "themes": db.query(Theme).count(),
            "characters": db.query(Character).count(),
        }
    return {"report": report, "counts": counts}


@pytest.fixture(scope="session")
def pipeline(seeded):
    from app.rag.pipeline import get_pipeline

    p = get_pipeline()
    p.invalidate()
    return p


@pytest.fixture(scope="session")
def client(seeded):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    shutil.rmtree(_TMP, ignore_errors=True)
