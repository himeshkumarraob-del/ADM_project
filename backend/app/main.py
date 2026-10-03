"""FastAPI application entry point.

Run with::

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .db.session import init_db, session_scope
from .security import ensure_admin_user

logger = logging.getLogger("mahabharata")
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


def _bootstrap() -> None:
    """Create schema, the admin account, and load the corpus if it is empty."""
    from .db.models import Passage

    init_db()
    with session_scope() as db:
        ensure_admin_user(db)
        empty = db.query(Passage.id).first() is None
    if empty:
        try:
            from .corpus.ingest import ingest_corpus

            report = ingest_corpus()
            logger.info("Corpus ingested on first boot: %s", report.as_dict())
        except Exception:  # noqa: BLE001 - boot must not fail on a bad file
            logger.exception("Corpus ingestion failed; continuing with an empty index")
    else:
        # make sure the keyword index is warm
        try:
            from .index import get_keyword_index
            from .rag.pipeline import get_pipeline

            get_pipeline().invalidate()
            get_keyword_index().invalidate()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to warm the retrieval index")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _bootstrap()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=(
            "A source-grounded AI companion for exploring wisdom and dilemmas "
            "through the Mahabharata attributed to Maharishi Veda Vyasa."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    from .api import admin, auth, chat, eval_api, explore

    app.include_router(chat.router, prefix=prefix)
    app.include_router(explore.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(eval_api.router, prefix=prefix)

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {
            "name": settings.app_name,
            "tagline": (
                "A source-grounded AI companion for exploring wisdom and dilemmas "
                "through the Mahabharata."
            ),
            "storage_backend": settings.storage_backend,
            "embedding_provider": settings.embedding_provider,
            "generator": settings.effective_generator,
            "analyst": settings.effective_analyst,
            "llm_provider": settings.llm_provider,
            "auth_required": settings.auth_required,
            "docs": "/docs",
        }

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        from .db.session import SessionLocal
        from .db.models import Passage
        from .vectorstore import get_vector_store

        try:
            with SessionLocal() as db:
                passages = db.query(Passage.id).count()
            return {
                "status": "ok",
                "passages": passages,
                "vectors": get_vector_store().count(),
            }
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=503,
                content={"status": "degraded", "error": f"{type(exc).__name__}: {exc}"},
            )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
