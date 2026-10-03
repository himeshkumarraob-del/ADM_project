"""Guidance / conversation endpoints (the main RAG entry point)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.models import Citation, Conversation, Feedback, Message, User
from ..db.session import get_db
from ..knowledge.taxonomy import MODES
from ..rag.pipeline import get_pipeline
from ..schemas import (
    ChatRequest,
    ChatResponse,
    CitationOut,
    ConversationOut,
    FeedbackRequest,
    GuidanceResponse,
    MessageOut,
)
from ..security import get_current_user

router = APIRouter(tags=["chat"])


def _conversation_out(c: Conversation, message_count: int | None = None) -> ConversationOut:
    return ConversationOut(
        id=c.id,
        title=c.title,
        mode=c.mode,
        language=c.language,
        created_at=c.created_at,
        updated_at=c.updated_at,
        message_count=message_count if message_count is not None else len(c.messages),
    )


@router.get("/modes")
def list_modes() -> list[dict]:
    return list(MODES.values())


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db),
         user: User | None = Depends(get_current_user)) -> ChatResponse:
    if req.mode not in MODES:
        raise HTTPException(400, f"Unknown mode: {req.mode}")

    pipeline = get_pipeline()

    # ---- conversation ------------------------------------------------- #
    conv: Conversation | None = None
    if req.conversation_id:
        conv = db.get(Conversation, req.conversation_id)
        if conv is None:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = Conversation(
            user_id=user.id if user else None,
            title=req.message.strip().split("\n")[0][:80] or "New conversation",
            mode=req.mode,
            language=req.language,
        )
        db.add(conv)
        db.flush()

    # ---- run pipeline -------------------------------------------------- #
    result = pipeline.run(
        query=req.message,
        mode=req.mode,
        language=req.language,
        character=req.character,
        include_perspectives=req.include_perspectives,
    )
    reply: GuidanceResponse = result.response

    # ---- persist ------------------------------------------------------- #
    user_msg = Message(
        conversation_id=conv.id, role="user", mode=req.mode,
        content=req.message, language=req.language,
    )
    bot_msg = Message(
        conversation_id=conv.id, role="assistant", mode=req.mode,
        content=reply.situation_summary or req.message,
        analysis_json=result.analysis.model_dump(),
        response_json=reply.model_dump(),
        language=req.language,
    )
    db.add_all([user_msg, bot_msg])
    db.flush()

    citations: list[CitationOut] = []
    citation_rows: list[Citation] = []
    # Persist only the passages actually cited in the response.
    for p in reply.primary_text:
        citation = Citation(
            message_id=bot_msg.id,
            passage_id=p.id,
            reference=p.source_reference or p.parva,
            quote_used=(p.quote or "")[:2000],
            support_level=reply.support_level,
            relevance=p.relevance,
            verified=p.verification_status == "verified",
        )
        citation_rows.append(citation)
    db.add_all(citation_rows)
    db.flush()  # assign ids before serialising

    for citation in citation_rows:
        citations.append(
            CitationOut(
                id=citation.id,
                passage_id=citation.passage_id,
                reference=citation.reference,
                support_level=citation.support_level,
                relevance=citation.relevance,
                verified=citation.verified,
            )
        )

    conv.mode = req.mode
    conv.language = req.language
    db.commit()

    return ChatResponse(
        message_id=bot_msg.id,
        conversation_id=conv.id,
        reply=reply,
        citations=citations,
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
    limit: int = 50,
) -> list[ConversationOut]:
    q = db.query(Conversation).order_by(Conversation.updated_at.desc())
    if user is not None:
        q = q.filter(Conversation.user_id == user.id)
    else:
        q = q.filter(Conversation.user_id.is_(None))
    rows = q.limit(min(limit, 200)).all()
    counts = {c.id: len(c.messages) for c in rows}
    return [_conversation_out(c, counts[c.id]) for c in rows]


@router.get("/conversations/{conversation_id}", response_model=dict)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    if user is not None and conv.user_id and conv.user_id != user.id:
        raise HTTPException(403, "Not your conversation")

    out: list[MessageOut] = []
    for m in conv.messages:
        reply = None
        if m.response_json:
            try:
                reply = GuidanceResponse.model_validate(m.response_json)
            except Exception:  # noqa: BLE001
                reply = None
        out.append(
            MessageOut(
                id=m.id, role=m.role, mode=m.mode, content=m.content,
                reply=reply, created_at=m.created_at,
            )
        )
    return {"conversation": _conversation_out(conv), "messages": out}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    if user is not None and conv.user_id and conv.user_id != user.id:
        raise HTTPException(403, "Not your conversation")
    db.delete(conv)
    db.commit()
    return {"deleted": conversation_id}


@router.post("/feedback")
def leave_feedback(req: FeedbackRequest, db: Session = Depends(get_db)) -> dict:
    msg = db.get(Message, req.message_id)
    if msg is None:
        raise HTTPException(404, "Message not found")
    db.add(
        Feedback(
            message_id=req.message_id,
            rating=req.rating,
            categories=req.categories,
            comment=req.comment,
        )
    )
    db.commit()
    return {"ok": True}
