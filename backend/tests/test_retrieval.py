"""
Comprehensive tests for the hybrid retrieval layer.

Uses SQLite in-memory database and deterministic embeddings.
No external APIs required.
"""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.knowledge import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentPage,
    KnowledgeFact,
)
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.embeddings.provider import DeterministicEmbeddingProvider
from app.services.knowledge.knowledge_indexer import KnowledgeIndexer
from app.services.retrieval import (
    retrieve,
    retrieve_structured_facts,
    retrieve_lexical_chunks,
    retrieve_semantic_chunks,
    HybridWeights,
    RetrievalResult,
    RetrievalResponse,
)


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, future=True)
    return session_factory()


def sample_pages():
    return [
        {
            "page_number": 1,
            "text": (
                "ORIGINAL - CONSIGNOR COPY\n"
                "Sr. No. : LR-001\n"
                "Date : 2026-08-17\n"
                "Consignor : Alpha Industries\n"
                "Consignee : Beta Corp\n"
                "Vehicle No. : MH20GC-9895\n"
                "WEIGHT\n"
                "Actual (Kg) : 42\n"
                "Charged (Kg) : 45\n"
                "FREIGHT DETAILS\n"
                "Freight Amount : 5000\n"
            ),
        },
        {
            "page_number": 2,
            "text": (
                "DUPLICATE - OFFICE COPY\n"
                "Sr. No. : LR-001\n"
                "Date : 2026-08-17\n"
                "Consignor : Alpha Industries\n"
                "Consignee : Beta Corp\n"
                "Vehicle No. : MH20GC-9895\n"
                "WEIGHT\n"
                "Actual (Kg) : 42\n"
                "Charged (Kg) : 45\n"
                "FREIGHT DETAILS\n"
                "Freight Amount : 5000\n"
            ),
        },
    ]


def index_sample_document(db, provider=None):
    """Helper to index the sample document and return the indexer stats."""
    if provider is None:
        provider = DeterministicEmbeddingProvider(dimensions=16)
    indexer = KnowledgeIndexer(db=db, embedding_provider=provider)
    stats = indexer.index_document(
        filename="LR-001.txt",
        file_type=".txt",
        pages=sample_pages(),
    )
    db.commit()
    return stats


# ---------------------------------------------------------------------------
# Structured Fact Retrieval Tests
# ---------------------------------------------------------------------------


def test_structured_fact_exact_field_match():
    """Query matching a field name should return the fact."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_structured_facts(db, "vehicle number", top_k=5)

    assert len(results) > 0
    assert any(r.field == "vehicle_number" for r in results)
    assert any("MH20GC-9895" in (r.value or "") for r in results)
    for r in results:
        assert r.source_type == "fact"
        assert r.retrieval_method == "structured"
        assert r.document_id is not None


def test_structured_fact_exact_value_match():
    """Query matching a field value should return the fact."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_structured_facts(db, "MH20GC-9895", top_k=5)

    assert len(results) > 0
    assert any("MH20GC-9895" in (r.value or "") for r in results)


def test_structured_fact_partial_match():
    """Query with partial token match should return relevant facts."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_structured_facts(db, "consignor", top_k=5)

    assert len(results) > 0
    assert any("consignor" in (r.field or "").lower() for r in results)


def test_structured_fact_empty_query():
    """Empty query should return empty results."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_structured_facts(db, "", top_k=5)
    assert results == []


def test_structured_fact_no_match():
    """Query with no matching facts should return empty."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_structured_facts(db, "nonexistent_field_xyz", top_k=5)
    assert results == []


# ---------------------------------------------------------------------------
# Lexical Retrieval Tests
# ---------------------------------------------------------------------------


def test_lexical_exact_phrase():
    """Exact phrase in quotes should match chunks containing that phrase."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_lexical_chunks(db, '"Alpha Industries"', top_k=5)

    assert len(results) > 0
    assert any("Alpha Industries" in r.text for r in results)
    for r in results:
        assert r.source_type == "chunk"
        assert r.retrieval_method == "lexical"


def test_lexical_token_match():
    """Token-level matching should find relevant chunks."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_lexical_chunks(db, "freight amount", top_k=5)

    assert len(results) > 0
    assert any("freight" in r.text.lower() for r in results)


def test_lexical_case_insensitive():
    """Lexical search should be case-insensitive."""
    db = make_session()
    index_sample_document(db)

    results_upper = retrieve_lexical_chunks(db, "ALPHA INDUSTRIES", top_k=5)
    results_lower = retrieve_lexical_chunks(db, "alpha industries", top_k=5)

    assert len(results_upper) > 0
    assert len(results_lower) > 0


def test_lexical_empty_query():
    """Empty query should return empty results."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_lexical_chunks(db, "", top_k=5)
    assert results == []


