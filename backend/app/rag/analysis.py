"""6. Situation analysis.

Turns free text into a structured :class:`SituationAnalysis` that drives query
expansion and metadata filtering.

* :class:`RuleBasedAnalyst` -- deterministic lexicon/entity/conflict matcher.
  Always available; used for tests and whenever no LLM key is configured.
* :class:`LLMAnalyst` -- asks the configured model for the same schema and
  validates the output, falling back to the rule-based analyst on any failure.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from ..config import settings
from ..knowledge.taxonomy import (
    CHARACTERS,
    CONFLICT_PATTERNS,
    EMOTION_LEXICON,
    MODE_INTENT_HINTS,
    THEMES,
)
from ..schemas import SituationAnalysis

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")
_SENTENCE = re.compile(r"[^.?!]+[.?!]?")

# These labels frame a dilemma for retrieval and reflection; they do not rank
# choices or declare a single action to be Dharma.
_DHARMA_TENSIONS = {
    "competing duties": ("duty", "duty"),
    "attachment": ("attachment", "duty"),
    "truth": ("truth", "duty"),
    "loyalty": ("loyalty", "justice"),
    "justice": ("justice", "compassion"),
    "responsibility": ("responsibility", "personal desire"),
    "consequences": ("action", "consequences"),
    "self-control": ("self-control", "anger"),
    "personal desire": ("personal desire", "duty"),
    "uncertainty": ("uncertainty", "duty"),
}

# Words that are far too common to be treated as an entity.
_STOP = {
    "i", "me", "my", "we", "our", "us", "you", "your", "they", "them", "their",
    "he", "she", "him", "her", "his", "its", "it", "this", "that", "these",
    "those", "am", "is", "are", "was", "were", "be", "been", "being", "do",
    "does", "did", "have", "has", "had", "will", "would", "could", "should",
    "can", "may", "might", "must", "shall", "not", "no", "yes", "and", "but",
    "or", "if", "then", "than", "so", "because", "when", "while", "what",
    "which", "who", "whom", "how", "why", "where", "a", "an", "the", "of",
    "to", "in", "on", "at", "for", "with", "from", "by", "as", "into", "about",
}


class Analyst(Protocol):
    name: str

    def analyze(self, text: str, mode: str, character: str | None = None) -> SituationAnalysis:
        ...


# --------------------------------------------------------------------------- #
# Helpers shared by both analysts
# --------------------------------------------------------------------------- #
def detect_characters(text: str) -> list[str]:
    low = text.lower()
    found: list[str] = []
    for c in CHARACTERS:
        names = [c["name"], *c["aliases"]]
        if any(re.search(rf"\b{re.escape(n.lower())}\b", low) for n in names):
            found.append(c["slug"])
    return found


def detect_emotions(text: str) -> list[str]:
    low = text.lower()
    return [emo for emo, words in EMOTION_LEXICON.items() if any(w in low for w in words)]


def detect_conflicts(text: str) -> list[tuple[str, str]]:
    low = text.lower()
    hits: list[tuple[str, str]] = []
    for a, b, triggers in CONFLICT_PATTERNS:
        if any(t in low for t in triggers):
            hits.append((a, b))
    return hits


def detect_dharma_tensions(text: str) -> list[str]:
    """Recognise common Dharma-related tensions without resolving them."""
    low = text.lower()
    return [label for label in _DHARMA_TENSIONS if _has_word(low, label)]


_THEME_LEMMAS: dict[str, list[str]] = {
    "loyalty": ["loyal", "loyalty", "allegiance", "faithfulness"],
    "vows": ["vow", "vows", "pledge", "pledges", "oath", "oaths"],
    "truth": ["truth", "truthful", "honesty", "promise", "promises"],
    "revenge": ["revenge", "vengeance", "retaliate", "retaliation"],
    "forgiveness": ["forgive", "forgiving", "forgiveness", "pardon"],
    "detachment": ["detachment", "detached", "unattached"],
}


def _theme_hits(text: str) -> list[str]:
    """Themes named in ``text``, matched on **word boundaries**.

    A bare substring test lets "control" inside ``self-control`` fire on
    "controller", which gave an out-of-corpus Kubernetes question a theme -- and
    therefore an answerability anchor -- it could not possibly earn. Boundaries
    keep every legitimate match ("control my temper", "self-control") while
    rejecting incidental stems ("controller", "revengeful").
    """
    low = text.lower()
    hits: list[str] = []
    for t in THEMES:
        label = t["name"].lower()
        slug = t["slug"]
        slug_bits = slug.replace("-", " ").split()
        lemmas = _THEME_LEMMAS.get(slug, [])
        if (
            _has_word(low, label)
            or any(_has_word(low, w) for w in slug_bits if len(w) >= 4)
            or any(_has_word(low, lem) for lem in lemmas)
        ):
            hits.append(slug)
    return hits


def _has_word(low: str, term: str) -> bool:
    """True when ``term`` occurs in ``low`` as a whole word.

    Word boundaries on both sides: "control" must not fire inside
    "controller", and "war" must not fire inside "toward". Whitespace in the
    term is normalised so a multi-word label ("ambition vs ethics") still
    matches however the user spaced it.

    Erring toward *fewer* matches is deliberate: this signal feeds the
    answerability anchor, so a false positive answers a question the corpus
    cannot support, while a false negative merely refuses.
    """
    if not term:
        return False
    pattern = r"\b" + r"\s+".join(re.escape(p) for p in term.split()) + r"\b"
    return re.search(pattern, low) is not None


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.findall(text) if s.strip()]


def _leading_sentence(text: str, limit: int = 320) -> str:
    for s in _sentences(text):
        return s if len(s) <= limit else s[: limit - 1].rsplit(" ", 1)[0] + "..."
    trimmed = text.strip()
    return trimmed if len(trimmed) <= limit else trimmed[: limit - 1].rsplit(" ", 1)[0] + "..."


def _extract_people(text: str, entities: list[str]) -> list[str]:
    """Capitalised noun phrases that are not sentence-initial generics."""
    words = _WORD.findall(text)
    people: list[str] = []
    for w in words:
        if w[0].isupper() and w.lower() not in _STOP and len(w) > 2:
            if w not in people:
                people.append(w)
    # add role-ish nouns
    for role in ("friend", "partner", "boss", "colleague", "manager", "spouse",
                 "husband", "wife", "sibling", "parent", "child", "teacher",
                 "student", "neighbour", "neighbor", "client", "roommate",
                 "family", "team", "parents", "brother", "sister"):
        if re.search(rf"\b{role}\b", text.lower()) and role not in people:
            people.append(role)
    return people[:10]


# --------------------------------------------------------------------------- #
# Rule-based
# --------------------------------------------------------------------------- #
class RuleBasedAnalyst:
    name = "rule"

    def analyze(self, text: str, mode: str, character: str | None = None) -> SituationAnalysis:
        entities = detect_characters(text)
        if character and character not in entities:
            entities.insert(0, character)

        conflicts = detect_conflicts(text)
        dharma_tensions = detect_dharma_tensions(text)
        emotions = detect_emotions(text)
        themes = _theme_hits(text)

        values: list[str] = []
        conflict_label = ""
        for a, b in conflicts[:3]:
            values.extend([a, b])
            if not conflict_label:
                conflict_label = f"{a} vs {b}"
        for tension in dharma_tensions:
            a, b = _DHARMA_TENSIONS[tension]
            values.extend([a, b])
            if not conflict_label:
                conflict_label = f"{a} vs {b}"
        values = list(dict.fromkeys(values))

        # pull theme labels for display
        slug_to_name = {t["slug"]: t["name"] for t in THEMES}
        theme_names = [slug_to_name.get(s, s.replace("-", " ")) for s in themes[:8]]

        if not conflict_label and themes:
            conflict_label = slug_to_name.get(themes[0], themes[0])

        question = _infer_question(text, mode)

        # Seed retrieval themes with the conflict halves when nothing matched.
        retrieval_themes = list(themes)
        if not retrieval_themes and conflicts:
            retrieval_themes = [a.replace(" ", "-") for a, _ in conflicts]
        if not retrieval_themes and emotions:
            retrieval_themes = [e for e in emotions][:3]

        people = _extract_people(text, entities)
        character_names = [
            c["name"] for c in CHARACTERS if c["slug"] in entities
        ]

        return SituationAnalysis(
            situation=_leading_sentence(text),
            people=list(dict.fromkeys(character_names + people))[:10],
            conflict=conflict_label,
            values=values or theme_names[:4],
            emotions=emotions,
            question=question,
            themes=retrieval_themes,
            entities=entities,
            analysis_method="rule",
        )


def _infer_question(text: str, mode: str) -> str:
    for s in _sentences(text):
        low = s.lower().strip()
        if any(low.startswith(h) or f" {h}" in low for h in MODE_INTENT_HINTS.get(mode, [])):
            return s.strip()
        if s.strip().endswith("?"):
            return s.strip()
    return _leading_sentence(text, 240)


# --------------------------------------------------------------------------- #
# LLM-backed
# --------------------------------------------------------------------------- #
_ANALYST_SYSTEM = """You analyse a user's real-life situation for a Mahabharata-grounded
guidance system. Respond with ONLY a JSON object (no markdown, no prose) of the form:

