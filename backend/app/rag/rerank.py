"""Evidence re-ranking.

Re-scores the fused candidates against the *dilemma* rather than against the
raw query. A passage that merely name-drops a famous character should not beat
a passage that actually stages the user's conflict, so re-ranking weights:

* conflict / value overlap with the analysed situation
* character relevance (people the analysis put at the centre)
* source quality: verified > unverified; primary text > retelling
* whether the passage carries a real quotation (verse/prose) vs. only a summary
* a light length prior that favours passages long enough to be quotable

The output is a single monotone ``relevance`` in 0..1 used everywhere
downstream (top-k cut, support-level classification, citation display).
"""

from __future__ import annotations

from ..config import settings
from ..knowledge.taxonomy import CHARACTERS, THEMES
from ..schemas import EvidencePassage, SituationAnalysis

_CHAR_BY_SLUG = {c["slug"]: c for c in CHARACTERS}
_THEME_TERMS = {
    t["slug"]: {t["slug"], *t["name"].lower().split(), *t["slug"].replace("-", " ").split()}
    for t in THEMES
}


def _text(p: EvidencePassage) -> str:
    return " ".join([p.summary, p.quote, p.parva, p.section, " ".join(p.themes)]).lower()


def _value_overlap(analysis: SituationAnalysis, p: EvidencePassage) -> float:
    if not analysis.values and not analysis.themes:
        return 0.0
    blob = _text(p)
    wanted: set[str] = set()
    for v in analysis.values:
        wanted |= _THEME_TERMS.get(v.lower().replace(" vs ", "-").replace(" ", "-"), {v.lower()})
    for t in analysis.themes:
        wanted |= _THEME_TERMS.get(t, {t.replace("-", " ")})
    if not wanted:
        return 0.0
    hits = sum(1 for w in wanted if len(w) > 3 and w in blob)
    return min(1.0, hits / max(2, len(wanted) // 2))


def _character_overlap(analysis: SituationAnalysis, p: EvidencePassage) -> float:
    if not analysis.entities:
        return 0.0
    present = {c.lower() for c in p.characters}
    present |= {(p.speaker or "").lower(), (p.listener or "").lower()}
    hits = 0
    for slug in analysis.entities:
        c = _CHAR_BY_SLUG.get(slug)
        names = [c["name"].lower(), *[a.lower() for a in c["aliases"]]] if c else [slug]
        if any(n in present for n in names):
            hits += 1
    return hits / max(1, len(analysis.entities))


def _source_quality(p: EvidencePassage) -> float:
    score = 0.55
    if p.verification_status == "verified":
        score += 0.30
    elif p.verification_status == "rejected":
        score -= 0.45
    if p.is_primary_text:
        score += 0.10
    if p.quote and p.text_type in {"verse", "prose"}:
        score += 0.05
    return max(0.0, min(1.0, score))


def _length_prior(p: EvidencePassage) -> float:
    n = len((p.quote or "") + (p.summary or ""))
    if n < 80:
        return 0.4
    if n > 400:
        return 0.85
    return 1.0


def rerank(
    candidates: list[EvidencePassage],
    analysis: SituationAnalysis,
    query: str,
    top_k: int | None = None,
) -> list[EvidencePassage]:
    top_k = top_k or settings.rerank_top_k
    if not candidates:
        return []

    low_query = query.lower()
    out: list[EvidencePassage] = []
    for p in candidates:
        base = max(p.relevance, 1e-6)
        score = (
            0.42 * min(1.0, base * 1.6)
            + 0.22 * _value_overlap(analysis, p)
            + 0.12 * _character_overlap(analysis, p)
            + 0.16 * _source_quality(p)
            + 0.08 * _length_prior(p)
        )
        # tiny lexical tie-breaker on rare tokens from the user's own text
        if any(tok in _text(p) for tok in low_query.split() if len(tok) > 6):
            score += 0.03
        p.relevance = round(min(1.0, score), 4)
        out.append(p)

    out.sort(key=lambda p: -p.relevance)
    return [p for p in out if p.relevance >= settings.min_relevance_cut][:top_k]


def required_evidence_count(passages: list[EvidencePassage]) -> int:
    return sum(1 for p in passages if p.relevance >= settings.strong_support_threshold)
