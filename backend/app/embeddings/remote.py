"""HTTP embedding providers (OpenAI, Gemini)."""

from __future__ import annotations

import httpx

from ..config import settings
from .base import l2_normalize


class _HttpEmbeddingBase:
    name = "remote"
    model = ""
    dim = 0

    def __init__(self) -> None:
        self.timeout = settings.http_timeout_seconds

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @staticmethod
    def _normalize(rows: list[list[float]]) -> list[list[float]]:
        return [l2_normalize(r) for r in rows]


class OpenAIEmbeddingProvider(_HttpEmbeddingBase):
    name = "openai"

    def __init__(self) -> None:
        super().__init__()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for EMBEDDING_PROVIDER=openai")
        self.model = settings.openai_embedding_model
        self.dim = settings.vector_dim
        self._client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=self.timeout,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        # batch to stay well under request limits
        for i in range(0, len(texts), 64):
            chunk = texts[i : i + 64]
            resp = self._client.post(
                "/embeddings", json={"model": self.model, "input": chunk}
            )
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            out.extend([row["embedding"] for row in data])
        return self._normalize(out)


class GeminiEmbeddingProvider(_HttpEmbeddingBase):
    name = "gemini"

    def __init__(self) -> None:
        super().__init__()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for EMBEDDING_PROVIDER=gemini")
        self.model = settings.gemini_embedding_model
        self.dim = settings.vector_dim
        self._client = httpx.Client(timeout=self.timeout)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            resp = self._client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:embedContent",
                params={"key": settings.gemini_api_key},
                json={"model": f"models/{self.model}", "content": {"parts": [{"text": text}]}},
            )
            resp.raise_for_status()
            out.append(resp.json()["embedding"]["values"])
        return self._normalize(out)
