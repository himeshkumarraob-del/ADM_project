"""Vector store protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VectorStore(Protocol):
    def upsert(self, items: list[tuple[str, list[float]]]) -> None:
        """Store (passage_id, vector) pairs for the active provider/model."""
        ...

    def search(
        self,
        vector: list[float],
        k: int,
        allowed_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Return up to ``k`` (passage_id, cosine_similarity) pairs, best first."""
        ...

    def delete(self, passage_ids: list[str]) -> None: ...

    def count(self) -> int: ...

    def clear_provider(self) -> None:
        """Drop every vector belonging to the active provider/model."""
        ...
