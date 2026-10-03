"""Query expansion.

Takes a :class:`SituationAnalysis` and produces:

* ``lexical_terms``  -- expanded keyword terms for the BM25 channel
* ``semantic_query`` -- a condensed "retrieval query" for the embedding channel
* ``metadata``       -- parva / character / theme filters
* ``entity_terms``   -- characters and episode names worth boosting

Expansion is deliberately conservative: every added term must be traceable to
the user's own words or to the fixed taxonomy, so the retriever cannot drift
into topics the user never raised.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..knowledge.taxonomy import CHARACTERS, THEMES
from ..schemas import SituationAnalysis

# Theme slug -> extra retrieval words that appear in the source text but are
# not part of the modern phrasing the user would use.
THEME_SYNONYMS: dict[str, list[str]] = {
    "dharma": ["dharma", "righteousness", "duty", "right conduct"],
    "duty": ["duty", "own duty", "svadharma", "work that must be done"],
    "revenge": ["vengeance", "retaliation", "revenge", "avenging", "reprisal"],
    "forgiveness": ["forgiveness", "pardon", "forbearance", "clemency"],
    "self-control": ["self-control", "restraint", "control of the senses", "forbearance"],
    "justice": ["justice", "judgement", "redress", "vindication"],
    "loyalty": ["loyalty", "faithfulness", "allegiance"],
    "gratitude": ["gratitude", "repayment of debt", "obligation received"],
    "detachment": ["attachment to results", "fruit of action", "without desire for reward",
                   "detachment"],
    "recognition": ["honour", "credit", "renown", "glory", "recognition"],
    "perseverance": ["perseverance", "steadfast", "endure", "not giving up"],
    "silence": ["silence", "not speaking", "remaining silent", "held his tongue"],
    "counsel": ["counsel", "advice", "warning", "admonished"],
    "consequences": ["consequence", "aftermath", "bore the fruit", "result of action"],
    "identity": ["birth", "origin", "who he was", "identity", "lineage"],
    "anger": ["anger", "wrath", "fury", "rage"],
    "fear": ["fear", "dread", "afraid"],
    "grief": ["grief", "mourning", "lament", "consolation"],
    "power": ["kingdom", "throne", "rule", "sovereign", "governance"],
    "truth": ["truth", "truthful", "speaking the truth", "oath", "vow"],
    "nonviolence": ["non-violence", "ahimsa", "killing", "slaying"],
    "war": ["battle", "war", "fighting", "warriors"],
    "doubt": ["doubt", "hesitation", "conflicted", "uncertain"],
    "attachment-vs-duty": ["attachment", "kinship", "relatives", "one's own people"],
    "friendship-vs-morality": ["friend", "companion", "ally"],
    "truth-vs-loyalty": ["deception", "concealment", "speaking out"],
    "forgiveness-vs-self-respect": ["insult", "dishonour", "humiliation"],
    "revenge-vs-restraint": ["forbearance", "restraining", "checking oneself"],
    "fear-vs-responsibility": ["fear", "responsibility", "must be faced"],
    "family-vs-justice": ["kinsmen", "family", "relatives"],
    "ambition-vs-ethics": ["ambition", "advancement", "gain"],
    "duty-vs-interest": ["one's own interest", "self-interest", "desire"],
    "individual-vs-society": ["multitude", "people", "the public"],
    "responsibility": ["responsibility", "charge", "obligation", "burden"],
    "shame": ["shame", "dishonour"],
    "gambling": ["dice", "gambling", "stake", "wager"],
    "secrecy": ["secret", "concealed", "hidden"],
    "resistance": ["protest", "questioned", "resisted", "demanded"],
    "deception": ["deceit", "fraud", "trickery", "delusion"],
    "refusal-of-counsel": ["would not listen", "ignored", "rejected advice"],
}

_EPISODE_HINTS: dict[str, list[str]] = {
    "dice game": ["dice", "gambling", "ashtapada", "yudhishthira lost"],
    "exile": ["forest exile", "twelve years", "thirteen years", "vanavasa"],
    "war": ["Kurukshetra", "eighteen days", "great war", "Mahabharata war"],
}


@dataclass
class ExpandedQuery:
    semantic_query: str
    lexical_terms: list[str] = field(default_factory=list)
    entity_terms: list[str] = field(default_factory=list)
    theme_filters: list[str] = field(default_factory=list)
    character_filters: list[str] = field(default_factory=list)
    parva_hint: str = ""


def expand(analysis: SituationAnalysis, original: str, character: str | None = None) -> ExpandedQuery:
    slug_to_name = {t["slug"]: t["name"] for t in THEMES}
    slug_to_terms = {t["slug"]: t["slug"].replace("-", " ") for t in THEMES}

    theme_filters = [t for t in analysis.themes][:8]
    for value in analysis.values:
        slug = value.lower().replace(" vs ", "-").replace(" ", "-")
        if slug not in theme_filters:
            matched = next((s for s in slug_to_name if s == slug or s in value.lower()), None)
            if matched:
                theme_filters.append(matched)

    lexical: list[str] = []
    for slug in theme_filters:
        lexical.append(slug_to_terms.get(slug, slug.replace("-", " ")))
        lexical.extend(THEME_SYNONYMS.get(slug, []))

    lexical.extend(analysis.emotions)
    lexical.extend(analysis.values)
    # keep the user's own significant words
    for word in _content_words(original):
        lexical.append(word)

    entity_terms: list[str] = []
    character_filters = list(analysis.entities)
    if character and character not in character_filters:
        character_filters.insert(0, character)
    for slug in character_filters:
        for c in CHARACTERS:
            if c["slug"] == slug:
                entity_terms.append(c["name"])
                entity_terms.extend(c["aliases"][:2])
                break

    low = original.lower()
    for hint, words in _EPISODE_HINTS.items():
        if any(w.lower() in low for w in words):
            lexical.extend(words)

    # de-duplicate, preserve order, drop empties
    def _dedupe(seq: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for s in seq:
            s = s.strip()
            key = s.lower()
            if s and key not in seen:
                seen.add(key)
                out.append(s)
        return out

    semantic_bits = _dedupe(
        [analysis.conflict, *analysis.values, *analysis.themes[:5],
         *analysis.emotions, *entity_terms, _squash(original)]
    )

    return ExpandedQuery(
        semantic_query=" | ".join(b for b in semantic_bits if b)[:1200],
        lexical_terms=_dedupe(lexical)[:120],
        entity_terms=_dedupe(entity_terms),
        theme_filters=theme_filters,
        character_filters=character_filters,
        parva_hint="",
    )


def _content_words(text: str) -> list[str]:
    stop = {
        "the", "a", "an", "and", "or", "but", "if", "then", "i", "me", "my",
        "we", "our", "you", "your", "they", "them", "their", "is", "are", "was",
        "were", "be", "been", "am", "do", "does", "did", "have", "has", "had",
        "will", "would", "could", "should", "can", "may", "might", "must",
        "not", "no", "yes", "of", "to", "in", "on", "at", "for", "with", "from",
        "by", "as", "it", "its", "this", "that", "what", "which", "who", "how",
        "why", "when", "where", "about", "into", "so", "because", "than", "too",
        "very", "just", "now", "really", "much", "many", "some", "any", "all",
    }
    words = [w for w in re_words(text) if len(w) > 3 and w.lower() not in stop]
    return words[:40]


def re_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'\-]+", text)


def _squash(text: str, limit: int = 400) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "..."
