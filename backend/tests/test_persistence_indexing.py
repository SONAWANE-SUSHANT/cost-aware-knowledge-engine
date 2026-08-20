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
                "WEIGHT\n"
                "Actual (Kg) : 42\n"
            ),
        }
    ]


def test_document_persistence():
    db = make_session()
    repository = KnowledgeRepository(db)

    document, created = repository.create_or_get_document(
        filename="sample.txt",
        file_type=".txt",
        checksum="abc123",
        metadata={"source": "test"},
    )
    db.commit()

    assert created is True
    assert document.id is not None

    stored = db.execute(select(Document)).scalar_one()

    assert stored.filename == "sample.txt"
    assert stored.processing_status == "processing"
    assert stored.meta == {"source": "test"}


def test_chunk_and_fact_persistence():
    db = make_session()
    repository = KnowledgeRepository(db)
    document, _ = repository.create_or_get_document(
        filename="sample.txt",
        file_type=".txt",
        checksum="abc123",
    )
    page, page_created = repository.add_page(
        document_id=document.id,
        page_number=1,
        text="Consignor : Alpha Industries",
    )
    chunk, chunk_created = repository.add_chunk(
        document_id=document.id,
        page_number=page.page_number,
        chunk_id="stable-chunk-id",
        chunk_type="text",
        chunk_text="Consignor : Alpha Industries",
        chunking_strategy="semantic",
    )
    fact, fact_created = repository.add_fact(
        document_id=document.id,
        page_number=1,
        field="consignor",
        value="Alpha Industries",
        source_text="Consignor : Alpha Industries",
        section=None,
        copy_type="original",
        confidence=0.85,
    )
    db.commit()

    assert page_created is True
    assert chunk_created is True
    assert fact_created is True
    assert db.execute(select(DocumentPage)).scalar_one().text
    assert db.execute(select(DocumentChunk)).scalar_one().chunking_strategy
    assert db.execute(select(KnowledgeFact)).scalar_one().confidence == 0.85
    assert chunk.chunk_id == "stable-chunk-id"
    assert fact.source_text == "Consignor : Alpha Industries"


def test_embedding_creation_and_retrieval():
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    repository = KnowledgeRepository(db)
    document, _ = repository.create_or_get_document(
        filename="sample.txt",
        file_type=".txt",
        checksum="abc123",
    )
    chunk, _ = repository.add_chunk(
        document_id=document.id,
        page_number=1,
        chunk_id="stable-chunk-id",
        chunk_type="text",
        chunk_text="alpha beta gamma",
        chunking_strategy="semantic",
    )
    vector = provider.embed_text(chunk.chunk_text)
    embedding, created = repository.add_embedding(
        document_id=document.id,
        chunk=chunk,
        provider=provider.name,
        model=provider.model,
        dimensions=provider.dimensions,
        embedding=vector,
    )
    db.commit()

    results = repository.search_similar_chunks(
        provider.embed_text("alpha beta"),
        limit=1,
        provider=provider.name,
        model=provider.model,
    )

    assert created is True
    assert embedding.dimensions == 16
    assert db.execute(select(DocumentEmbedding)).scalar_one().embedding
    assert results[0][0].chunk_id == "stable-chunk-id"
    assert results[0][1] > 0


def test_indexer_prevents_duplicates():
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    indexer = KnowledgeIndexer(
        db=db,
        embedding_provider=provider,
    )

    first = indexer.index_document(
        filename="sample.txt",
        file_type=".txt",
        pages=sample_pages(),
    )
    db.commit()

    second = indexer.index_document(
        filename="sample.txt",
        file_type=".txt",
        pages=sample_pages(),
    )
    db.commit()

    assert first["document_created"] is True
    assert second["document_created"] is False
    assert second["pages_created"] == 0
    assert second["chunks_created"] == 0
    assert second["facts_created"] == 0
    assert second["embeddings_created"] == 0
    assert len(db.execute(select(Document)).scalars().all()) == 1
    assert len(db.execute(select(DocumentChunk)).scalars().all()) > 0


def test_indexer_supports_both_chunking_strategies():
    db = make_session()
    provider = DeterministicEmbeddingProvider(dimensions=16)
    indexer = KnowledgeIndexer(
        db=db,
        embedding_provider=provider,
    )

    indexer.index_document(
        filename="sample.txt",
        file_type=".txt",
        pages=sample_pages(),
    )
    db.commit()

    chunks = db.execute(select(DocumentChunk)).scalars().all()
    strategies = {
        chunk.chunking_strategy
        for chunk in chunks
    }

    assert "sliding_window" in strategies
    assert "semantic" in strategies
