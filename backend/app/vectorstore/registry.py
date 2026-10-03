"""Vector store registry."""

from __future__ import annotations

from functools import lru_cache

from ..config import settings
from ..db.session import SessionLocal
from .base import VectorStore

__all__ = ["get_vector_store", "VectorStore"]


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    if settings.storage_backend == "postgres":
        from .pgvector_store import PgVectorStore

        return PgVectorStore(SessionLocal)
    from .local import LocalVectorStore

    return LocalVectorStore(SessionLocal)
