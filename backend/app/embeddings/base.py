"""Embedding provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class EmbeddingProvider(Protocol):
    name: str
    model: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one L2-normalised vector per input text."""
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


def l2_normalize(vec: list[float]) -> list[float]:
    total = sum(v * v for v in vec)
    if total <= 0:
        return vec
    inv = 1.0 / (total ** 0.5)
    return [v * inv for v in vec]
