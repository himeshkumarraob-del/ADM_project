"""Answer generation.

Two implementations of the same contract:

``LLMGenerator``
    Prompts the configured model with the evidence pack and validates its
    JSON output. Anything it cannot verify against the evidence (unknown
    passage ids, quotation-shaped text not present in evidence) is removed.

``TemplateGenerator``
    Deterministic and offline. It composes the answer *only* from retrieved
    passages, the taxonomy and the i18n catalogue. It invents nothing, which
    makes it both the zero-config default and the reference implementation the
    anti-hallucination tests are written against.

Select with ``GENERATOR=llm | template | auto``.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from ..config import settings
from ..i18n import get_messages
from ..knowledge.taxonomy import CHARACTERS, THEMES
from ..schemas import EvidencePassage, GuidanceResponse, Perspective, SituationAnalysis
from .attributor import AttributedClaim, build_evidence_set
from .evidence import is_strong_textual_evidence
from .guardrails import grounding_check, register_evidence_refs
from .prompts import SYSTEM_PROMPT, build_user_prompt

_CHAR_BY_SLUG = {c["slug"]: c for c in CHARACTERS}
_THEMES_BY_SLUG = {t["slug"]: t for t in THEMES}

# Interpretive one-line principles. These are *readings* of the text and are
# always presented as such ("This episode can be read as emphasising ...").
PRINCIPLES: dict[str, str] = {
    "dharma": "the passage foregrounds dharma as a set of obligations that do not "
              "stop being binding when they become inconvenient",
    "duty": "the passage distinguishes the work your position demands from what you "
            "personally want from it",
    "duty-vs-interest": "the passage weighs what you owe against what you stand to gain",
    "truth-vs-loyalty": "the passage puts honesty toward the facts against fidelity "
                        "to a person",
    "family-vs-justice": "the passage sets kinship obligations against fair dealing "
                         "for everyone else",
    "ambition-vs-ethics": "the passage considers how far advancement may go before it "
                          "crosses a line",
    "forgiveness-vs-self-respect": "the passage asks whether absorbing a wrong protects "
                                   "anything real",
    "revenge-vs-restraint": "the passage weighs retaliation against checking oneself",
    "fear-vs-responsibility": "the passage weighs personal safety against a duty that "
                              "still has to be faced",
    "attachment-vs-duty": "the passage separates clinging from acting as the situation "
                          "requires",
    "friendship-vs-morality": "the passage tests loyalty to a friend against refusing "
                              "a wrong",
    "individual-vs-society": "the passage weighs a personal wish against its effect on "
                             "others",
    "revenge": "the passage follows retaliation far enough to show what it produces",
    "anger": "the passage treats anger as something to be governed rather than obeyed",
    "forgiveness": "the passage distinguishes forbearance from weakness",
    "justice": "the passage is concerned with redress: who may demand it and how",
    "self-control": "the passage locates the first victory in restraining one's own "
                    "impulse",
    "consequences": "the passage traces an action to its downstream cost",
    "loyalty": "the passage shows fidelity being carried past the point of comfort",
    "gratitude": "the passage treats an obligation received as a claim that must be "
                 "repaid",
    "identity": "the passage questions what one's origin or role actually obliges one "
                "to do",
    "recognition": "the passage separates the work itself from who gets credit for it",
    "perseverance": "the passage treats continuing as a choice made without guarantee "
                    "of outcome",
    "detachment": "the passage separates committing to the action from clinging to its "
                  "fruit",
    "counsel": "the passage shows advice being offered, weighed, and possibly refused",
    "silence": "the passage examines what silence costs and whom it protects",
    "responsibility": "the passage ties obligation to the role one actually holds",
    "grief": "the passage sits with loss rather than explaining it away",
    "fear": "the passage shows fear acting on judgement",
    "ambition": "the passage shows aspiration outrunning the limits around it",
    "nonviolence": "the passage marks the cost of harm even where harm is permitted",
    "truth": "the passage treats truth-telling as costly rather than merely correct",
    "power": "the passage ties authority to the duties that come with it",
    "war": "the passage presents conflict with its cost visible",
    "doubt": "the passage legitimises hesitation before action",
    "resistance": "the passage shows a challenge being voiced to power",
    "deception": "the passage exposes a constructed trap",
    "secrecy": "the passage shows a withheld truth taking on a life of its own",
    "gambling": "the passage shows a stake being raised beyond what can be paid",
    "refusal-of-counsel": "the passage shows a warning delivered and then ignored",
}


# --------------------------------------------------------------------------- #
class Generator(Protocol):
    name: str

    def generate(
        self,
        analysis: SituationAnalysis,
        evidence: list[EvidencePassage],
        query: str,
        mode: str,
        language: str,
        *,
        character: str | None = None,
        include_perspectives: bool = False,
    ) -> GuidanceResponse:
        ...


# --------------------------------------------------------------------------- #
# Deterministic reference implementation
# --------------------------------------------------------------------------- #
def _principle_for(p: EvidencePassage) -> str:
    for slug in p.themes:
        if slug in PRINCIPLES:
            return PRINCIPLES[slug]
    return PRINCIPLES.get("dharma", PRINCIPLES["duty"])


def _lead_text(msgs: dict, top: EvidencePassage, quoted: str) -> str:
    """TEXTUAL CLAIM: what the retrieved passage actually says or records.

    Three shapes, in priority order:

    1. quotation present      -> ``reads "..." and records A, B in S.``
    2. characters, no quote   -> ``records A, B in S.``
    3. neither                -> ``is an editorial summary: ...``
    """
    label = msgs["textual_evidence"]
    ref = top.source_reference or top.parva
    where = top.section or top.parva
    if not quoted and not top.characters:
        return f"{label}: the retrieved passage ({ref}) is an editorial summary: {top.summary}"

    body = f"the retrieved passage ({ref}) "
    if quoted:
        body += f"reads {quoted}"
        if top.characters:
            body += f" and records {', '.join(top.characters[:4])} in {where}."
        else:
            body += "."
    else:
        body += f"records {', '.join(top.characters[:4])} in {where}."
    return f"{label}: {body}"


def _to_generated_claims(
    claims: list[AttributedClaim], evidence: list[EvidencePassage]
) -> list["GeneratedClaim"]:
    """Project attributed claims into the typed, inspectable ledger.

    Each entry records the claim's type, the passages that back it, a resolved
    citation and whether the claim passes :func:`grounding_check` on its own --
    the data the faithfulness debug panel renders.
    """
    from ..schemas import GeneratedClaim

    ref_by_id = {p.id: (p.source_reference or p.parva) for p in evidence}
    out: list[GeneratedClaim] = []
    for c in claims:
        best = c.supporting_passages[0] if c.supporting_passages else ""
        # A claim whose wording carries quotation/reference shapes that the
        # evidence does not back is reported as ungrounded, never silently OK.
        grounded = grounding_check(c.claim, evidence)["clean"]
        out.append(
            GeneratedClaim(
                text=c.claim,
                claim_type=c.claim_type,  # type: ignore[arg-type]
                supporting_passages=list(c.supporting_passages),
                support_level=c.support_level,
                citation=ref_by_id.get(best, ""),
                grounded=grounded,
            )
        )
    return out


def _attributed(claim: str, evidence_set) -> "AttributedClaim":
    """Attribute a generated claim; keep it when at least one passage backs it.

    If no passage supports the claim it is marked ``unsupported`` and dropped
    by the caller -- a claim is never cited on retrieval rank alone.
    """
    from .attributor import attribute_claim

    attributed = attribute_claim(claim, evidence_set)
    return attributed


def _episode_text(p: EvidencePassage) -> str:
    bits: list[str] = []
    if p.speaker and p.listener:
        bits.append(f"{p.speaker} is speaking to {p.listener}")
    elif p.speaker:
        bits.append(f"{p.speaker} speaks")
    elif p.characters:
        bits.append(f"{', '.join(p.characters[:4])} appear")
    if p.section:
        bits.append(f"in {p.section}")
    elif p.parva:
        bits.append(f"in {p.parva}")
    head = ", ".join(bits) + "." if bits else ""
    detail = (p.summary or "").strip()
    if detail:
        return (head + " " + detail).strip()
    if p.quote:
        return (head + f" The passage reads: \u201c{p.quote}\u201d").strip()
    return head or p.parva


def _application_for(
    analysis: SituationAnalysis, top: EvidencePassage, language: str,
    query: str = "",
) -> str:
    """MODERN APPLICATION layer only.

    Deliberately separate from the reading: it bridges the *principle* to the
    user's situation and never restates the episode, so the two cannot be
    mistaken for one another (or for a quotation).

    The analogy caveat is attached only when the user is actually describing
    a modern situation of their own. For a corpus question ("what happens in
    the dice game?") there is no analogy to qualify, and a caveat there would
    be boilerplate rather than honesty.
    """
    msgs = get_messages(language)
    conflict = analysis.conflict or (analysis.values and " vs ".join(analysis.values[:2])) or ""
    suggestion = (
        "separating the principle you want to act on from the pressure you are under"
        if not conflict
        else f"asking which of {conflict} you are actually serving right now"
    )
    personal = _describes_modern_situation(query, analysis)
    key = "application_only" if personal else "application_reader"
    body = msgs[key].format(suggestion=suggestion)
    caveat = f" {_analogy_caveat(msgs, top)}" if personal else ""
    return f"{msgs['modern_application']}: {body}{caveat}"


# Modern-situation signals: the user speaking about their own life, or naming
# a contemporary setting. Used only to decide whether the analogy caveat is
# worth emitting -- never to alter the evidence or the support level.
_MODERN_SETTINGS = (
    "workplace", "work", "job", "boss", "manager", "colleague", "office",
    "career", "promotion", "salary", "team", "company", "project",
    "family", "parents", "mother", "father", "spouse", "wife", "husband",
    "partner", "friend", "friendship", "marriage", "divorce", "child",
    "children", "sibling", "brother", "sister", "school", "university",
    "college", "classmate", "teacher", "money", "debt", "loan", "tax",
    "court", "police", "lawyer", "legal", "doctor", "diagnosis", "patient",
    "therapy", "medication", "online", "social media", "email", "neighbour",
    "neighbor", "roommate", "client", "customer", "business",
)
_PERSONAL_PRONOUNS = re.compile(
    r"\b(i|my|me|we|our|us|you|your)\b", re.I
)


def _describes_modern_situation(query: str, analysis: SituationAnalysis) -> bool:
    """True when the user is asking about *their own* modern circumstances.

    Pronouns are matched on word boundaries -- a plain substring test reads
    ``me`` inside "dice **game** of ..." as first person and mislabels a pure
    corpus question as a personal one. Modern-setting terms keep the cheaper
    substring test because they are multi-letter stems that do not collide
    with the corpus vocabulary.
    """
    low = query.lower()
    if any(term in low for term in _MODERN_SETTINGS):
        return True
    if not _PERSONAL_PRONOUNS.search(query):
        return False
    # A first/second-person question plus people or emotions in play reads as
    # the user's own situation rather than a corpus query. "Mahabharata" being
    # detected as a person by the extractor is not a person in this sense.
    people = [p for p in analysis.people if p.lower() != "mahabharata"]
    return bool(people or analysis.emotions)


def _analogy_caveat(msgs: dict, top: EvidencePassage) -> str:
    """Acknowledge where the ancient context differs from the modern one."""
    ref = f"{top.source_reference or ''} {top.parva or ''}"
    key = "analogy_caveat_teaching" if "Bhagavad Gita" in ref else "analogy_caveat_episode"
    return msgs[key]


def _perspectives_for(
    analysis: SituationAnalysis,
    evidence: list[EvidencePassage],
    mode: str,
) -> list[Perspective]:
    """Evidence-based readings attributed to figures *associated with* episodes,
    never invented dialogue."""
    wanted: list[str] = list(analysis.entities)
    if mode == "perspectives" and not wanted:
        wanted = ["krishna", "vidura", "bhishma", "karna", "draupadi"]
    out: list[Perspective] = []
    for slug in wanted[:4]:
        c = _CHAR_BY_SLUG.get(slug)
        if not c:
            continue
        related = [
            p for p in evidence
            if slug in [x.lower() for x in p.characters]
            or (p.speaker or "").lower() == c["name"].lower()
            or (p.listener or "").lower() == c["name"].lower()
        ]
        if not related:
            # fall back to any evidence whose themes overlap the character's
            related = [p for p in evidence if set(c["primary_themes"]) & set(p.themes)][:1]
        if not related:
            continue
        p = related[0]
        stance = (
            f"A reading associated with {c['name']}'s position in {p.parva} "
            f"{('— ' + p.section) if p.section else ''}: {c['description']}"
        )
        out.append(
            Perspective(
                character=c["name"],
                character_slug=slug,
                stance=stance,
                basis=(
                    f"{p.source_reference or p.parva}. "
                    "This is an interpretation of the episode, not a quotation."
                ),
                passage_ids=[p.id],
                support_level="interpretive",
            )
        )
    return out


class TemplateGenerator:
    name = "template"

    def generate(
        self,
        analysis: SituationAnalysis,
        evidence: list[EvidencePassage],
        query: str,
        mode: str,
        language: str,
        *,
        character: str | None = None,
        include_perspectives: bool = False,
    ) -> GuidanceResponse:
        msgs = get_messages(language)
        resp = GuidanceResponse(
            situation_summary=analysis.situation or query.strip()[:300],
            analysis=analysis,
            generator=self.name,
            language=language,
        )

        if not evidence:
            resp.support_level = "insufficient_evidence"
            resp.evidence_note = msgs["insufficient"]
            resp.interpretation = msgs["no_evidence_body"]
            resp.application = ""
            resp.reflection_questions = list(msgs["reflection_default"])
            resp.perspectives = []
            return resp

        top = evidence[0]
        resp.episode = _episode_text(top)
        resp.episode_reference = top.source_reference or top.parva
        resp.episode_characters = top.characters[:6] or ([top.speaker] if top.speaker else [])

        # ---- multi-passage evidence set (Phase 2, Parts 7-8) ------------- #
        # The answer is reasoned over a bounded, structured evidence set
        # rather than ``evidence[0]`` alone. Every claim is attributed to the
        # passages that actually support it; unsupported claims are dropped
        # instead of being cited anyway.
        evidence_set = build_evidence_set(evidence, max_items=4)
        # Cite exactly the passages the answer reasons over: every reference
        # that appears in the prose must resolve to a listed passage (and a
        # listed source), otherwise the grounding check would -- rightly --
        # flag the extra locator as fabricated.
        _by_id = {p.id: p for p in evidence}
        resp.primary_text = [
            _by_id[item.passage_id]
            for item in evidence_set
            if item.passage_id in _by_id
        ]
        claims: list[AttributedClaim] = []

        # ---- interpretation (explicitly labelled) ------------------------ #
        quoted = f"\u201c{top.quote}\u201d" if top.quote else ""
        lead_claim_text = _lead_text(msgs, top, quoted)
        claims.append(_attributed(lead_claim_text, evidence_set))

        # corroborating claims from the rest of the evidence set
        lead_key = f"{top.parva}|{top.section}".lower()
        for item in evidence_set[1:]:
            if f"{item.parva}|{item.section}".lower() == lead_key:
                continue
            snippet = item.text[:160].rstrip()
            if len(item.text) > 160:
                snippet = snippet.rsplit(" ", 1)[0] + "..."
            corrob = (
                f"The evidence set also includes {item.reference}: {snippet}"
            )
            claims.append(_attributed(corrob, evidence_set))

        principle_slug = next((s for s in top.themes if s in PRINCIPLES), None)
        principle_text = _principle_for(top)
        # INTERPRETATION: a reading of what the episode illustrates -- never a
        # quotation, never a direct teaching. Presented under its own label so
        # it cannot be confused with the textual claims above it.
        claims.append(
            AttributedClaim(
                claim=(
                    f"{msgs['interpretation']}: "
                    + msgs["reading"].format(value=principle_text)
                ),
                supporting_passages=[top.id] if principle_slug else [],
                support_level="interpretive" if principle_slug else "unsupported",
                claim_type="interpretation",
            )
        )

        interp_parts = [c.claim for c in claims if c.support_level != "unsupported"]
        if mode in {"moral_dilemma", "situation_advice", "perspectives"}:
            interp_parts.append(msgs["not_a_command"])
        resp.interpretation = " ".join(x for x in interp_parts if x)

        resp.retrieval_debug["evidence_set"] = [it.as_dict() for it in evidence_set]
        resp.retrieval_debug["claim_attributions"] = [
            {
                "claim": c.claim,
                "claim_type": c.claim_type,
                "supporting_passages": c.supporting_passages,
                "support_level": c.support_level,
            }
            for c in claims
        ]

        # ---- application -------------------------------------------------- #
        # Built from its own claim so the layer stays type-distinct.
        application_claim = AttributedClaim(
            claim=_application_for(analysis, top, language, query),
            supporting_passages=[top.id],
            support_level="interpretive",
            claim_type="application",
        )
        resp.application = application_claim.claim

        # ---- typed claim ledger (Phase 3) --------------------------------- #
        # Every claim the answer makes, with its type, supporters, resolved
        # citation and whether it passes the grounding check on its own.
        resp.claims = _to_generated_claims(
            [c for c in claims if c.support_level != "unsupported"]
            + [application_claim],
            evidence,
        )

        # ---- perspectives -------------------------------------------------- #
        if mode == "perspectives" or include_perspectives:
            resp.perspectives = _perspectives_for(analysis, evidence, mode)
        elif character and mode == "character_wisdom":
            resp.perspectives = _perspectives_for(
                analysis, evidence, "perspectives"
            )[:1]

        # ---- reflection ---------------------------------------------------- #
        resp.reflection_questions = list(msgs["reflection_default"])[:4]

        # ---- support level / sources --------------------------------------- #
        register_evidence_refs(evidence)
        resp.support_level = (
            "strong_textual_support"
            if is_strong_textual_evidence(top)
            else "interpretive"
        )
        resp.evidence_note = "" if resp.support_level == "strong_textual_support" else (
            "The retrieved passage supports the theme; the link to your situation "
            "is an interpretation rather than a statement in the text."
        )
        resp.sources = [
            p.source_reference or p.parva
            for p in resp.primary_text
            if p.source_reference or p.parva
        ]
        resp.retrieval_debug["grounding"] = grounding_check(
            resp.episode + " " + resp.interpretation, evidence
        )
        return resp


# --------------------------------------------------------------------------- #
# LLM implementation
# --------------------------------------------------------------------------- #
class LLMGenerator:
    name = "llm"

    def __init__(self, llm) -> None:
        self.llm = llm
        self._fallback = TemplateGenerator()

    def generate(
        self,
        analysis: SituationAnalysis,
        evidence: list[EvidencePassage],
        query: str,
        mode: str,
        language: str,
        *,
        character: str | None = None,
        include_perspectives: bool = False,
    ) -> GuidanceResponse:
        if not evidence:
            return self._fallback.generate(
                analysis, evidence, query, mode, language,
                character=character, include_perspectives=include_perspectives,
            )
        try:
            raw = self.llm.complete(
                [
                    {"role": "system", "content": SYSTEM_PROMPT.format(language=language)},
                    {
                        "role": "user",
                        "content": build_user_prompt(
                            analysis, evidence, query, mode, language,
                            character=character,
                            include_perspectives=include_perspectives,
                        ),
                    },
                ],
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                json_mode=True,
            )
            data = _parse_json(raw)
            return self._merge(data, analysis, evidence, query, mode, language)
        except Exception as exc:  # noqa: BLE001 - degrade, never fail the request
            resp = self._fallback.generate(
                analysis, evidence, query, mode, language,
                character=character, include_perspectives=include_perspectives,
            )
            resp.retrieval_debug["llm_error"] = f"{type(exc).__name__}: {exc}"
            return resp

    # ------------------------------------------------------------------ #
    def _merge(
        self,
        data: dict,
        analysis: SituationAnalysis,
        evidence: list[EvidencePassage],
        query: str,
        mode: str,
        language: str,
    ) -> GuidanceResponse:
        msgs = get_messages(language)
        by_id = {p.id: p for p in evidence}

        cited: list[EvidencePassage] = []
        for pid in [str(x) for x in data.get("primary_text", [])]:
            if pid in by_id and pid not in {c.id for c in cited}:
                cited.append(by_id[pid])
        # never let the model cite outside the evidence pack
        cited = cited or evidence[:1]

        resp = GuidanceResponse(
            situation_summary=str(data.get("situation_summary") or analysis.situation),
            analysis=analysis,
            episode=str(data.get("episode") or ""),
            episode_reference=str(
                data.get("episode_reference") or (cited[0].source_reference if cited else "")
            ),
            episode_characters=[str(c) for c in data.get("episode_characters", [])][:8],
            primary_text=cited[:4],
            interpretation=str(data.get("interpretation") or ""),
            application=str(data.get("application") or ""),
            reflection_questions=[str(q) for q in data.get("reflection_questions", [])][:6],
            generator=self.name,
            language=language,
        )

        # perspectives: clamp ids to evidence
        perspectives: list[Perspective] = []
        for item in data.get("perspectives", []) or []:
            if not isinstance(item, dict):
                continue
            pids = [p for p in [str(x) for x in item.get("passage_ids", [])] if p in by_id]
            perspectives.append(
                Perspective(
                    character=str(item.get("character") or ""),
                    character_slug=str(item.get("character_slug") or ""),
                    stance=str(item.get("stance") or ""),
                    basis=str(item.get("basis") or ""),
                    passage_ids=pids,
                    support_level="interpretive",
                )
            )
        resp.perspectives = [p for p in perspectives if p.character][:5]

        level = str(data.get("support_level") or "interpretive")
        if level not in {
            "strong_textual_support", "interpretive", "modern_application",
            "insufficient_evidence",
        }:
            level = "interpretive"
        # Enforce: "strong" requires a verified primary-text passage in evidence.
        top = max((p.relevance for p in resp.primary_text), default=0.0)
        if level == "strong_textual_support" and not any(
            is_strong_textual_evidence(p)
            for p in resp.primary_text
        ):
            level = "interpretive" if top else "insufficient_evidence"
        resp.support_level = level
        resp.evidence_note = str(data.get("evidence_note") or "")
        if level == "insufficient_evidence" and not resp.evidence_note:
            resp.evidence_note = msgs["insufficient"]

        register_evidence_refs(evidence)
        resp.sources = [
            p.source_reference or p.parva for p in resp.primary_text if p.source_reference or p.parva
        ]
        grounding = grounding_check(
            " ".join([resp.episode, resp.interpretation, resp.application]), evidence
        )
        resp.retrieval_debug["grounding"] = grounding
        if not grounding["clean"]:
            # Never ship an ungrounded quotation: drop the offending layer and
            # downgrade the support level.
            resp.support_level = (
                "insufficient_evidence" if not resp.primary_text else "interpretive"
            )
            resp.evidence_note = (
                "Part of the generated wording could not be matched against the "
                "retrieved passages, so it has been removed. "
                + (resp.evidence_note or "")
            ).strip()
            if grounding["unsupported_quotes"]:
                resp.interpretation = _strip_quotes(
                    resp.interpretation, grounding["unsupported_quotes"]
                )
        if not resp.reflection_questions:
            resp.reflection_questions = list(msgs["reflection_default"])[:4]
        return resp


def _strip_quotes(text: str, quotes: list[str]) -> str:
    for q in quotes:
        text = text.replace(q, "").replace("  ", " ")
    return text.strip()


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.S)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("model did not return JSON")
    return json.loads(raw[start : end + 1])


# --------------------------------------------------------------------------- #
def get_generator():
    mode = settings.effective_generator
    if mode == "llm":
        try:
            from ..llm.registry import get_llm

            return LLMGenerator(get_llm())
        except Exception:
            return TemplateGenerator()
    return TemplateGenerator()