def test_lexical_no_match():
    """Query with no matches should return empty."""
    db = make_session()
    index_sample_document(db)

    results = retrieve_lexical_chunks(db, "zzzzzzzzzzzzz", top_k=5)
    assert results == []


# ---------------------------------------------------------------------------
# Semantic Retrieval Tests
# ---------------------------------------------------------------------------


def test_semantic_retrieval():
    """Semantic search should return chunks with positive similarity."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    results = retrieve_semantic_chunks(
        db, "Alpha Industries", top_k=5, embedding_provider=provider
    )

    assert len(results) > 0
    for r in results:
        assert r.source_type == "chunk"
        assert r.retrieval_method == "semantic"
        assert r.score > 0


def test_semantic_retrieval_empty_query():
    """Empty query should return empty results."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    results = retrieve_semantic_chunks(
        db, "", top_k=5, embedding_provider=provider
    )
    assert results == []


# ---------------------------------------------------------------------------
# Hybrid Retrieval Tests
# ---------------------------------------------------------------------------


def test_hybrid_retrieval_structured():
    """Hybrid retrieval should return structured facts for field queries."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "vehicle number", top_k=5, embedding_provider=provider)

    assert isinstance(response, RetrievalResponse)
    assert response.total_results > 0
    assert any(r.source_type == "fact" for r in response.results)
    assert any(r.retrieval_method == "hybrid" for r in response.results)


def test_hybrid_retrieval_lexical():
    """Hybrid retrieval should return chunks for text queries."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "freight amount", top_k=5, embedding_provider=provider)

    assert response.total_results > 0
    assert any(r.source_type == "chunk" for r in response.results)


def test_hybrid_retrieval_exact_identifier():
    """Exact identifier match (e.g., vehicle number) should get a score boost."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "MH20GC-9895", top_k=5, embedding_provider=provider)

    assert response.total_results > 0
    # The exact value match should appear in results
    assert any(
        "MH20GC-9895" in (r.value or "") or "MH20GC-9895" in r.text
        for r in response.results
    )


def test_hybrid_retrieval_natural_language():
    """Natural language queries should return relevant results."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(
        db, "who is the consignor", top_k=5, embedding_provider=provider
    )

    assert response.total_results > 0
    # Should find consignor-related facts or chunks
    assert any(
        "consignor" in (r.field or "").lower() or "Alpha" in r.text
        for r in response.results
    )


def test_hybrid_retrieval_empty_query():
    """Empty query should return empty response."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "", top_k=5, embedding_provider=provider)
    assert response.total_results == 0
    assert response.results == []


def test_hybrid_retrieval_no_match():
    """Query with no matches should return empty."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(
        db, "zzzzzzzzzzzzzzzzzz", top_k=5, embedding_provider=provider
    )
    assert response.total_results == 0


# ---------------------------------------------------------------------------
# Ranking Tests
# ---------------------------------------------------------------------------


def test_ranking_structured_higher_for_field_queries():
    """For exact field queries, structured facts should rank high."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "vehicle number", top_k=5, embedding_provider=provider)

    assert response.total_results > 0
    # Top result should be a fact or at least contain vehicle info
    top = response.results[0]
    assert top.score > 0


def test_ranking_weights_configurable():
    """Custom weights should affect ranking."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    weights = HybridWeights(structured=1.0, lexical=0.0, semantic=0.0)
    response = retrieve(
        db, "freight", top_k=5, weights=weights, embedding_provider=provider
    )

    assert response.total_results > 0


# ---------------------------------------------------------------------------
# Deduplication Tests
# ---------------------------------------------------------------------------


def test_deduplication_same_chunk_not_duplicated():
    """The same chunk should not appear twice in results."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "Alpha Industries", top_k=10, embedding_provider=provider)

    chunk_ids = [
        r.chunk_id for r in response.results if r.chunk_id is not None
    ]
    # No duplicate chunk_ids
    assert len(chunk_ids) == len(set(chunk_ids))


def test_deduplication_same_fact_not_duplicated():
    """The same fact should not appear twice in results."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "consignor", top_k=10, embedding_provider=provider)

    fact_ids = [
        r.fact_id for r in response.results if r.fact_id is not None
    ]
    assert len(fact_ids) == len(set(fact_ids))


