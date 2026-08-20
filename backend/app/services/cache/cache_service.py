"""
In-memory response cache for the Cost-Aware Knowledge Engine.

Caches answer responses keyed by normalized query to avoid redundant
retrieval and LLM calls.
"""

import hashlib
import json
import threading
import time
from typing import Any, Optional


class ResponseCache:
    """
    Thread-safe in-memory cache for query answers.

    Entries expire after ttl_seconds. The cache is bounded at max_entries
    and evicts oldest entries when full.
    """

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 1000):
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def _make_key(self, query: str) -> str:
        """Generate a stable cache key from a normalized query string."""
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, query: str) -> Optional[Any]:
        """Retrieve a cached response. Returns None on miss or expiry."""
        key = self._make_key(query)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            timestamp, value = entry
            if time.time() - timestamp > self._ttl:
                del self._cache[key]
                return None
            return value

    def set(self, query: str, value: Any) -> None:
        """Cache a response value for the given query."""
        key = self._make_key(query)
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self._max_entries and key not in self._cache:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k][0],
                )
                del self._cache[oldest_key]
            self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()

    def invalidate(self, query: str) -> None:
        """Remove a specific query from the cache."""
        key = self._make_key(query)
        with self._lock:
            self._cache.pop(key, None)

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        with self._lock:
            return len(self._cache)


# Global singleton for app-wide use
_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get or create the global response cache singleton."""
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache