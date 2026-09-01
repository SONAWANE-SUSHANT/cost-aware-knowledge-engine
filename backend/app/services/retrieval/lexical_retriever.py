"""
Lexical (text-based) chunk retrieval.

Searches the existing DocumentChunk table using SQL ILIKE patterns
for case-insensitive token and exact-phrase matching.

No Elasticsearch/OpenSearch dependency.
"""

import re
from typing import Optional

from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session

from app.models.knowledge import Document, DocumentChunk
from app.services.retrieval.models import RetrievalResult
from app.utils.tokenize import content_tokens


def retrieve_lexical_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
) -> list[RetrievalResult]:
    """
    Search document chunks by lexical matching on chunk_text.

    Supports:
      - exact phrase matching (quoted tokens in query)
      - token-level matching (unquoted words)
      - case-insensitive matching

    Only content words are used for the unquoted token-level matching
    below -- common function words are filtered out first, since a word
    like "the" appears in nearly every chunk and would otherwise inflate
    scores for chunks that have nothing to do with the query.
    """
    normalized = query.strip().lower()

    if not normalized:
        return []

    # Parse query into exact phrases and individual tokens
    exact_phrases = re.findall(r'"([^"]+)"', normalized)
    # Remove quoted phrases and split remaining into content-word tokens
    remaining = re.sub(r'"[^"]+"', "", normalized).strip()
    tokens = content_tokens(remaining, min_len=3)

    # Build filters
    filters = []

    # Exact phrase matches (look for the phrase as-is, case-insensitive)
    for phrase in exact_phrases:
        filters.append(DocumentChunk.chunk_text.ilike(f"%{phrase}%"))

    # Token-level matches
    for token in tokens:
        filters.append(DocumentChunk.chunk_text.ilike(f"%{token}%"))

    # If no filters, return empty
    if not filters:
        return []

    statement = (
        select(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(or_(*filters) if len(filters) > 1 else filters[0])
        .limit(top_k * 3)  # fetch extra for scoring
    )

    rows = list(db.execute(statement).scalars().unique())

    results = []
    for chunk in rows:
        score = _score_chunk_lexical(
            chunk=chunk,
            normalized_query=normalized,
            exact_phrases=exact_phrases,
            tokens=tokens,
        )
        results.append(
            RetrievalResult(
                source_type="chunk",
                document_id=chunk.document_id,
                document_name=chunk.document.filename if chunk.document else "",
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
                text=chunk.chunk_text,
                score=score,
                retrieval_method="lexical",
                section=None,
                copy_type=None,
                chunking_strategy=chunk.chunking_strategy,
                source_checksum=chunk.checksum,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]


def _score_chunk_lexical(
    chunk: DocumentChunk,
    normalized_query: str,
    exact_phrases: list[str],
    tokens: list[str],
) -> float:
    """Score a chunk based on lexical match quality."""
    text_lower = chunk.chunk_text.lower()
    score = 0.0

    # Exact phrase match — strong signal
    for phrase in exact_phrases:
        count = text_lower.count(phrase.lower())
        if count > 0:
            score += 2.0 * count

    # Token matches
    for token in tokens:
        count = text_lower.count(token)
        if count > 0:
            score += 1.0 * count

    # If the chunk exactly (or nearly) matches the query text
    if normalized_query in text_lower:
        score += 0.5

    # Normalize by chunk length to avoid bias toward long chunks
    word_count = len(text_lower.split())
    if word_count > 0:
        score = score / (word_count ** 0.3)  # mild length normalization

    return score