"""Exploration endpoints: characters, themes, source search, daily reflection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.models import Character, Message, Passage, Source, Theme
from ..db.session import get_db
from ..knowledge.taxonomy import MODES
from ..rag.pipeline import get_pipeline
from ..schemas import EvidencePassage, PassageOut, SearchRequest

router = APIRouter(tags=["explore"])


def _passage_out(p: Passage, source_title: str = "", relevance: float | None = None) -> PassageOut:
    return PassageOut(
        id=p.id,
        parva=p.parva,
        section=p.section,
        chapter=p.chapter,
        reference=p.source_reference,
        speaker=p.speaker,
        listener=p.listener,
        characters=list(p.characters or []),
        themes=list(p.themes or []),
        keywords=list(p.keywords or []),
        events=list(p.events or []),
        original_text=p.original_text,
        translation=p.translation,
        summary=p.summary,
        text_type=p.text_type,
        source_title=source_title,
        verification_status=p.verification_status,
        is_primary_text=p.is_primary_text,
        embedding_status=p.embedding_status,
        relevance=relevance,
    )


# --------------------------------------------------------------------------- #
@router.get("/characters")
def list_characters(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(Character).order_by(Character.name).all()
    counts: dict[str, int] = {}
    for (themes,) in db.query(Passage.themes).all():
        for t in themes or []:
            counts[t] = counts.get(t, 0) + 1
    return [
        {
            "slug": c.slug,
            "name": c.name,
            "aliases": list(c.aliases or []),
            "role": c.role,
            "description": c.description,
            "primary_themes": list(c.primary_themes or []),
            "theme_counts": {t: counts.get(t, 0) for t in (c.primary_themes or [])},
        }
        for c in rows
    ]


@router.get("/characters/{slug}")
def get_character(slug: str, db: Session = Depends(get_db),
                  limit: int = 10) -> dict:
    c = db.query(Character).filter(Character.slug == slug).one_or_none()
    if c is None:
        raise HTTPException(404, "Character not found")
    rows = (
        db.query(Passage, Source)
        .join(Source, Passage.source_id == Source.id)
        .filter(Passage.verification_status != "rejected")
        .order_by(Passage.updated_at.desc())
        .limit(400)
    ).all()

    def mentions(p: Passage) -> bool:
        names = {p.speaker.lower(), p.listener.lower()}
        names |= {x.lower() for x in (p.characters or [])}
        return slug in (p.characters or []) or any(
            n == slug or n == c.name.lower() or n in {a.lower() for a in (c.aliases or [])}
            for n in names if n
        )

    matched = [(p, s) for p, s in rows if mentions(p)]
    return {
        "character": {
            "slug": c.slug,
            "name": c.name,
            "aliases": list(c.aliases or []),
            "role": c.role,
            "description": c.description,
            "primary_themes": list(c.primary_themes or []),
        },
        "passages": [_passage_out(p, s.title) for p, s in matched[:limit]],
        "passage_count": len(matched),
        "perspective_hint": (
            f"A perspective associated with {c.name} in the retrieved episodes is: "
            f"{c.description} This is an interpretation of the episodes, not a "
            f"quotation."
        ),
    }


@router.get("/themes")
def list_themes(db: Session = Depends(get_db)) -> list[dict]:
    counts: dict[str, int] = {}
    for (themes,) in db.query(Passage.themes).all():
        for t in themes or []:
            counts[t] = counts.get(t, 0) + 1
    rows = db.query(Theme).order_by(Theme.kind, Theme.name).all()
    return [
        {
            "slug": t.slug, "name": t.name, "kind": t.kind,
            "description": t.description, "passage_count": counts.get(t.slug, 0),
        }
        for t in rows
    ]


# --------------------------------------------------------------------------- #
@router.post("/search")
def search(req: SearchRequest, db: Session = Depends(get_db)) -> dict:
    """6./12. Source Explorer — hybrid search over the indexed corpus."""
    pipeline = get_pipeline()
    results: list[EvidencePassage] = []
    if req.q.strip():
        results = pipeline.search(req.q, limit=max(req.limit, 50))
    else:
        q = db.query(Passage)
        if req.parva:
            q = q.filter(Passage.parva.ilike(f"%{req.parva}%"))
        if req.speaker:
            q = q.filter(Passage.speaker.ilike(f"%{req.speaker}%"))
        if req.text_type:
            q = q.filter(Passage.text_type == req.text_type)
        if req.character:
            q = q.filter(Passage.characters.like(f"%{req.character}%"))
        if req.theme:
            q = q.filter(Passage.themes.like(f"%{req.theme}%"))
        if req.verified_only:
            q = q.filter(Passage.verification_status == "verified")
        for p in q.order_by(Passage.updated_at.desc()).limit(req.limit).all():
            results.append(
                EvidencePassage(
                    id=p.id, parva=p.parva, section=p.section, chapter=p.chapter,
                    reference=p.source_reference, speaker=p.speaker, listener=p.listener,
                    characters=list(p.characters or []), themes=list(p.themes or []),
                    context=p.summary, quote=p.translation or p.original_text,
                    summary=p.summary, original_text=p.original_text,
                    text_type=p.text_type, verification_status=p.verification_status,
                    is_primary_text=p.is_primary_text, relevance=0.0, source="metadata",
                )
            )

    out = []
    for r in results:
        if req.parva and req.parva.lower() not in r.parva.lower():
            continue
        if req.character and req.character.lower() not in " ".join(
            [r.speaker, r.listener, *r.characters]
        ).lower():
            continue
        if req.theme and req.theme not in r.themes:
            continue
        if req.speaker and req.speaker.lower() not in r.speaker.lower():
            continue
        if req.text_type and req.text_type != r.text_type:
            continue
        if req.verified_only and r.verification_status != "verified":
            continue
        out.append(r.model_dump())
        if len(out) >= req.limit:
            break
    return {"count": len(out), "results": out}


@router.get("/search")
def search_get(q: str = "", limit: int = 10) -> dict:
    pipeline = get_pipeline()
    rows = pipeline.search(q, limit=limit) if q.strip() else []
    return {"count": len(rows), "results": [r.model_dump() for r in rows]}


@router.get("/reflection/daily")
def daily_reflection(language: str = "en") -> dict:
    """12. Daily Reflection — a verified passage for today, deterministically."""
    pipeline = get_pipeline()
    result = pipeline.run(
        query="Give me today's reflection from the Mahabharata.",
        mode="daily_reflection",
        language=language,
    )
    reply = result.response
    if reply.support_level == "insufficient_evidence" and not result.evidence:
        return {
            "available": False,
            "message": (
                "No verified passage is indexed yet. Run the corpus ingest and mark "
                "passages as verified in the admin area."
            ),
            "reply": reply.model_dump(),
        }
    return {"available": True, "reply": reply.model_dump()}


@router.get("/passages/{passage_id}")
def get_passage(passage_id: str, db: Session = Depends(get_db)) -> dict:
    p = db.query(Passage).filter(Passage.id == passage_id).one_or_none()
    if p is None:
        raise HTTPException(404, "Passage not found")
    source = db.get(Source, p.source_id)
    return _passage_out(p, source.title if source else "").model_dump()
