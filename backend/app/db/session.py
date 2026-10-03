"""Engine / session management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from .models import Base

_is_sqlite = settings.storage_backend != "postgres"

engine: Engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

if _is_sqlite:

    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables and enable the pgvector extension when using Postgres."""
    if settings.storage_backend == "postgres":
        with engine.begin() as conn:
            from pgvector.sqlalchemy import Vector  # noqa: F401  (registers the type)

            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=engine)
    _ensure_pg_vector_column()


def _ensure_pg_vector_column() -> None:
    """Add a native ``vector`` column when running on PostgreSQL.

    The ORM keeps vectors as JSON for portability; the extra column exists only
    so that pgvector can serve ``ORDER BY vector <=> :q`` queries.
    """
    if settings.storage_backend != "postgres":
        return
    from sqlalchemy import text

    dim = settings.vector_dim
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='embeddings' AND column_name='vector_native'"
            )
        ).first()
        if not exists:
            conn.exec_driver_sql(f"ALTER TABLE embeddings ADD COLUMN vector_native vector({dim})")
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_native "
            "ON embeddings USING hnsw (vector_native vector_cosine_ops)"
        )


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope for scripts and background jobs."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
