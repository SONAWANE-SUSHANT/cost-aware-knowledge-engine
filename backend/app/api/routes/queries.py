"""
Query/retrieval API routes.

Exposes the hybrid retrieval service through REST endpoints,
including the full answer pipeline with LLM fallback.
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.query import (
    QueryEvidence,
    QueryRequest,
    QueryResponse,
    QueryUsage,
)
from app.core.config import settings
from app.db import get_db
from app.services.answering.answer_extractor import AnswerExtractor
from app.services.cache.cache_service import get_cache
from app.services.cost_tracker import get_cost_tracker
from app.services.llm.provider import OpenRouterProvider
from app.services.retrieval import retrieve, RetrievalResponse
from app.services.routing.analyzer import QueryAnalyzer
from app.services.routing.normalizer import normalize
from app.services.routing.router import QueryRouter


router = APIRouter(
    prefix="/queries",
    tags=["Queries"],
)


# Global (lazy) instances
_extractor: Optional[AnswerExtractor] = None
_analyzer: Optional[QueryAnalyzer] = None
_router: Optional[QueryRouter] = None
_llm_provider: Optional[OpenRouterProvider] = None


def _get_extractor() -> AnswerExtractor:
    global _extractor

    if _extractor is None:
        _extractor = AnswerExtractor()

    return _extractor


def _get_analyzer() -> QueryAnalyzer:
    global _analyzer

    if _analyzer is None:
        _analyzer = QueryAnalyzer()

    return _analyzer


def _get_router() -> QueryRouter:
    global _router

    if _router is None:
        _router = QueryRouter()

    return _router


def _get_llm() -> Optional[OpenRouterProvider]:
    """Get the LLM provider only if an API key is configured."""

    global _llm_provider

    if settings.openrouter_api_key:
        if _llm_provider is None:
            _llm_provider = OpenRouterProvider(
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
            )

        return _llm_provider

    return None


# ---------------------------------------------------------------------------
# /search endpoint
# ---------------------------------------------------------------------------

@router.get("/search")
def search(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(
        5,
        ge=1,
        le=50,
        description="Number of results",
    ),
    db: Session = Depends(get_db),
) -> RetrievalResponse:
    """
    Hybrid search across structured facts, lexical chunks,
    and semantic vectors.
    """

    return retrieve(
        db=db,
        query=q,
        top_k=top_k,
    )


# ---------------------------------------------------------------------------
# /answer endpoint
# ---------------------------------------------------------------------------

@router.post("/answer", response_model=QueryResponse)
def answer(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """
    Full answer pipeline:

    normalize -> cache -> analyze -> route -> retrieve
    -> deterministic extraction -> optional LLM fallback
    -> cost tracking -> cache.
    """

    start_time = time.time()

    query_text = request.query.strip()

    cache = get_cache()
    cost_tracker = get_cost_tracker()

    # ------------------------------------------------------------------
    # 1. Normalize
    # ------------------------------------------------------------------

    normalized_query = normalize(query_text)

    # ------------------------------------------------------------------
    # 2. Cache
    # ------------------------------------------------------------------

    cached = cache.get(normalized_query)

    if cached is not None:
        cached["cache_hit"] = True
        return QueryResponse(**cached)

    # ------------------------------------------------------------------
    # 3. Analyze and route
    # ------------------------------------------------------------------

    analysis = _get_analyzer().analyze(normalized_query)
    route = _get_router().route(normalized_query)

    # ------------------------------------------------------------------
    # 4. Retrieve
    # ------------------------------------------------------------------

    retrieval_response = retrieve(
        db=db,
        query=normalized_query,
        top_k=request.top_k,
    )

    # ------------------------------------------------------------------
    # 5. Deterministic answer extraction
    # ------------------------------------------------------------------

    extractor = _get_extractor()

    # IMPORTANT:
    # The actual AnswerExtractor in this project accepts only:
    # extract(query, results)
    answer_response = extractor.extract(
    query=query_text,
    results=retrieval_response.results,
    query_type=route.query_type.value,
)

    llm_used = False
    llm_cost = 0.0

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    # ------------------------------------------------------------------
    # 6. LLM fallback
    # ------------------------------------------------------------------

    needs_llm = (
        answer_response.method == "unknown"
        or answer_response.confidence < 0.3
    )

    if needs_llm and route.llm_allowed:

        llm = _get_llm()

        if llm is not None:

            try:
                evidence_text = "\n".join(
                    (
                        f"- {e.document_name}: "
                        f"{e.field + ': ' if e.field else ''}"
                        f"{e.value or e.text}"
                    )
                    for e in retrieval_response.results[:5]
                )

                prompt = (
                    "Answer the following question based ONLY on "
                    "the provided evidence.\n\n"
                    f"Question: {query_text}\n\n"
                    f"Evidence:\n{evidence_text}\n\n"
                    "Answer concisely:"
                )

                llm_result = llm.generate(
                    prompt=prompt
                )

                if (
                    llm_result.success
                    and llm_result.text
                    and llm_result.text.strip()
                ):

                    answer_response.answer = (
                        llm_result.text.strip()
                    )

                    answer_response.method = "llm_fallback"
                    answer_response.llm_used = True
                    answer_response.confidence = 0.7

                    llm_used = True

                    prompt_tokens = (
                        llm_result.usage.prompt_tokens
                    )

                    completion_tokens = (
                        llm_result.usage.completion_tokens
                    )

                    total_tokens = (
                        llm_result.usage.total_tokens
                    )

                    llm_cost = (
                        llm_result.usage.estimated_cost
                    )

            except Exception:
                # Preserve graceful failure behavior.
                pass

    # ------------------------------------------------------------------
    # 7. Evidence
    # ------------------------------------------------------------------

    evidence_list = [
        QueryEvidence(
            document_id=e.document_id,
            document_name=e.document_name,
            page_number=e.page_number,
            text=e.text,
            field=e.field,
            value=e.value,
            score=e.score,
            source_type=e.source_type,
        )
        for e in answer_response.evidence
    ]

    # ------------------------------------------------------------------
    # 8. Usage / Cost
    # ------------------------------------------------------------------

    retrieval_cost = settings.retrieval_cost_per_query

    total_estimated_cost = (
        retrieval_cost + llm_cost
    )

    usage = QueryUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=round(
            total_estimated_cost,
            8,
        ),
        retrieval_cost=retrieval_cost,
    )

    # ------------------------------------------------------------------
    # 9. Response
    # ------------------------------------------------------------------

    duration_ms = (
        time.time() - start_time
    ) * 1000

    response_data = {
        "answer": answer_response.answer,
        "method": answer_response.method,
        "confidence": answer_response.confidence,
        "llm_used": (
            llm_used
            or answer_response.llm_used
        ),
        "cache_hit": False,
        "query": query_text,
        "evidence": [
            (
                e.to_dict()
                if hasattr(e, "to_dict")
                else e.dict()
            )
            for e in evidence_list
        ],
        "usage": usage,
    }

    # ------------------------------------------------------------------
    # 10. Cost tracking
    # ------------------------------------------------------------------

    cost_tracker.record_query(
        query=query_text,
        method=answer_response.method,
        llm_used=(
            llm_used
            or answer_response.llm_used
        ),
        retrieval_cost=retrieval_cost,
        llm_cost=llm_cost,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
    )

    # ------------------------------------------------------------------
    # 11. Cache
    # ------------------------------------------------------------------

    cache.set(
        normalized_query,
        response_data,
    )

    return QueryResponse(
        **response_data
    )