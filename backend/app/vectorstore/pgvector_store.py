"""pgvector-backed store (``STORAGE_BACKEND=postgres``).

Requires the ``pgvector`` extension and, for exact ANN queries, the
``vector_native`` column maintained by :func:`app.db.session.init_db`.
Vectors are also mirrored into ``embeddings.vector`` (JSON) so that the data
survives a downgrade to the local backend.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import Embedding


class PgVectorStore:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory
        self._dim = settings.vector_dim

    def _key(self) -> tuple[str, str]:
        from ..embeddings import get_embedder

        e = get_embedder()
        return (e.name, e.model)

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
                payload = [float(x) for x in vec]
                if row is None:
                    db.add(
                        Embedding(
                            passage_id=pid,
                            provider=provider,
                            model=model,
                            dim=len(payload),
                            vector=payload,
                        )
                    )
                else:
                    row.dim = len(payload)
                    row.vector = payload
                db.flush()
                db.execute(
                    text(
                        "UPDATE embeddings SET vector_native = CAST(:v AS vector) "
                        "WHERE passage_id = :p AND provider = :pr AND model = :m"
                    ),
                    {"v": json.dumps(payload), "p": pid, "pr": provider, "m": model},
                )
            db.commit()
        finally:
            db.close()

    def search(
        self,
        vector: list[float],
        k: int,
        allowed_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        provider, model = self._key()
        params: dict = {"v": json.dumps([float(x) for x in vector]), "k": k,
                        "pr": provider, "m": model}
        sql = (
            "SELECT passage_id, 1 - (vector_native <=> CAST(:v AS vector)) AS sim "
            "FROM embeddings "
            "WHERE provider = :pr AND model = :m AND vector_native IS NOT NULL"
        )
        if allowed_ids is not None:
            if not allowed_ids:
                return []
            sql += " AND passage_id = ANY(:allowed)"
            params["allowed"] = list(allowed_ids)
        sql += " ORDER BY vector_native <=> CAST(:v AS vector) LIMIT :k"

        db: Session = self._session_factory()
        try:
            rows = db.execute(text(sql), params).all()
        except Exception:
            # Extension missing or column absent -> degrade to exact cosine in SQL.
            rows = self._fallback_search(db, params, k)
        finally:
            db.close()
        return [(r[0], float(r[1])) for r in rows]

    def _fallback_search(self, db: Session, params: dict, k: int) -> list:
        sql = (
            "SELECT passage_id, 1 - (embedding_json_cosine(vector, :v)) AS sim "
            "FROM embeddings WHERE provider = :pr AND model = :m"
        )
        if params.get("allowed"):
            sql += " AND passage_id = ANY(:allowed)"
        sql += " LIMIT 500"
        try:
            rows = db.execute(
                text(
                    "SELECT passage_id, vector FROM embeddings "
                    "WHERE provider = :pr AND model = :m"
                ),
                {"pr": params["pr"], "m": params["m"]},
            ).all()
        except Exception:
            return []
        import json as _json

        q = _json.loads(params["v"])
        qn = sum(x * x for x in q) ** 0.5 or 1.0
        allowed = params.get("allowed")
        scored: list[tuple[str, float]] = []
        for pid, vec_json in rows:
            if allowed and pid not in allowed:
                continue
            vec = vec_json if isinstance(vec_json, list) else _json.loads(vec_json)
            if len(vec) != len(q):
                continue
            vn = sum(x * x for x in vec) ** 0.5 or 1.0
            dot = sum(a * b for a, b in zip(vec, q))
            scored.append((pid, dot / (qn * vn)))
        scored.sort(key=lambda t: -t[1])
        return scored[:k]

    def delete(self, passage_ids: list[str]) -> None:
        if not passage_ids:
            return
        db: Session = self._session_factory()
        try:
            db.execute(
                text("DELETE FROM embeddings WHERE passage_id = ANY(:ids)"),
                {"ids": list(passage_ids)},
            )
            db.commit()
        finally:
            db.close()

    def count(self) -> int:
        provider, model = self._key()
        db: Session = self._session_factory()
        try:
            return int(
                db.execute(
                    text(
                        "SELECT COUNT(*) FROM embeddings WHERE provider = :pr AND model = :m"
                    ),
                    {"pr": provider, "m": model},
                ).scalar()
                or 0
            )
        finally:
            db.close()

    def clear_provider(self) -> None:
        provider, model = self._key()
        db: Session = self._session_factory()
        try:
            db.execute(
                text("DELETE FROM embeddings WHERE provider = :pr AND model = :m"),
                {"pr": provider, "m": model},
            )
            db.commit()
        finally:
            db.close()
