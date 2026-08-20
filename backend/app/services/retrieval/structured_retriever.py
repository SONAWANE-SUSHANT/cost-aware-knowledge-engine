"""
Structured fact retrieval.

Searches the existing KnowledgeFact table for exact and partial matches
on field names and values.  No LLM required.
"""

from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models.knowledge import Document, KnowledgeFact
from app.services.retrieval.models import RetrievalResult


def retrieve_structured_facts(
    db: Session,
    query: str,
    top_k: int = 5,
) -> list[RetrievalResult]:
    """
    Search structured facts by field name and value.

    Matching is case-insensitive and covers:
      - field name contains query tokens
      - value contains query tokens
      - exact field:value matches
    """
    normalized = query.strip().lower()
    tokens = [t for t in normalized.split() if t]

    if not tokens:
        return []

    # Build a filter that matches any token against field or value
    filters = []
    for token in tokens:
        filters.append(
            KnowledgeFact.field.ilike(f"%{token}%")
        )
        filters.append(
            KnowledgeFact.value.ilike(f"%{token}%")
        )

    statement = (
        select(KnowledgeFact)
        .join(Document, KnowledgeFact.document_id == Document.id)
        .where(or_(*filters))
        .order_by(KnowledgeFact.confidence.desc())
        .limit(top_k * 2)  # fetch extra for dedup later
    )

    rows = list(db.execute(statement).scalars().unique())

    results = []
    for fact in rows:
        # Compute a simple relevance score based on match quality
        score = _score_fact(fact, normalized, tokens)
        results.append(
            RetrievalResult(
                source_type="fact",
                document_id=fact.document_id,
                document_name=fact.document.filename if fact.document else "",
                page_number=fact.page_number,
                fact_id=fact.id,
                text=f"{fact.field}: {fact.value}",
                field=fact.field,
                value=fact.value,
                score=score,
                retrieval_method="structured",
                section=fact.section,
                copy_type=fact.copy_type,
                source_checksum=fact.source_checksum,
                confidence=fact.confidence,
            )
        )

    # Sort by score descending and take top_k
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]


def _score_fact(
    fact: KnowledgeFact,
    normalized_query: str,
    tokens: list[str],
) -> float:
    """Score a fact based on how well it matches the query."""
    field_lower = (fact.field or "").lower()
    value_lower = (fact.value or "").lower()
    score = 0.0

    # Exact field match
    if field_lower == normalized_query:
        score += 1.0
    # Exact value match
    if value_lower == normalized_query:
        score += 1.0
    # Field contains query
    if normalized_query in field_lower:
        score += 0.8
    # Value contains query
    if normalized_query in value_lower:
        score += 0.8

    # Token-level matches
    for token in tokens:
        if token in field_lower:
            score += 0.5
        if token in value_lower:
            score += 0.5

    # Boost by confidence
    score *= (fact.confidence or 1.0)

    return score