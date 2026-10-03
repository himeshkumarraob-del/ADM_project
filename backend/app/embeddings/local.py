"""Deterministic, dependency-free embedding provider.

Not a neural model: it hashes word uni/bi-grams and character trigrams into a
fixed-size signed feature vector and L2-normalises the result. Its purpose is
to make semantic retrieval *and the whole application* work offline and
reproducibly (tests, CI, demos) while the real providers (OpenAI, Gemini, …)
are drop-in replacements behind the same interface.

Cosine similarity between these vectors behaves like a soft lexical/semantic
overlap, which is exactly what the hybrid retriever needs from an embedding
channel.
"""

from __future__ import annotations

import hashlib
import re

from .base import l2_normalize

_WORD_RE = re.compile(r"[a-z0-9']+")

# Light stemming so "helping"/"helped"/"help" collide.
_SUFFIXES = (
    "ingly", "edly", "ations", "ation", "ments", "ment", "ings", "ing",
    "ies", "ied", "ies", "ier", "iest", "ness", "fully", "less",
    "ed", "es", "s", "ly", "er", "est", "d",
)


def _stem(token: str) -> str:
    if len(token) <= 3:
        return token
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 3:
            return token[: -len(suf)]
    return token


def _tokens(text: str) -> list[str]:
    return [_stem(w) for w in _WORD_RE.findall(text.lower())]


def _bucket(feature: str, dim: int) -> tuple[int, float]:
    digest = hashlib.md5(feature.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "little") % dim
    sign = 1.0 if digest[4] & 1 else -1.0
    return idx, sign


class LocalEmbeddingProvider:
    name = "local"
    model = "hashing-ngram-v1"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    # ------------------------------------------------------------------ #
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    # ------------------------------------------------------------------ #
    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        toks = _tokens(text)
        if not toks:
            return vec

        # word unigrams (weight 1.0), bigrams (weight 1.6), char trigrams (0.35)
        for tok in toks:
            idx, sign = _bucket("w:" + tok, self.dim)
            vec[idx] += sign * 1.0

        for a, b in zip(toks, toks[1:]):
            idx, sign = _bucket("b:" + a + "\x00" + b, self.dim)
            vec[idx] += sign * 1.6

        for tok in toks:
            padded = "^" + tok + "$"
            for i in range(len(padded) - 2):
                gram = padded[i : i + 3]
                idx, sign = _bucket("c:" + gram, self.dim)
                vec[idx] += sign * 0.35

        return l2_normalize(vec)