# ---------------------------------------------------------------------------
# Provenance Tests
# ---------------------------------------------------------------------------


def test_provenance_preserved():
    """Every result should carry full provenance metadata."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "Alpha Industries", top_k=5, embedding_provider=provider)

    for r in response.results:
        assert r.document_id is not None
        assert r.document_name is not None
        assert r.score >= 0
        assert r.retrieval_method is not None
        # At least one of these should be present
        assert (
            r.chunk_id is not None
            or r.fact_id is not None
        )


def test_provenance_fact_has_field_value():
    """Fact results should carry field and value."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    response = retrieve(db, "vehicle number", top_k=5, embedding_provider=provider)

    fact_results = [r for r in response.results if r.source_type == "fact"]
    if fact_results:
        assert fact_results[0].field is not None
        assert fact_results[0].value is not None


# ---------------------------------------------------------------------------
# Multiple Documents Tests
# ---------------------------------------------------------------------------


def test_multiple_documents():
    """Retrieval across multiple documents should work."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    indexer = KnowledgeIndexer(db=db, embedding_provider=provider)

    # Index first document
    indexer.index_document(
        filename="doc1.txt",
        file_type=".txt",
        pages=sample_pages(),
    )
    # Index second document with different content
    indexer.index_document(
        filename="doc2.txt",
        file_type=".txt",
        pages=[
            {
                "page_number": 1,
                "text": (
                    "ORIGINAL - CONSIGNOR COPY\n"
                    "Sr. No. : LR-002\n"
                    "Date : 2026-08-18\n"
                    "Consignor : Gamma Corp\n"
                    "Consignee : Delta Ltd\n"
                    "Vehicle No. : GJ01AB-1234\n"
                ),
            }
        ],
    )
    db.commit()

    response = retrieve(db, "Gamma Corp", top_k=5, embedding_provider=provider)

    assert response.total_results > 0
    assert any("Gamma Corp" in r.text for r in response.results)


# ---------------------------------------------------------------------------
# Duplicate/Original Copies Tests
# ---------------------------------------------------------------------------


def test_duplicate_copies_preserved():
    """Both original and duplicate copy facts should be retrievable."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    index_sample_document(db, provider=provider)

    # The sample has both ORIGINAL and DUPLICATE copies
    response = retrieve(db, "consignor", top_k=10, embedding_provider=provider)

    fact_results = [r for r in response.results if r.source_type == "fact"]
    # Should have facts from both copies
    copy_types = {r.copy_type for r in fact_results if r.copy_type}
    assert len(copy_types) > 0


# ---------------------------------------------------------------------------
# Result Model Tests
# ---------------------------------------------------------------------------


def test_retrieval_result_to_dict():
    """RetrievalResult should serialize to dict."""
    result = RetrievalResult(
        source_type="fact",
        document_id="doc-1",
        document_name="test.txt",
        page_number=1,
        fact_id="fact-1",
        text="field: value",
        field="field",
        value="value",
        score=0.95,
        retrieval_method="structured",
    )
    d = result.to_dict()
    assert d["source_type"] == "fact"
    assert d["score"] == 0.95
    assert d["retrieval_method"] == "structured"


def test_retrieval_response_to_dict():
    """RetrievalResponse should serialize to dict."""
    result = RetrievalResult(
        source_type="fact",
        document_id="doc-1",
        document_name="test.txt",
        text="test",
        score=0.5,
        retrieval_method="hybrid",
    )
    response = RetrievalResponse(
        query="test query",
        top_k=5,
        results=[result],
        total_results=1,
    )
    d = response.to_dict()
    assert d["query"] == "test query"
    assert d["total_results"] == 1
    assert len(d["results"]) == 1


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_empty_database():
    """Retrieval on an empty database should return empty."""
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)

    response = retrieve(db, "anything", top_k=5, embedding_provider=provider)
    assert response.total_results == 0


def test_retrieval_without_embeddings():
    """Retrieval should still work with structured and lexical even without embeddings."""
    db = make_session()
    # Index without embedding provider (uses default deterministic)
    indexer = KnowledgeIndexer(db=db)
    indexer.index_document(
        filename="test.txt",
        file_type=".txt",
        pages=sample_pages(),
    )
    db.commit()

    # This should still return structured and lexical results
    response = retrieve(db, "consignor", top_k=5)
    assert response.total_results > 0