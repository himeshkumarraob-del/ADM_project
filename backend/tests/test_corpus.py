"""Corpus ingestion: schema, metadata completeness, idempotency."""

from __future__ import annotations

import pytest

REQUIRED_FIELDS = [
    "parva", "section", "speaker", "listener", "characters", "events",
    "themes", "keywords", "source_reference",
]


def test_corpus_ingests(seeded):
    assert seeded["report"].errors == []
    assert seeded["counts"]["passages"] >= 40
    assert seeded["counts"]["sources"] >= 1
    assert seeded["counts"]["themes"] >= 20
    assert seeded["counts"]["characters"] >= 15


def test_every_passage_has_metadata(seeded):
    from app.db.models import Passage, Source

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        rows = db.query(Passage, Source).join(Source).all()
    finally:
        db.close()
    assert rows, "no passages indexed"
    for p, s in rows:
        assert p.parva, f"{p.id} missing parva"
        assert p.source_reference, f"{p.id} missing source_reference"
        assert p.summary or p.translation or p.original_text, f"{p.id} has no text"
        assert p.content_hash, f"{p.id} missing content hash"
        assert s.source_type in {"primary_text", "translation", "modern_retelling",
                                 "commentary", "rejected_source"}
        assert isinstance(p.characters, list) and isinstance(p.themes, list)
        assert p.verification_status in {"verified", "unverified", "rejected"}


def test_reference_uniqueness(seeded):
    from collections import Counter

    from app.db.models import Passage

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        refs = [r[0] for r in db.query(Passage.source_reference).all()]
    finally:
        db.close()
    dupes = [ref for ref, n in Counter(refs).items() if n > 1]
    assert not dupes, f"duplicate source references: {dupes}"


def test_reingest_is_idempotent(seeded):
    from app.corpus.ingest import ingest_corpus
    from app.db.models import Passage

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        before = db.query(Passage).count()
    finally:
        db.close()

    report = ingest_corpus()

    db = SessionLocal()
    try:
        after = db.query(Passage).count()
    finally:
        db.close()
    assert report.passages_created == 0, "re-ingest created duplicates"
    assert after == before
    assert report.errors == []


def test_embeddings_built_for_every_passage(seeded):
    from app.db.models import Embedding, Passage

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        pending = db.query(Passage).filter(Passage.embedding_status != "indexed").count()
        vectors = db.query(Embedding).count()
        total = db.query(Passage).count()
    finally:
        db.close()
    assert pending == 0, f"{pending} passages not indexed"
    assert vectors == total, f"{vectors} vectors for {total} passages"


def test_embedding_vectors_are_normalised(seeded):
    from app.db.models import Embedding

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        row = db.query(Embedding).first()
    finally:
        db.close()
    assert row is not None
    norm = sum(v * v for v in row.vector) ** 0.5
    assert 0.99 <= norm <= 1.01, f"vector not normalised: {norm}"
