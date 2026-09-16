"""
System metrics and cost tracking routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.knowledge import Document, DocumentChunk, KnowledgeFact, DocumentEmbedding
from app.services.cost_tracker import get_cost_tracker
from app.services.cache.cache_service import get_cache

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"]
)


@router.get("/costs")
def get_costs():
    """Returns aggregated cost metrics, query logs, and estimated savings."""
    tracker = get_cost_tracker()
    stats = tracker.get_stats()
    recent = tracker.get_recent(50)

    # Baseline cost estimation: if standard LLM call ($0.002 avg) had been made for every query
    baseline_llm_cost_per_query = 0.002
    total_queries = stats.get("total_queries", 0)
    baseline_potential_cost = total_queries * baseline_llm_cost_per_query
    actual_cost = stats.get("total_cost", 0.0)
    saved_cost = max(0.0, baseline_potential_cost - actual_cost)

    return {
        "stats": stats,
        "recent_queries": [r.to_dict() for r in reversed(recent)],
        "baseline_potential_cost": round(baseline_potential_cost, 6),
        "estimated_savings": round(saved_cost, 6),
        "savings_percentage": round(
            (saved_cost / baseline_potential_cost * 100) if baseline_potential_cost > 0 else 0,
            1
        ),
    }


@router.post("/costs/reset")
def reset_costs():
    """Reset all query cost records."""
    tracker = get_cost_tracker()
    tracker.reset()
    return {"message": "Cost tracker records reset successfully"}


@router.get("/overview")
def get_system_overview(db: Session = Depends(get_db)):
    """System-wide entity counts and cache statistics."""
    doc_count = db.query(Document).count()
    chunk_count = db.query(DocumentChunk).count()
    fact_count = db.query(KnowledgeFact).count()
    embedding_count = db.query(DocumentEmbedding).count()
    cache = get_cache()
    cache_entries = len(cache._cache) if hasattr(cache, "_cache") else 0
    tracker = get_cost_tracker()

    return {
        "documents": doc_count,
        "chunks": chunk_count,
        "facts": fact_count,
        "embeddings": embedding_count,
        "cache_entries": cache_entries,
        "total_queries": len(tracker._records),
        "total_cost": round(tracker.get_total_cost(), 6),
    }
