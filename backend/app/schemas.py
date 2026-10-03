"""Shared Pydantic schemas (pipeline <-> API <-> frontend)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

SupportLevel = Literal[
    "strong_textual_support",
    "interpretive",
    "modern_application",
    "insufficient_evidence",
]

Mode = Literal[
    "situation_advice",
    "episode",
    "character_wisdom",
    "moral_dilemma",
    "source_explorer",
    "daily_reflection",
    "perspectives",
]


# --------------------------------------------------------------------------- #
# 6. Situation analysis
# --------------------------------------------------------------------------- #
class SituationAnalysis(BaseModel):
    situation: str = Field("", description="What is happening, in one sentence.")
    people: list[str] = Field(default_factory=list, description="People involved.")
    conflict: str = Field("", description="The central dilemma, as a short phrase.")
    values: list[str] = Field(
        default_factory=list, description="Values in conflict (taxonomy slugs/labels)."
    )
    emotions: list[str] = Field(default_factory=list)
    question: str = Field("", description="What the user is actually asking.")
    themes: list[str] = Field(
        default_factory=list, description="Mahabharata theme slugs for retrieval."
    )
    entities: list[str] = Field(
        default_factory=list, description="Named characters/episodes detected."
    )
    analysis_method: str = "rule"  # rule | llm


# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #
class EvidencePassage(BaseModel):
    id: str
    parva: str = ""
    section: str = ""
    chapter: str | None = None
    reference: str = ""
    source_reference: str = ""
    speaker: str = ""
    listener: str = ""
    characters: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    context: str = ""            # what is happening in the source at this point
    quote: str = ""              # translation / original text actually used
    summary: str = ""            # editorial summary (never presented as a quote)
    original_text: str = ""
    text_type: str = "summary"
    source_title: str = ""
    verification_status: str = "unverified"
    is_primary_text: bool = True
    relevance: float = 0.0
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    source: str = "hybrid"       # semantic | keyword | metadata | hybrid

    @model_validator(mode="after")
    def _sync_reference(self) -> "EvidencePassage":
        """``reference`` and ``source_reference`` are two names for one value."""
        if not self.source_reference:
            self.source_reference = self.reference
        elif not self.reference:
            self.reference = self.source_reference
        return self


class Perspective(BaseModel):
    character: str
    character_slug: str = ""
    stance: str = ""
    basis: str = ""              # what in the text this rests on
    passage_ids: list[str] = Field(default_factory=list)
    support_level: SupportLevel = "interpretive"


class SafetyNotice(BaseModel):
    kind: Literal["crisis", "medical", "legal", "financial", "general"] = "general"
    message: str


class GeneratedClaim(BaseModel):
    """One generated claim, typed and attributed (Phase 3).

    The response never blurs these three kinds of statement:

    ``textual``         what the retrieved passage actually says/describes
    ``interpretation``  a reasoned reading of what the episode illustrates
    ``application``     a bridge from the textual principle to the user's
                        modern situation -- explicitly *not* a teaching of
                        the text
    """

    text: str
    claim_type: Literal["textual", "interpretation", "application"]
    supporting_passages: list[str] = Field(default_factory=list)
    support_level: str = "interpretive"
    citation: str = ""                    # reference of the best supporter
    grounded: bool = True                 # passes grounding_check on its own


# --------------------------------------------------------------------------- #
# 8. Response format
# --------------------------------------------------------------------------- #
class GuidanceResponse(BaseModel):
    situation_summary: str = ""
    analysis: SituationAnalysis = Field(default_factory=SituationAnalysis)
    episode: str = ""                    # "From the Mahabharata" heading content
    episode_reference: str = ""
    episode_characters: list[str] = Field(default_factory=list)
    primary_text: list[EvidencePassage] = Field(default_factory=list)
    interpretation: str = ""
    application: str = ""
    claims: list[GeneratedClaim] = Field(default_factory=list)
    perspectives: list[Perspective] = Field(default_factory=list)
    reflection_questions: list[str] = Field(default_factory=list)
    support_level: SupportLevel = "insufficient_evidence"
    evidence_note: str = ""
    sources: list[str] = Field(default_factory=list)
    safety_notices: list[SafetyNotice] = Field(default_factory=list)
    generator: str = "template"
    language: str = "en"
    retrieval_debug: dict = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# API payloads
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    mode: Mode = "situation_advice"
    conversation_id: str | None = None
    language: Literal["en", "hi"] = "en"
    character: str | None = None         # for character_wisdom / perspectives
    include_perspectives: bool | None = None


class CitationOut(BaseModel):
    id: str
    passage_id: str
    reference: str
    support_level: str
    relevance: float
    verified: bool


class ChatResponse(BaseModel):
    message_id: str
    conversation_id: str
    reply: GuidanceResponse
    citations: list[CitationOut] = Field(default_factory=list)


class MessageOut(BaseModel):
    id: str
    role: str
    mode: str
    content: str
    reply: GuidanceResponse | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    id: str
    title: str
    mode: str
    language: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class PassageOut(BaseModel):
    id: str
    parva: str
    section: str
    chapter: str | None
    reference: str
    speaker: str
    listener: str
    characters: list[str]
    themes: list[str]
    keywords: list[str]
    events: list[str]
    original_text: str
    translation: str
    summary: str
    text_type: str
    source_title: str
    verification_status: str
    is_primary_text: bool
    embedding_status: str
    relevance: float | None = None


class PassageCreate(BaseModel):
    parva: str
    section: str = ""
    chapter: str | None = None
    verse_range: str = ""
    speaker: str = ""
    listener: str = ""
    characters: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    original_text: str = ""
    translation: str = ""
    summary: str = ""
    text_type: Literal["verse", "prose", "summary"] = "summary"
    language: str = "en"
    source_reference: str
    source_id: str | None = None
    is_primary_text: bool = True


class PassageUpdate(BaseModel):
    parva: str | None = None
    section: str | None = None
    chapter: str | None = None
    verse_range: str | None = None
    speaker: str | None = None
    listener: str | None = None
    characters: list[str] | None = None
    events: list[str] | None = None
    themes: list[str] | None = None
    keywords: list[str] | None = None
    original_text: str | None = None
    translation: str | None = None
    summary: str | None = None
    text_type: str | None = None
    source_reference: str | None = None
    is_primary_text: bool | None = None


class VerifyRequest(BaseModel):
    status: Literal["verified", "unverified", "needs_review", "rejected"]
    note: str = ""


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int = Field(default=-1, ge=-1, le=1)
    categories: list[str] = Field(default_factory=list)
    comment: str = ""


class SearchRequest(BaseModel):
    q: str = ""
    parva: str | None = None
    character: str | None = None
    theme: str | None = None
    speaker: str | None = None
    text_type: Literal["verse", "prose", "summary"] | None = None
    verified_only: bool = False
    limit: int = Field(default=20, ge=1, le=100)
