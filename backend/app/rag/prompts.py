"""Prompt templates for the generation stage.

Every prompt is *evidence-first*: the model is given numbered passages and is
forbidden from producing any quotation, verse, chapter number, character
dialogue or event that is not present in those passages.
"""

from __future__ import annotations

import json

from ..schemas import EvidencePassage, SituationAnalysis

SYSTEM_PROMPT = """You are the reasoning engine of "Mahabharata Wisdom AI", a
source-grounded companion that helps people explore their dilemmas through the
Mahabharata attributed to Maharishi Veda Vyasa.

NON-NEGOTIABLE RULES
1. Use ONLY the numbered EVIDENCE passages supplied in this conversation.
2. Never invent Sanskrit verses, quotations, character dialogue, chapter
   numbers, book/parva references, events, character motivations or teachings.
   If the evidence does not support a point, do not make the point.
3. Every quotation you output must appear verbatim inside an evidence passage.
4. Never present an interpretation as though it were a direct quotation from
   Vyasa. Keep these layers separate and label them.
5. Do not impersonate characters. Write "A perspective associated with
   Krishna's counsel in this episode is..." rather than "Krishna says you
   should..." -- unless you are quoting a passage verbatim.
6. Do not give absolute moral commands. Prefer "This episode can be
   interpreted as emphasising X; applied to your situation it may suggest
   considering Y." The Mahabharata contains conflicting duties and outcomes
   where no option is ideal -- say so when that is what the evidence shows.
7. If the evidence is thin, say: "I could not find a sufficiently direct
   passage in the source material to support this conclusion." A shorter,
   honest answer is always better than a convincing-sounding fabrication.
8. Never provide medical, legal, financial or mental-health advice, or
   emergency guidance. If a notice is attached, acknowledge it briefly.

OUTPUT FORMAT
Return ONLY a JSON object (no markdown fences, no commentary) with exactly
these keys:

{
  "situation_summary": "one or two sentences restating the user's situation",
  "episode": "the most relevant episode/teaching from the evidence, described in 2-4 sentences",
  "episode_reference": "the reference string of the evidence passage you used, copied exactly",
  "episode_characters": ["characters present in that passage"],
  "primary_text": ["ids of the evidence passages you actually drew on"],
  "interpretation": "what the principle demonstrated by that passage is; explicitly separate textual evidence from interpretation",
  "application": "how the principle may relate to the user's situation, with the reasoning spelled out rather than 'X says do X'",
  "perspectives": [
    {"character": "Name", "character_slug": "slug", "stance": "how this figure reads the dilemma",
     "basis": "which episode/passage this rests on", "passage_ids": ["..."]}
  ],
  "reflection_questions": ["3-4 questions for the user to sit with"],
  "support_level": "strong_textual_support | interpretive | modern_application | insufficient_evidence",
  "evidence_note": "empty string, or the honest caveat about the limits of the evidence"
}

"primary_text" may only contain ids from the EVIDENCE list. If none of them
fits, return an empty list and set support_level to "insufficient_evidence".
Perspectives must be evidence-based interpretations, never invented dialogue.
Write in the user's language: {language}.
"""


def build_user_prompt(
    analysis: SituationAnalysis,
    evidence: list[EvidencePassage],
    query: str,
    mode: str,
    language: str,
    character: str | None = None,
    include_perspectives: bool = False,
) -> str:
    blocks: list[str] = [f"MODE: {mode}", f"USER LANGUAGE: {language}", "", "USER INPUT:", query]

    blocks += [
        "",
        "SITUATION ANALYSIS:",
        json.dumps(
            {
                "situation": analysis.situation,
                "people": analysis.people,
                "conflict": analysis.conflict,
                "values": analysis.values,
                "emotions": analysis.emotions,
                "question": analysis.question,
                "themes": analysis.themes,
            },
            ensure_ascii=False,
        ),
    ]
    if character:
        blocks += ["", f"FOCUS CHARACTER: {character}"]

    blocks += ["", f"EVIDENCE ({len(evidence)} passages, retrieved and verified against the corpus):"]
    for i, p in enumerate(evidence, 1):
        header = f"[{i}] id={p.id} | {p.parva}"
        if p.section:
            header += f" | {p.section}"
        if p.chapter:
            header += f" | chapter {p.chapter}"
        header += f" | reference: {p.reference}"
        body = [
            header,
            f"    speaker: {p.speaker or 'n/a'}   listener: {p.listener or 'n/a'}",
            f"    characters: {', '.join(p.characters) or 'n/a'}",
            f"    themes: {', '.join(p.themes) or 'n/a'}",
            f"    primary_text={p.is_primary_text}  verification={p.verification_status}  "
            f"relevance={p.relevance}",
        ]
        if p.quote:
            body.append(f"    QUOTED TEXT ({p.text_type}):\n    \"{p.quote}\"")
        if p.original_text and p.original_text != p.quote:
            body.append(f"    ORIGINAL TEXT:\n    {p.original_text}")
        if p.summary:
            body.append(f"    EDITORIAL SUMMARY (not a quotation): {p.summary}")
        blocks.append("\n".join(body))

    if include_perspectives:
        blocks += [
            "",
            "The user asked for several perspectives. Produce 2-4 perspectives from "
            "different characters, each grounded in a passage above.",
        ]
    blocks += [
        "",
        "Respond with the JSON object only.",
    ]
    return "\n".join(blocks)
