"""
Hybrid retrieval service.

Combines structured facts, lexical chunk search, and semantic vector
search into a single ranked, deduplicated evidence set.

Scoring strategy (deterministic, no LLM):
    final_score = structured_weight * structured_score
                + lexical_weight    * lexical_score
                + semantic_weight   * semantic_score

All component scores are normalized to [0, 1] before weighting.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.embeddings.provider import EmbeddingProvider
from app.services.retrieval.lexical_retriever import retrieve_lexical_chunks
from app.services.retrieval.models import RetrievalResponse, RetrievalResult
from app.services.retrieval.semantic_retriever import retrieve_semantic_chunks
from app.services.retrieval.structured_retriever import retrieve_structured_facts


@dataclass
class HybridWeights:
    """Configurable weights for hybrid scoring."""

    structured: float = 0.4
    lexical: float = 0.3
    semantic: float = 0.3

    def normalize(self):
        total = self.structured + self.lexical + self.semantic
        if total <= 0:
            raise ValueError("Retrieval weights must sum to > 0")
        self.structured /= total
        self.lexical /= total
        self.semantic /= total
        return self


def get_default_weights() -> HybridWeights:
    """Read weights from settings, falling back to defaults."""
    return HybridWeights(
        structured=float(getattr(settings, "retrieval_weight_structured", 0.4)),
        lexical=float(getattr(settings, "retrieval_weight_lexical", 0.3)),
        semantic=float(getattr(settings, "retrieval_weight_semantic", 0.3)),
    ).normalize()


def retrieve(
    db: Session,
    query: str,
    top_k: int = 5,
    weights: Optional[HybridWeights] = None,
    embedding_provider: Optional[EmbeddingProvider] = None,
) -> RetrievalResponse:
    """
    Retrieve evidence for a query using hybrid retrieval.

    Combines structured facts, lexical chunks, and semantic chunks.
    Returns a deduplicated, ranked list of RetrievalResult items.
    """
    if not query or not query.strip():
        return RetrievalResponse(query=query, top_k=top_k, results=[])

    weights = weights or get_default_weights()
    query = query.strip()

    # --- Candidate Generation ---
    structured_results = retrieve_structured_facts(
        db=db, query=query, top_k=top_k * 3,
    )
    lexical_results = retrieve_lexical_chunks(
        db=db, query=query, top_k=top_k * 3,
    )
    semantic_results = retrieve_semantic_chunks(
        db=db, query=query, top_k=top_k * 3,
        embedding_provider=embedding_provider,
    )

    # --- Candidate Fusion ---
    candidates: list[RetrievalResult] = []
    candidates.extend(structured_results)
    candidates.extend(lexical_results)
    candidates.extend(semantic_results)

    # --- Normalize component scores to [0, 1] ---
    candidates = _normalize_scores(candidates)

    # --- Deduplication ---
    # Merge candidates that refer to the same fact_id or same chunk_id.
    deduplicated = _deduplicate(candidates)

    # --- Weighted Ranking ---
    for result in deduplicated:
        structured_score = result.score if result.retrieval_method == "structured" else 0.0
        lexical_score = result.score if result.retrieval_method == "lexical" else 0.0
        semantic_score = result.score if result.retrieval_method == "semantic" else 0.0

        result.score = (
            weights.structured * structured_score
            + weights.lexical * lexical_score
            + weights.semantic * semantic_score
        )
        result.retrieval_method = "hybrid"

    # Add a bonus for exact identifier matches (e.g., "MH20GC-9895")
    # This is a deterministic metadata-relevance boost, not LLM-based.
    for result in deduplicated:
        if _is_exact_identifier_match(query, result):
            result.score += 0.2

    # Sort by final score, stable tiebreak by source type
    deduplicated.sort(
        key=lambda r: (r.score, r.source_type),
        reverse=True,
    )

    # --- Evidence Set ---
    results = deduplicated[:top_k]
    return RetrievalResponse(
        query=query,
        top_k=top_k,
        results=results,
        total_results=len(results),
    )


def _normalize_scores(
    results: list[RetrievalResult],
) -> list[RetrievalResult]:
    """
    Normalize component scores to [0, 1] per retrieval method.
    """
    methods = {}
    for result in results:
        if result.retrieval_method not in methods:
            methods[result.retrieval_method] = []
        methods[result.retrieval_method].append(result)

    for method, group in methods.items():
        max_score = max((r.score for r in group), default=0.0)
        if max_score > 0:
            for result in group:
                result.score = result.score / max_score

    return results


def _deduplicate(
    results: list[RetrievalResult],
) -> list[RetrievalResult]:
    """
    Deduplicate evidence while preserving provenance.

    - Facts with the same fact_id are merged (keep highest score).
    - Chunks with the same chunk_id are merged (keep highest score,
      preserve both chunking strategies if applicable).
    - A fact and a chunk are NOT merged: they are different evidence types
      even if they contain the same information.
    """
    merged: dict[str, RetrievalResult] = {}

    for result in results:
        if result.source_type == "fact" and result.fact_id:
            key = f"fact:{result.fact_id}"
        elif result.source_type == "chunk" and result.chunk_id:
            key = f"chunk:{result.chunk_id}"
        else:
            key = f"{result.source_type}:{result.text}:{result.document_id}"

        if key in merged:
            existing = merged[key]
            # Keep the highest raw score
            if result.score > existing.score:
                existing.score = result.score
            # Preserve provenance: merge metadata
            if result.chunking_strategy and existing.chunking_strategy:
                if result.chunking_strategy != existing.chunking_strategy:
                    existing.chunking_strategy = (
                        f"{existing.chunking_strategy},{result.chunking_strategy}"
                    )
            elif result.chunking_strategy:
                existing.chunking_strategy = result.chunking_strategy
        else:
            merged[key] = result

    return list(merged.values())


def _is_exact_identifier_match(query: str, result: RetrievalResult) -> bool:
    """Detect whether the query closely matches a specific value or field."""
    query_norm = query.strip().lower()
    value_norm = (result.value or "").strip().lower()
    field_norm = (result.field or "").strip().lower()

    # Exact value match (e.g., a vehicle number, invoice number)
    if value_norm and query_norm == value_norm:
        return True

    # Query equals field name
    if field_norm and query_norm == field_norm:
        return True

    return False