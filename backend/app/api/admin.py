"""19. Admin / knowledge management.

Upload sources, add and edit passages, verify citations, rebuild embeddings,
remove bad data and monitor retrieval quality.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..corpus.ingest import CORPUS_DIR, content_hash, ingest_corpus, rebuild_embeddings
from ..db.models import (
    Character,
    Citation,
    Embedding,
    Feedback,
    Message,
    Passage,
    PassageTheme,
    Source,
    Theme,
    User,
)
from ..db.session import get_db
from ..rag.pipeline import get_pipeline
from ..schemas import PassageCreate, PassageUpdate, SearchRequest, VerifyRequest
from ..security import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# --------------------------------------------------------------------------- #
# Corpus health (Phase 2, Part 6)
# --------------------------------------------------------------------------- #
@router.get("/corpus-health")
def corpus_health_endpoint(db: Session = Depends(get_db)) -> dict:
    """Integrity report computed live from the database: canonical parvas,
    duplicates, broken references, metadata gaps, taxonomy drift."""
    from ..corpus.health import corpus_health

    return corpus_health(db)


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    def count(model) -> int:
        return int(db.query(func.count(model.id)).scalar() or 0)

    by_status = dict(
        db.query(Passage.verification_status, func.count(Passage.id))
        .group_by(Passage.verification_status)
        .all()
    )
    by_parva = dict(
        db.query(Passage.parva, func.count(Passage.id))
        .group_by(Passage.parva)
        .order_by(func.count(Passage.id).desc())
        .all()
    )
    return {
        "passages": count(Passage),
        "sources": count(Source),
        "characters": count(Character),
        "themes": count(Theme),
        "embeddings": count(Embedding),
        "messages": count(Message),
        "citations": count(Citation),
        "feedback": count(Feedback),
        "by_verification": by_status,
        "by_parva": by_parva,
        "indexed": int(
            db.query(func.count(Passage.id))
            .filter(Passage.embedding_status == "indexed")
            .scalar()
            or 0
        ),
        "pending": int(
            db.query(func.count(Passage.id))
            .filter(Passage.embedding_status == "pending")
            .scalar()
            or 0
        ),
        "corpus_dir": str(CORPUS_DIR),
    }


# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #
@router.get("/sources")
def list_sources(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(Source).all()
    return [
        {
            "id": s.id, "title": s.title, "author": s.author, "translator": s.translator,
            "edition": s.edition, "language": s.language, "source_type": s.source_type,
            "url": s.url, "is_primary": s.is_primary, "notes": s.notes,
            "passage_count": len(s.passages),
        }
        for s in rows
    ]


@router.post("/sources")
def create_source(payload: dict, db: Session = Depends(get_db)) -> dict:
    s = Source(
        title=payload.get("title") or "Untitled source",
        author=payload.get("author", ""),
        translator=payload.get("translator", ""),
        edition=payload.get("edition", ""),
        language=payload.get("language", "en"),
        source_type=payload.get("source_type", "primary_text"),
        url=payload.get("url", ""),
        is_primary=bool(payload.get("is_primary", False)),
        notes=payload.get("notes", ""),
    )
    db.add(s)
    db.commit()
    return {"id": s.id, "title": s.title}


# --------------------------------------------------------------------------- #
# Passages
# --------------------------------------------------------------------------- #
@router.get("/passages")
def list_passages(
    db: Session = Depends(get_db),
    q: str = "",
    parva: str = "",
    status: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    query = db.query(Passage, Source).join(Source, Passage.source_id == Source.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Passage.source_reference.ilike(like)
            | Passage.summary.ilike(like)
            | Passage.translation.ilike(like)
            | Passage.parva.ilike(like)
            | Passage.speaker.ilike(like)
        )
    if parva:
        query = query.filter(Passage.parva.ilike(f"%{parva}%"))
    if status:
        query = query.filter(Passage.verification_status == status)
    total = query.count()
    rows = query.order_by(Passage.updated_at.desc()).limit(limit).offset(offset).all()
    items = []
    for p, s in rows:
        items.append(
            {
                "id": p.id, "parva": p.parva, "section": p.section, "chapter": p.chapter,
                "reference": p.source_reference, "speaker": p.speaker,
                "listener": p.listener, "characters": list(p.characters or []),
                "themes": list(p.themes or []), "keywords": list(p.keywords or []),
                "events": list(p.events or []),
                "original_text": p.original_text, "translation": p.translation,
                "summary": p.summary, "text_type": p.text_type,
                "source_id": s.id, "source_title": s.title,
                "verification_status": p.verification_status,
                "verification_note": p.verification_note,
                "is_primary_text": p.is_primary_text,
                "embedding_status": p.embedding_status,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
        )
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.post("/passages")
def create_passage(req: PassageCreate, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, req.source_id) if req.source_id else None
    if source is None:
        source = db.query(Source).filter(Source.is_primary.is_(True)).first()
    if source is None:
        raise HTTPException(400, "No source available; create a source first")

    text = " ".join([req.original_text, req.translation, req.summary])
    ch = content_hash(req.source_reference, text)
    exists = (
        db.query(Passage)
        .filter(Passage.source_reference == req.source_reference,
                Passage.content_hash == ch)
        .one_or_none()
    )
    if exists is not None:
        raise HTTPException(409, "An identical passage already exists")

    stale = db.query(Passage).filter(
        Passage.source_reference == req.source_reference
    ).first()
    if stale is not None:
        raise HTTPException(
            409,
            "A passage with this reference already exists and differs. Update it "
            "instead so verification can be re-run.",
        )

    p = Passage(
        source_id=source.id,
        parva=req.parva, section=req.section, chapter=req.chapter,
        verse_range=req.verse_range, speaker=req.speaker, listener=req.listener,
        characters=req.characters, events=req.events, themes=req.themes,
        keywords=req.keywords, original_text=req.original_text,
        translation=req.translation, summary=req.summary, text_type=req.text_type,
        language=req.language, source_reference=req.source_reference,
        content_hash=ch, verification_status="unverified",
        is_primary_text=req.is_primary_text, embedding_status="pending",
    )
    db.add(p)
    db.flush()
    for slug in set(p.themes or []):
        db.add(PassageTheme(passage_id=p.id, theme_slug=slug))
    db.commit()
    get_pipeline().invalidate()
    return {"id": p.id, "reference": p.source_reference, "verification_status": "unverified"}


@router.patch("/passages/{passage_id}")
def update_passage(passage_id: str, req: PassageUpdate,
                   db: Session = Depends(get_db)) -> dict:
    p = db.get(Passage, passage_id)
    if p is None:
        raise HTTPException(404, "Passage not found")
    data = req.model_dump(exclude_unset=True)
    text_changed = False
    for field in ("parva", "section", "chapter", "verse_range", "speaker", "listener",
                  "original_text", "translation", "summary", "text_type",
                  "source_reference", "is_primary_text"):
        if field in data:
            if getattr(p, field) != data[field]:
                text_changed = True
            setattr(p, field, data[field])
    for field in ("characters", "events", "themes", "keywords"):
        if field in data:
            setattr(p, field, data[field])

    if text_changed:
        blob = " ".join([p.original_text, p.translation, p.summary])
        p.content_hash = content_hash(p.source_reference, blob)
        p.embedding_status = "pending"
        if p.verification_status == "verified":
            # §19: edited content must be re-checked by a human.
            p.verification_status = "unverified"
            p.verification_note = (
                (p.verification_note + " ").strip()
                + " Content edited after verification; re-check required."
            ).strip()
            p.verified_at = None
        if "themes" in data:
            db.query(PassageTheme).filter(PassageTheme.passage_id == p.id).delete()
            for slug in set(p.themes or []):
                db.add(PassageTheme(passage_id=p.id, theme_slug=slug))
        from ..corpus.ingest import build_embeddings

        build_embeddings(db, [p.id])
    db.commit()
    get_pipeline().invalidate()
    return {"id": p.id, "verification_status": p.verification_status,
            "embedding_status": p.embedding_status}


@router.post("/passages/{passage_id}/verify")
def verify_passage(passage_id: str, req: VerifyRequest,
                   db: Session = Depends(get_db)) -> dict:
    p = db.get(Passage, passage_id)
    if p is None:
        raise HTTPException(404, "Passage not found")
    status = req.status.strip().lower()
    if status not in {"verified", "unverified", "needs_review", "rejected"}:
        raise HTTPException(422, "status must be verified | unverified | needs_review | rejected")
    p.verification_status = status
    p.verification_note = req.note or p.verification_note
    if status == "verified":
        p.verified_at = datetime.now(timezone.utc)
    else:
        p.verified_at = None
    db.commit()
    get_pipeline().invalidate()
    return {"id": p.id, "status": p.verification_status,
            "verified_at": p.verified_at.isoformat() if p.verified_at else None}


@router.delete("/passages/{passage_id}")
def delete_passage(passage_id: str, db: Session = Depends(get_db)) -> dict:
    p = db.get(Passage, passage_id)
    if p is None:
        raise HTTPException(404, "Passage not found")
    db.delete(p)
    db.commit()
    from ..vectorstore import get_vector_store

    get_vector_store().delete([passage_id])
    get_pipeline().invalidate()
    return {"deleted": passage_id}


# --------------------------------------------------------------------------- #
# Indexing
# --------------------------------------------------------------------------- #
@router.post("/ingest")
def run_ingest(rebuild: bool = False) -> dict:
    """Re-read ``data/corpus/*.json`` into the database and re-index."""
    report = ingest_corpus(rebuild=rebuild)
    get_pipeline().invalidate()
    return report.as_dict()


@router.post("/embeddings/rebuild")
def run_rebuild(db: Session = Depends(get_db)) -> dict:
    built = rebuild_embeddings(db)
    get_pipeline().invalidate()
    return {"rebuilt": built}


# --------------------------------------------------------------------------- #
# Retrieval quality monitoring
# --------------------------------------------------------------------------- #
_MONITORED_QUERIES = [
    "What does the Mahabharata say about keeping promises?",
    "Why did Karna remain loyal to Duryodhana?",
    "What can be learned from Yudhishthira's decisions?",
    "How does Krishna approach difficult decisions?",
    "What does the Mahabharata show about revenge?",
    "My friend keeps taking advantage of me. Should I keep helping?",
    "I worked hard but someone else got the credit.",
    "Should I stay silent when someone I know is doing wrong?",
]


@router.get("/retrieval-quality")
def retrieval_quality(db: Session = Depends(get_db)) -> dict:
    """Sample the retrieval channel over the evaluation questions.

    Reports channel coverage and how many verified, primary-text passages each
    query surfaces -- operational signal, not a fabricated confidence score.
    """
    pipeline = get_pipeline()
    samples = []
    for text in _MONITORED_QUERIES:
        analysis = pipeline.analyst.analyze(text, "situation_advice")
        from ..rag.expansion import expand
        from ..rag.rerank import rerank

        expanded = expand(analysis, text)
        result = pipeline.retriever.retrieve(text, expanded)
        ranked = rerank(result.passages, analysis, text)
        verified = [p for p in ranked if p.verification_status == "verified"]
        samples.append(
            {
                "query": text,
                "themes": analysis.themes,
                "conflict": analysis.conflict,
                "candidates": len(result.passages),
                "returned": len(ranked),
                "verified_returned": len(verified),
                "top_reference": ranked[0].source_reference if ranked else None,
                "top_relevance": ranked[0].relevance if ranked else None,
                "channels": [p.source for p in ranked[:3]],
                "debug": result.debug,
            }
        )
    empty = [s["query"] for s in samples if s["returned"] == 0]
    return {
        "corpus_size": pipeline.retriever._load() and len(pipeline.retriever._load()),
        "queries": samples,
        "no_evidence_queries": empty,
        "no_evidence_rate": round(len(empty) / max(1, len(samples)), 3),
        "note": (
            "These are retrieval-coverage figures, not confidence scores. "
            "A passage count of zero means the corpus needs more material for "
            "that theme."
        ),
    }


@router.get("/feedback")
def list_feedback(db: Session = Depends(get_db), limit: int = 100) -> list[dict]:
    rows = db.query(Feedback).order_by(Feedback.created_at.desc()).limit(limit).all()
    out = []
    for f in rows:
        m = db.get(Message, f.message_id)
        out.append(
            {
                "id": f.id, "message_id": f.message_id, "rating": f.rating,
                "categories": list(f.categories or []), "comment": f.comment,
                "created_at": f.created_at.isoformat(),
                "answer_excerpt": (m.content or "")[:200] if m else "",
            }
        )
    return out


@router.get("/citations/{message_id}")
def message_citations(message_id: str, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(Citation).filter(Citation.message_id == message_id).all()
    return [
        {
            "id": c.id, "passage_id": c.passage_id, "reference": c.reference,
            "support_level": c.support_level, "relevance": c.relevance,
            "verified": c.verified,
            "quote_used": c.quote_used,
        }
        for c in rows
    ]