{
  "situation": "one sentence describing what is happening",
  "people": ["people or roles involved"],
  "conflict": "the central dilemma as a short phrase, e.g. 'betrayal vs revenge'",
  "values": ["values in conflict as short lowercase labels"],
  "emotions": ["emotions the user appears to feel"],
  "question": "what the user is actually asking",
  "themes": ["3-8 retrieval themes from this fixed vocabulary only"],
  "entities": ["Mahabharata characters or episodes named or clearly implied"]
}

Fixed theme vocabulary:
{themes}

Rules:
- This is analysis only. Do NOT answer the user's question.
- Do not invent characters that are not named or clearly implied.
- Keep every field short."""


class LLMAnalyst:
    name = "llm"

    def __init__(self, llm) -> None:  # app.llm.base.LLMProvider
        self.llm = llm
        self._fallback = RuleBasedAnalyst()

    def analyze(self, text: str, mode: str, character: str | None = None) -> SituationAnalysis:
        base = self._fallback.analyze(text, mode, character)
        theme_vocab = ", ".join(sorted({t["slug"] for t in THEMES}))
        prompt = _ANALYST_SYSTEM.format(themes=theme_vocab)
        if character:
            prompt += f"\n\nFocus character for this turn: {character}"
        try:
            raw = self.llm.complete(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Mode: {mode}\n\nText:\n{text}"},
                ],
                temperature=0.0,
                max_tokens=700,
            )
            data = _parse_json(raw)
            themes = [str(t) for t in data.get("themes", [])][:8]
            valid_slugs = {t["slug"] for t in THEMES}
            themes = [t for t in themes if t in valid_slugs] or base.themes
            entities = [str(e) for e in data.get("entities", [])][:12] or base.entities
            return SituationAnalysis(
                situation=str(data.get("situation") or base.situation),
                people=[str(p) for p in data.get("people", [])][:10] or base.people,
                conflict=str(data.get("conflict") or base.conflict),
                values=[str(v) for v in data.get("values", [])][:8] or base.values,
                emotions=[str(e) for e in data.get("emotions", [])][:8] or base.emotions,
                question=str(data.get("question") or base.question),
                themes=themes,
                entities=entities,
                analysis_method="llm",
            )
        except Exception:
            return base


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.S)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(raw[start : end + 1])


def get_analyst():
    """Factory honouring the ANALYST setting (auto | llm | rule)."""
    mode = settings.effective_analyst
    if mode == "llm":
        try:
            from ..llm.registry import get_llm

            return LLMAnalyst(get_llm())
        except Exception:
            return RuleBasedAnalyst()
    return RuleBasedAnalyst()
