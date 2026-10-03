"""Hybrid retrieval relevance (semantic + keyword + metadata fusion)."""

from __future__ import annotations

import pytest

from app.rag.expansion import expand

CASES = [
    ("What happens in the dice game of the Mahabharata?", ["Sabha Parva"], ["gambling"]),
    ("Why did Karna remain loyal to Duryodhana?", ["Udyoga Parva"], ["loyalty"]),
    ("What does the Bhagavad Gita say about acting without attachment to results?",
     ["Bhishma Parva"], ["detachment"]),
    ("Why did Bhishma refuse to fight Shikhandi?", ["Adi Parva", "Bhishma Parva"], ["vows"]),
    ("What does the Mahabharata show about revenge?", ["Sauptika Parva", "Adi Parva",
                                                        "Stri Parva"], ["revenge"]),
]


@pytest.mark.parametrize("query,expected_parvas,expected_themes", CASES)
def test_retrieval_surfaces_relevant_parva(pipeline, query, expected_parvas,
                                           expected_themes):
    analysis = pipeline.analyst.analyze(query, "episode")
    expanded = expand(analysis, query)
    result = pipeline.retriever.retrieve(query, expanded)
    assert result.passages, f"no passages retrieved for: {query}"

    top_parvas = [p.parva for p in result.passages[:5]]
    assert any(exp in pv for pv in top_parvas for exp in expected_parvas), (
        f"expected one of {expected_parvas} in the top 5, got {top_parvas}"
    )

    got_themes = {t for p in result.passages[:5] for t in p.themes}
    assert set(expected_themes) & got_themes, (
        f"expected {expected_themes} in retrieved themes, got {sorted(got_themes)}"
    )


def test_all_three_channels_reported(pipeline):
    analysis = pipeline.analyst.analyze(
        "Krishna's peace mission and Karna's refusal to join the Pandavas", "episode"
    )
    expanded = expand(analysis, "Krishna peace mission Karna refuse Pandavas")
    result = pipeline.retriever.retrieve("Krishna peace mission Karna refuse Pandavas", expanded)
    debug = result.debug
    assert debug["corpus_size"] > 0
    assert debug["keyword_hits"] > 0, "keyword channel returned nothing"
    assert debug["semantic_hits"] > 0, "semantic channel returned nothing"
    assert debug["returned"] > 0
    assert {"semantic", "keyword"} <= {c for p in result.passages for c in p.source.split("+")}


def test_metadata_filter_does_not_empty_the_corpus(pipeline):
    analysis = pipeline.analyst.analyze("Vidura's counsel to the king", "episode")
    analysis.themes = ["counsel", "refusal-of-counsel"]
    analysis.entities = ["vidura"]
    expanded = expand(analysis, "Vidura counsel")
    result = pipeline.retriever.retrieve("Vidura counsel", expanded)
    assert result.debug["corpus_size"] > 0
    assert result.passages


def test_reranking_orders_verified_primary_first(pipeline):
    analysis = pipeline.analyst.analyze("the dice game", "episode")
    expanded = expand(analysis, "the dice game")
    result = pipeline.retriever.retrieve("the dice game", expanded)
    from app.rag.rerank import rerank

    ranked = rerank(result.passages, analysis, "the dice game")
    assert ranked
    scores = [p.relevance for p in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0].parva.startswith("Sabha")


def test_empty_corpus_is_handled(seeded):
    """Retrieval must degrade gracefully rather than raise."""
    from app.rag.retrieval import HybridRetriever
    from app.rag.expansion import expand
    from app.schemas import SituationAnalysis

    from app.db.session import SessionLocal

    retriever = HybridRetriever(SessionLocal)
    retriever._meta = {}
    retriever._order = []
    analysis = SituationAnalysis(situation="x", themes=["dharma"])
    res = retriever.retrieve("anything", expand(analysis, "anything"))
    assert res.passages == []
    assert res.debug.get("corpus_size") == 0
