"""SQLAlchemy models.

Tables
------
users, conversations, messages, sources, passages, characters, themes,
passage_themes, embeddings, citations, feedback, eval_runs.

The schema is shared by the SQLite (local) and PostgreSQL backends. Vector
storage is handled by :mod:`app.vectorstore`; the ``embeddings`` table keeps a
JSON serialisation of every vector so that both backends can persist and
rebuild embeddings without requiring the pgvector extension at rest.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[str]: JSON}


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")


# --------------------------------------------------------------------------- #
# Conversation history
# --------------------------------------------------------------------------- #
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    mode: Mapped[str] = mapped_column(String(40), default="situation_advice")
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User | None] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    mode: Mapped[str] = mapped_column(String(40), default="situation_advice")
    content: Mapped[str] = mapped_column(Text, default="")
    analysis_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
    feedback: Mapped[list["Feedback"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


# --------------------------------------------------------------------------- #
# Knowledge base
# --------------------------------------------------------------------------- #
class Source(Base):
    """A published edition / translation. Only ``is_primary=True`` sources can
    back a *strong textual support* claim."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(300))
    author: Mapped[str] = mapped_column(String(200), default="")
    translator: Mapped[str] = mapped_column(String(200), default="")
    edition: Mapped[str] = mapped_column(String(200), default="")
    language: Mapped[str] = mapped_column(String(20), default="en")
    source_type: Mapped[str] = mapped_column(String(40), default="primary_text")
    # primary_text | translation | modern_retelling | commentary | rejected_source
    url: Mapped[str] = mapped_column(String(500), default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    passages: Mapped[list["Passage"]] = relationship(back_populates="source")


class Passage(Base):
    """One indexed unit of the Mahabharata."""

    __tablename__ = "passages"
    __table_args__ = (
        UniqueConstraint("source_reference", "content_hash", name="uq_ref_hash"),
        Index("ix_passages_parva", "parva"),
        Index("ix_passages_verification", "verification_status"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)

    parva: Mapped[str] = mapped_column(String(120), default="")
    section: Mapped[str] = mapped_column(String(200), default="")
    chapter: Mapped[str | None] = mapped_column(String(60), nullable=True)
    verse_range: Mapped[str] = mapped_column(String(80), default="")

    speaker: Mapped[str] = mapped_column(String(120), default="")
    listener: Mapped[str] = mapped_column(String(120), default="")
    characters: Mapped[list[str]] = mapped_column(JSON, default=list)
    events: Mapped[list[str]] = mapped_column(JSON, default=list)
    themes: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)

    # provenance-typed content -----------------------------------------------
    original_text: Mapped[str] = mapped_column(Text, default="")   # Sanskrit / original language
    translation: Mapped[str] = mapped_column(Text, default="")     # published translation
    summary: Mapped[str] = mapped_column(Text, default="")         # editorial summary (NOT a quote)
    text_type: Mapped[str] = mapped_column(String(20), default="summary")  # verse | prose | summary
    language: Mapped[str] = mapped_column(String(10), default="en")

    source_reference: Mapped[str] = mapped_column(String(300), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), default="")

    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    # unverified | verified | rejected
    verification_note: Mapped[str] = mapped_column(Text, default="")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(32), nullable=True)

    is_primary_text: Mapped[bool] = mapped_column(Boolean, default=True)
    embedding_status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | indexed | error

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    source: Mapped[Source] = relationship(back_populates="passages")
    embedding: Mapped["Embedding | None"] = relationship(
        back_populates="passage", uselist=False, cascade="all, delete-orphan"
    )


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    role: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    primary_themes: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    # theme clusters used by the situation analyst, e.g. "revenge", "duty"
    kind: Mapped[str] = mapped_column(String(40), default="value")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PassageTheme(Base):
    """Explicit many-to-many, used for metadata-filtered retrieval."""

    __tablename__ = "passage_themes"
    __table_args__ = (UniqueConstraint("passage_id", "theme_slug", name="uq_passage_theme"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    passage_id: Mapped[str] = mapped_column(
        ForeignKey("passages.id", ondelete="CASCADE"), index=True
    )
    theme_slug: Mapped[str] = mapped_column(String(80), index=True)


class Embedding(Base):
    """Persisted vector for a passage.

    ``vector`` is stored as JSON (a flat float list) so that the local and
    PostgreSQL backends share one representation. When ``STORAGE_BACKEND=
    postgres`` the vector store additionally maintains a native ``vector``
    column for exact nearest-neighbour search.
    """

    __tablename__ = "embeddings"
    __table_args__ = (UniqueConstraint("passage_id", "provider", "model", name="uq_emb"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    passage_id: Mapped[str] = mapped_column(
        ForeignKey("passages.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(80))
    dim: Mapped[int] = mapped_column(Integer)
    vector: Mapped[list[float]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    passage: Mapped[Passage] = relationship(back_populates="embedding")


# --------------------------------------------------------------------------- #
# Provenance of a generated answer
# --------------------------------------------------------------------------- #
class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    passage_id: Mapped[str] = mapped_column(String(32), index=True)
    reference: Mapped[str] = mapped_column(String(300))
    quote_used: Mapped[str] = mapped_column(Text, default="")
    support_level: Mapped[str] = mapped_column(String(40), default="interpretive")
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    message: Mapped[Message] = relationship(back_populates="citations")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer, default=0)  # -1 | 0 | 1
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    # grounded | misattributed | invented_quote | too_vague | unsafe | other
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    message: Mapped[Message] = relationship(back_populates="feedback")


class EvalRun(Base):
    """Persisted evaluation results (see :mod:`app.eval.runner`)."""

    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    dataset: Mapped[str] = mapped_column(String(200), default="default")
    generator: Mapped[str] = mapped_column(String(40), default="")
    results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


__all__ = [
    "Base",
    "User",
    "Conversation",
    "Message",
    "Source",
    "Passage",
    "Character",
    "Theme",
    "PassageTheme",
    "Embedding",
    "Citation",
    "Feedback",
    "EvalRun",
    "new_id",
    "utcnow",
    "settings",
]
