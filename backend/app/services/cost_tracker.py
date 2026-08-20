"""
Cost tracking for the Cost-Aware Knowledge Engine.

Tracks estimated cost per query and maintains running totals.
"""

import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class QueryCostRecord:
    """Cost record for a single query."""

    query: str
    method: str
    llm_used: bool
    retrieval_cost: float = 0.0
    llm_cost: float = 0.0
    total_cost: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class CostTracker:
    """
    Tracks estimated costs for queries.

    Pure estimation based on token counts — no external billing API.
    """

    def __init__(self):
        self._records: list[QueryCostRecord] = []
        self._lock = threading.Lock()
        self._total_cost = 0.0

    def record_query(
        self,
        query: str,
        method: str,
        llm_used: bool,
        retrieval_cost: float = 0.0,
        llm_cost: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        duration_ms: float = 0.0,
    ) -> QueryCostRecord:
        """Record costs for a single query and return the record."""
        record = QueryCostRecord(
            query=query,
            method=method,
            llm_used=llm_used,
            retrieval_cost=retrieval_cost,
            llm_cost=llm_cost,
            total_cost=retrieval_cost + llm_cost,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            timestamp=time.time(),
        )
        with self._lock:
            self._records.append(record)
            self._total_cost += record.total_cost
        return record

    def get_total_cost(self) -> float:
        """Get the running total cost across all recorded queries."""
        with self._lock:
            return self._total_cost

    def get_recent(self, n: int = 10) -> list[QueryCostRecord]:
        """Get the most recent N cost records."""
        with self._lock:
            return list(self._records[-n:])

    def get_stats(self) -> dict:
        """Get aggregated cost statistics."""
        with self._lock:
            total_queries = len(self._records)
            llm_calls = sum(1 for r in self._records if r.llm_used)
            avg_cost = (
                self._total_cost / total_queries if total_queries > 0 else 0.0
            )
            return {
                "total_queries": total_queries,
                "total_cost": round(self._total_cost, 8),
                "average_cost": round(avg_cost, 8),
                "llm_calls": llm_calls,
                "cache_eligible": total_queries,
            }

    def reset(self) -> None:
        """Reset all cost tracking data."""
        with self._lock:
            self._records.clear()
            self._total_cost = 0.0


# Global singleton for app-wide use
_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get or create the global cost tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker