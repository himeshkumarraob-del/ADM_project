"""Local (no external service) vector store.

Vectors are persisted in the ``embeddings`` table as JSON float lists and
loaded into a NumPy matrix for brute-force cosine search. A small in-process
cache avoids re-reading the table on every request; any write invalidates it.

Brute force is comfortably fast for the corpus sizes this backend targets
(tens of thousands of chunks); beyond that, switch ``STORAGE_BACKEND=postgres``
and use the pgvector store.
"""

from __future__ import annotations

import numpy as np
from sqlalchemy import delete as sa_delete
from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import Embedding


class LocalVectorStore:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory
        self._ids: list[str] | None = None
        self._matrix: np.ndarray | None = None
        self._provider_key: tuple[str, str] | None = None

    # ------------------------------------------------------------------ #
    def _key(self) -> tuple[str, str]:
        from ..embeddings import get_embedder

        e = get_embedder()
        return (e.name, e.model)

    def invalidate(self) -> None:
        self._ids = None
        self._matrix = None
        self._provider_key = None

    def _load(self) -> None:
        provider, model = self._key()
        if self._ids is not None and self._provider_key == (provider, model):
            return
        db: Session = self._session_factory()
        try:
            rows = (
                db.query(Embedding.passage_id, Embedding.vector)
                .filter(Embedding.provider == provider, Embedding.model == model)
                .all()
            )
        finally:
            db.close()
        ids = [r[0] for r in rows]
        if rows:
            matrix = np.asarray([r[1] for r in rows], dtype=np.float32)
            # guard against malformed rows
            if matrix.ndim != 2 or matrix.shape[1] != settings.vector_dim:
                good = [(i, v) for i, v in rows if len(v) == settings.vector_dim]
                ids = [g[0] for g in good]
                matrix = (
                    np.asarray([g[1] for g in good], dtype=np.float32)
                    if good
                    else np.zeros((0, settings.vector_dim), dtype=np.float32)
                )
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            matrix = matrix / norms
        else:
            matrix = np.zeros((0, settings.vector_dim), dtype=np.float32)
        self._ids = ids
        self._matrix = matrix
        self._provider_key = (provider, model)

    # ------------------------------------------------------------------ #
    def upsert(self, items: list[tuple[str, list[float]]]) -> None:
        if not items:
            return
        provider, model = self._key()
        db: Session = self._session_factory()
        try:
            for pid, vec in items:
                row = (
                    db.query(Embedding)
                    .filter(
                        Embedding.passage_id == pid,
                        Embedding.provider == provider,
                        Embedding.model == model,
                    )
                    .one_or_none()
                )
                if row is None:
                    db.add(
                        Embedding(
                            passage_id=pid,
                            provider=provider,
                            model=model,
                            dim=len(vec),
                            vector=[float(x) for x in vec],
                        )
                    )
                else:
                    row.dim = len(vec)
                    row.vector = [float(x) for x in vec]
            db.commit()
        finally:
            db.close()
        self.invalidate()

    def search(
        self,
        vector: list[float],
        k: int,
        allowed_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        self._load()
        assert self._matrix is not None and self._ids is not None
        if self._matrix.shape[0] == 0:
            return []
        q = np.asarray(vector, dtype=np.float32)
        n = np.linalg.norm(q)
        if n > 0:
            q = q / n
        sims = self._matrix @ q
        order = np.argsort(-sims)
        out: list[tuple[str, float]] = []
        for idx in order:
            pid = self._ids[int(idx)]
            if allowed_ids is not None and pid not in allowed_ids:
                continue
            out.append((pid, float(sims[int(idx)])))
            if len(out) >= k:
                break
        return out

    def delete(self, passage_ids: list[str]) -> None:
        if not passage_ids:
            return
        db: Session = self._session_factory()
        try:
            db.execute(sa_delete(Embedding).where(Embedding.passage_id.in_(passage_ids)))
            db.commit()
        finally:
            db.close()
        self.invalidate()

    def count(self) -> int:
        self._load()
        return 0 if self._ids is None else len(self._ids)

    def clear_provider(self) -> None:
        provider, model = self._key()
        db: Session = self._session_factory()
        try:
            db.execute(
                sa_delete(Embedding).where(
                    Embedding.provider == provider, Embedding.model == model
                )
            )
            db.commit()
        finally:
            db.close()
        self.invalidate()
