"""
Semantic (vector) chunk retrieval.

Uses the existing EmbeddingProvider abstraction and the repository's
search_similar_chunks method to find semantically similar chunks.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.embeddings.provider import EmbeddingProvider, get_embedding_provider
from app.services.retrieval.models import RetrievalResult


def retrieve_semantic_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
    embedding_provider: Optional[EmbeddingProvider] = None,
) -> list[RetrievalResult]:
    """
    Search document chunks by semantic similarity.

    Generates a query embedding using the existing EmbeddingProvider
    and searches the stored embeddings via cosine similarity.
    """
    if not query.strip():
        return []

    provider = embedding_provider or get_embedding_provider()
    repository = KnowledgeRepository(db)

    # Generate query embedding
    query_vector = provider.embed_text(query.strip())

    # Search similar chunks using existing repository method
    scored_chunks = repository.search_similar_chunks(
        query_embedding=query_vector,
        limit=top_k,
        provider=provider.name,
        model=provider.model,
    )

    results = []
    for chunk, similarity in scored_chunks:
        # Filter out non-positive similarities: the query has no
        # meaningful semantic overlap with the chunk.
        if similarity <= 0:
            continue
        results.append(
            RetrievalResult(
                source_type="chunk",
                document_id=chunk.document_id,
                document_name=chunk.document.filename if chunk.document else "",
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
                text=chunk.chunk_text,
                score=similarity,
                retrieval_method="semantic",
                section=None,
                copy_type=None,
                chunking_strategy=chunk.chunking_strategy,
                source_checksum=chunk.checksum,
            )
        )

    return results
