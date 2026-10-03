"""BM25 keyword index over the passage corpus.

The keyword channel complements semantic search: proper names, episode titles
and rare technical terms ("dice game", "Vidura", "Gandhari") are often lost in
embedding space but dominate the exact-match signal.

The index is built in-process from the ``passages`` table and cached; any
ingest/verify/delete operation calls :meth:`invalidate`.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from ..db.models import Passage

_WORD = re.compile(r"[a-z0-9']+")

_STOP = {
    "the", "a", "an", "and", "or", "but", "if", "then", "of", "to", "in",
    "on", "at", "for", "with", "from", "by", "as", "is", "are", "was", "were",
    "be", "been", "being", "it", "its", "this", "that", "these", "those", "i",
    "me", "my", "we", "our", "you", "your", "they", "them", "their", "he",
    "she", "his", "her", "do", "does", "did", "have", "has", "had", "will",
    "would", "could", "should", "can", "not", "no", "yes", "at", "into",
    "what", "which", "who", "whom", "how", "why", "when", "where",
}

_SUFFIXES = (
    "ingly", "edly", "ations", "ation", "ments", "ment", "ings", "ing",
    "ies", "ied", "ier", "iest", "ness", "ed", "es", "s", "ly", "er", "est", "d",
)


def _stem(token: str) -> str:
    if len(token) <= 3:
        return token
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 3:
            return token[: -len(suf)]
    return token


def tokenize(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(text.lower()):
        if w in _STOP:
            continue
        out.append(_stem(w))
    return out


class BM25Index:
    """Okapi BM25 over passage text + metadata."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._loaded = False
        self._ids: list[str] = []
        self._len: list[float] = []
        self._df: dict[str, int] = defaultdict(int)
        self._tf: list[Counter] = []
        self._avg_len: float = 0.0
        self._cache: dict[str, float] = {}

    # ------------------------------------------------------------------ #
    def invalidate(self) -> None:
        self._loaded = False
        self._cache.clear()

    def load(self, session_factory) -> None:
        if self._loaded:
            return
        db: Session = session_factory()
        try:
            rows = db.query(Passage).all()
        finally:
            db.close()
        self._ids, self._len, self._tf = [], [], []
        self._df = defaultdict(int)
        for p in rows:
            blob = " ".join(
                [
                    p.parva or "",
                    p.section or "",
                    p.chapter or "",
                    p.speaker or "",
                    p.listener or "",
                    " ".join(p.characters or []),
                    " ".join(p.themes or []),
                    " ".join(p.keywords or []),
                    " ".join(p.events or []),
                    p.source_reference or "",
                    p.summary or "",
                    p.translation or "",
                ]
            )
            tokens = tokenize(blob)
            tf = Counter(tokens)
            self._ids.append(p.id)
            self._tf.append(tf)
            self._len.append(max(1, len(tokens)))
            for term in tf:
                self._df[term] += 1
        total = sum(self._len)
        self._avg_len = (total / len(self._len)) if self._len else 1.0
        self._loaded = True
        self._cache.clear()

    # ------------------------------------------------------------------ #
    def search(
        self,
        terms: list[str],
        k: int,
        allowed_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Return (passage_id, score) with scores normalised to roughly 0..1."""
        if not self._ids:
            return []
        n = len(self._ids)
        query_tokens: list[str] = []
        for t in terms:
            query_tokens.extend(tokenize(t))
        if not query_tokens:
            return []

        scores = [0.0] * n
        for term, _weight in Counter(query_tokens).items():
            df = self._df.get(term)
            if not df:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i, tf in enumerate(self._tf):
                f = tf.get(term)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * self._len[i] / self._avg_len)
                scores[i] += idf * (f * (self.k1 + 1)) / denom

        best = max(scores) or 1.0
        ranked = []
        for i, s in enumerate(scores):
            if s <= 0:
                continue
            pid = self._ids[i]
            if allowed_ids is not None and pid not in allowed_ids:
                continue
            ranked.append((pid, s / best))
        ranked.sort(key=lambda t: -t[1])
        return ranked[:k]

    @property
    def size(self) -> int:
        return len(self._ids)


_index: BM25Index | None = None


def get_keyword_index() -> BM25Index:
    global _index
    if _index is None:
        _index = BM25Index()
    return _index
