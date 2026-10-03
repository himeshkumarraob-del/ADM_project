"""Embedding provider registry."""

from __future__ import annotations

from functools import lru_cache

from ..config import settings
from .base import EmbeddingProvider, l2_normalize
from .local import LocalEmbeddingProvider

__all__ = ["get_embedder", "EmbeddingProvider", "l2_normalize", "LocalEmbeddingProvider"]


@lru_cache(maxsize=1)
def get_embedder() -> EmbeddingProvider:
    provider = settings.embedding_provider
    if provider == "openai":
        from .remote import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider()
    if provider == "gemini":
        from .remote import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider()
    if provider == "local":
        return LocalEmbeddingProvider(dim=settings.vector_dim)
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider!r}")
