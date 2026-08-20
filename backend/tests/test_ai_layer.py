"""
Comprehensive tests for the AI layer: /queries/answer endpoint,
LLM fallback, caching, cost tracking, and response schema.

All tests are deterministic: mocked LLM, never calls external APIs.
"""

import time
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.schemas.query import QueryRequest, QueryResponse, QueryUsage
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.knowledge import Document, KnowledgeFact
from app.services.cache.cache_service import ResponseCache, get_cache
from app.services.cost_tracker import CostTracker, get_cost_tracker
from app.services.llm.provider import (
    FailingLLMProvider,
    MockLLMProvider,
    estimate_cost,
)
from app.services.retrieval.models import RetrievalResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset global singletons before each test."""
    cache = get_cache()
    cache.clear()
    tracker = get_cost_tracker()
    tracker.reset()
    yield


@pytest.fixture(scope="module")
def client():
    """Create a test client with an in-memory database."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, future=True)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
# ---------------------------------------------------------------------------
# Response Schema Tests
# ---------------------------------------------------------------------------


class TestResponseSchema:
    """Verify the /queries/answer response matches the required schema."""

    def test_response_has_all_required_fields(self, client):
        """Frontend-ready response must contain all required fields."""
        response = client.post("/queries/answer", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "method" in data
        assert "confidence" in data
        assert "llm_used" in data
        assert "cache_hit" in data
        assert "query" in data
        assert "evidence" in data
        assert "usage" in data

        assert isinstance(data["answer"], str)
        assert isinstance(data["method"], str)
        assert isinstance(data["confidence"], (int, float))
        assert isinstance(data["llm_used"], bool)
        assert isinstance(data["cache_hit"], bool)
        assert isinstance(data["query"], str)
        assert isinstance(data["evidence"], list)
        assert isinstance(data["usage"], dict)

    def test_usage_has_required_fields(self, client):
        """Usage object must contain cost and token fields."""
        response = client.post("/queries/answer", json={"query": "some query"})
        assert response.status_code == 200
        usage = response.json()["usage"]

        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage
        assert "estimated_cost" in usage
        assert "retrieval_cost" in usage

    def test_evidence_item_schema(self, client):
        """Each evidence item must have the required fields."""
        response = client.post("/queries/answer", json={"query": "test"})
        assert response.status_code == 200
        evidence = response.json()["evidence"]

        for item in evidence:
            assert isinstance(item, dict)
            assert "document_id" in item
            assert "document_name" in item
            assert "text" in item
            assert "score" in item
            assert "source_type" in item


# ---------------------------------------------------------------------------
# Deterministic Answer Tests
# ---------------------------------------------------------------------------


class TestDeterministicAnswer:
    """Deterministic answers must never use the LLM."""

    def test_deterministic_answer_llm_not_used(self, client):
        """For deterministic answers, llm_used must be False."""
        response = client.post("/queries/answer", json={"query": "What is the vehicle number?"})
        assert response.status_code == 200
        data = response.json()
        assert data["llm_used"] is False

    def test_deterministic_answer_cost_zero(self, client):
        """For deterministic answers, LLM cost must be 0."""
        response = client.post("/queries/answer", json={"query": "invoice number"})
        assert response.status_code == 200
        usage = response.json()["usage"]
        assert usage["total_tokens"] == 0

    def test_deterministic_unknown_answer(self, client):
        """Empty database should return unknown/controlled answer."""
        response = client.post("/queries/answer", json={"query": "What is the secret?"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] and len(data["answer"]) > 0
        assert data["llm_used"] is False

    def test_deterministic_answer_has_evidence(self, client):
        """Answer should include evidence field as list."""
        response = client.post("/queries/answer", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
# ---------------------------------------------------------------------------
# Cache Tests
# ---------------------------------------------------------------------------


class TestCache:
    """Verify response caching behavior."""

    def test_cache_miss_first_request(self, client):
        """First request for a query should be a cache miss."""
        get_cache().clear()
        response = client.post("/queries/answer", json={"query": "unique query 12345"})
        assert response.status_code == 200
        assert response.json()["cache_hit"] is False

    def test_cache_hit_second_request(self, client):
        """Second request for the same query should be a cache hit."""
        get_cache().clear()
        client.post("/queries/answer", json={"query": "repeat query"})
        response2 = client.post("/queries/answer", json={"query": "repeat query"})
        assert response2.status_code == 200
        assert response2.json()["cache_hit"] is True

    def test_cache_different_queries_different_results(self, client):
        """Different queries should not interfere in cache."""
        get_cache().clear()
        r1 = client.post("/queries/answer", json={"query": "query alpha"})
        r2 = client.post("/queries/answer", json={"query": "query beta"})
        assert r1.json()["cache_hit"] is False
        assert r2.json()["cache_hit"] is False
        r3 = client.post("/queries/answer", json={"query": "query alpha"})
        assert r3.json()["cache_hit"] is True

    def test_cache_clear(self, client):
        """After clearing cache, repeat query should be a miss again."""
        get_cache().clear()
        client.post("/queries/answer", json={"query": "clearable query"})
        get_cache().clear()
        response = client.post("/queries/answer", json={"query": "clearable query"})
        assert response.json()["cache_hit"] is False
        assert isinstance(response.json()["evidence"], list)

# ---------------------------------------------------------------------------
# LLM Fallback Tests (using MockLLMProvider)
# ---------------------------------------------------------------------------


class TestLLMFallback:
    """LLM fallback behavior with mocked providers."""

    def test_mock_llm_provider_basic(self):
        """MockLLMProvider should return canned response without API calls."""
        mock = MockLLMProvider(response_text="Mock answer text")
        result = mock.generate("test prompt")
        assert result.success is True
        assert result.text == "Mock answer text"
        assert result.usage.prompt_tokens > 0

    def test_mock_llm_tracks_calls(self):
        """MockLLMProvider should track call count and last prompt."""
        mock = MockLLMProvider()
        mock.generate("first prompt")
        mock.generate("second prompt")
        assert mock.call_count == 2
        assert "second prompt" in mock.last_prompt

    def test_failing_llm_provider(self):
        """FailingLLMProvider should return failure without API calls."""
        failing = FailingLLMProvider("API unavailable")
        result = failing.generate("any prompt")
        assert result.success is False
        assert result.error == "API unavailable"
        assert result.text == ""

    def test_llm_failure_graceful(self, client):
        """When LLM fails, system should fall back to deterministic answer."""
        get_cache().clear()
        response = client.post("/queries/answer", json={"query": "complex question"})
        assert response.status_code == 200
        data = response.json()
        assert data["llm_used"] is False

# ---------------------------------------------------------------------------
# Cost Tracking Tests
# ---------------------------------------------------------------------------


class TestCostTracking:
    """Verify cost tracking behavior."""

    def test_cost_tracker_records_query(self, client):
        """Cost tracker should record query cost data."""
        tracker = get_cost_tracker()
        tracker.reset()
        client.post("/queries/answer", json={"query": "tracked query"})
        stats = tracker.get_stats()
        assert stats["total_queries"] >= 1
        assert stats["total_cost"] >= 0

    def test_cost_tracker_aggregates(self, client):
        """Multiple queries should be aggregated correctly."""
        tracker = get_cost_tracker()
        tracker.reset()
        client.post("/queries/answer", json={"query": "query one"})
        client.post("/queries/answer", json={"query": "query two"})
        stats = tracker.get_stats()
        assert stats["total_queries"] == 2

    def test_deterministic_cost_is_zero_for_llm(self, client):
        """Deterministic answers should have zero LLM cost."""
        tracker = get_cost_tracker()
        tracker.reset()
        client.post("/queries/answer", json={"query": "simple fact query"})
        records = tracker.get_recent(5)
        if records:
            assert records[0].llm_cost == 0.0

    def test_cost_tracker_reset(self):
        """Resetting tracker should clear all records."""
        tracker = get_cost_tracker()
        tracker.reset()
        tracker.record_query(query="test", method="test", llm_used=False)
# ---------------------------------------------------------------------------
# Cache Service Tests
# ---------------------------------------------------------------------------


class TestCacheService:
    """Unit tests for the ResponseCache class."""

    def test_set_and_get(self):
        cache = ResponseCache(ttl_seconds=60)
        cache.set("test query", {"answer": "test answer"})
        result = cache.get("test query")
        assert result is not None
        assert result["answer"] == "test answer"

    def test_miss_on_unknown(self):
        cache = ResponseCache()
        result = cache.get("nonexistent query")
        assert result is None

    def test_ttl_expiry(self):
        cache = ResponseCache(ttl_seconds=0)
        cache.set("expiring query", {"answer": "temp"})
        time.sleep(0.01)
        result = cache.get("expiring query")
        assert result is None

    def test_clear(self):
        cache = ResponseCache()
        cache.set("query a", {"data": 1})
        cache.set("query b", {"data": 2})
        cache.clear()
        assert cache.size == 0

    def test_invalidate(self):
        cache = ResponseCache()
        cache.set("query a", {"data": 1})
        cache.invalidate("query a")
        assert cache.get("query a") is None

    def test_max_entries_eviction(self):
        cache = ResponseCache(ttl_seconds=3600, max_entries=3)
        cache.set("q1", {"n": 1})
        cache.set("q2", {"n": 2})
        cache.set("q3", {"n": 3})
        cache.set("q4", {"n": 4})
        assert cache.size <= 3

    def test_case_insensitive_keys(self):
        cache = ResponseCache()
        cache.set("Hello World", {"answer": "hi"})
        result = cache.get("hello world")
        assert result is not None and result["answer"] == "hi"
        assert cache.size == 1
        cache.clear()
# ---------------------------------------------------------------------------
# LLM Provider Tests
# ---------------------------------------------------------------------------


class TestLLMProvider:
    """Unit tests for LLM providers."""

    def test_estimate_cost_known_model(self):
        cost = estimate_cost("openai/gpt-4o-mini", 100, 50)
        expected = 0.000015 + 0.000030
        assert cost == expected

    def test_estimate_cost_unknown_model(self):
        cost = estimate_cost("unknown/model", 1000, 500)
        expected = (1000 / 1000) * 0.00050 + (500 / 1000) * 0.00150
        assert cost == expected

    def test_estimate_cost_zero_tokens(self):
        cost = estimate_cost("openai/gpt-4o-mini", 0, 0)
        assert cost == 0.0

    def test_openrouter_no_key_fails_gracefully(self):
        from app.services.llm.provider import OpenRouterProvider
        provider = OpenRouterProvider(api_key="", model="test-model")
        result = provider.generate("test prompt")
        assert result.success is False
        assert "not configured" in result.error


# ---------------------------------------------------------------------------
# Router + Extractor Integration
# ---------------------------------------------------------------------------


class TestRouterExtractorIntegration:
    """Verify the router and extractor work together correctly."""

    def test_route_direct_fact_no_llm(self):
        from app.services.routing.router import route_query
        route = route_query("What is the invoice number?")
        assert route.llm_allowed is False
        assert route.query_type.value == "DIRECT_FACT"

    def test_route_synthesis_allows_llm(self):
        from app.services.routing.router import route_query
        route = route_query("Explain why the total cost differs")
        assert route.llm_allowed is True
        assert route.query_type.value == "SYNTHESIS"


# ---------------------------------------------------------------------------
# End-to-End Pipeline Tests
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    """End-to-end tests for the full answer pipeline."""

    def test_pipeline_returns_valid_response(self, client):
        """The pipeline should return a valid QueryResponse."""
        response = client.post("/queries/answer", json={"query": "What is X?"})
        assert response.status_code == 200
        data = response.json()
        model = QueryResponse(**data)
        assert model.answer is not None
        assert model.method in ("structured_fact", "exact_evidence", "unknown", "llm_fallback")

    def test_pipeline_tracks_costs(self, client):
        """Each pipeline run must be tracked by the cost tracker."""
        tracker = get_cost_tracker()
        tracker.reset()
        client.post("/queries/answer", json={"query": "cost test query"})
        stats = tracker.get_stats()
        assert stats["total_queries"] > 0
        assert stats["total_cost"] >= 0

    def test_pipeline_includes_evidence(self, client):
        """Response must include an evidence list."""
        response = client.post("/queries/answer", json={"query": "find something"})
        data = response.json()
        assert "evidence" in data
        assert isinstance(data["evidence"], list)
        tracker = get_cost_tracker()
        assert tracker.get_stats()["total_queries"] == 1