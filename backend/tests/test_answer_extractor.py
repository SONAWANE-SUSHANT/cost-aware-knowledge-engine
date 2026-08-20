"""
Regression tests for AnswerExtractor.extract().

Covers the bug where a deterministic "Field: Value" match in a retrieved
chunk was discarded because it sat behind a fixed retrieval-score cutoff,
leaving DIRECT_FACT-routed queries (which disallow the LLM fallback) with
no way to ever surface a correct, already-retrieved answer.
"""

import pytest

from app.services.answering.answer_extractor import AnswerExtractor
from app.services.retrieval.models import RetrievalResult


def _chunk_result(text, score, document_id="doc-1", document_name="LR-001.pdf"):
    return RetrievalResult(
        document_id=document_id,
        document_name=document_name,
        page_number=1,
        text=text,
        field=None,
        value=None,
        score=score,
        source_type="chunk",
        confidence=None,
    )


class TestDirectFactExtraction:
    """The originally-reported bug: 'what was the total amount'."""

    def test_total_amount_extracted_below_old_threshold(self):
        extractor = AnswerExtractor()
        # Score deliberately BELOW the old hard-coded 0.75 gate to prove
        # the fix no longer depends on it.
        results = [_chunk_result("Total Amount : 5600", score=0.62)]

        response = extractor.extract(
            query="what was the total amount",
            results=results,
            query_type="DIRECT_FACT",
        )

        assert response.answer == "5600"
        assert response.method == "exact_evidence"
        assert response.llm_used is False

    def test_different_field_not_hardcoded(self):
        """Proves the fix is generic, not specific to 'total amount'."""
        extractor = AnswerExtractor()
        results = [_chunk_result("LR Number : LR-001", score=0.55)]

        response = extractor.extract(
            query="what is the LR number",
            results=results,
            query_type="DIRECT_FACT",
        )

        assert response.answer == "LR-001"
        assert response.method == "exact_evidence"
        assert response.llm_used is False

    def test_tries_lower_scored_candidate_when_top_result_has_no_match(self):
        """The old code only ever inspected the single top-scored result."""
        extractor = AnswerExtractor()
        results = [
            _chunk_result("Some unrelated boilerplate text.", score=0.9),
            _chunk_result("Total Amount : 5600", score=0.4),
        ]

        response = extractor.extract(
            query="what was the total amount",
            results=results,
            query_type="DIRECT_FACT",
        )

        assert response.answer == "5600"
        assert response.method == "exact_evidence"


class TestSynthesisStillReachesLLM:
    """Explanation/synthesis queries must not be short-circuited."""

    def test_synthesis_query_skips_text_extraction(self):
        extractor = AnswerExtractor()
        # Same evidence chunk as the direct-fact case, on purpose.
        results = [_chunk_result("Total Amount : 5600", score=0.62)]

        response = extractor.extract(
            query="Explain how the total amount was calculated.",
            results=results,
            query_type="SYNTHESIS",
        )

        # Must fall through to "unknown" so the caller's needs_llm check
        # (method == "unknown" or confidence < 0.3) triggers the existing
        # OpenRouter LLM fallback instead of returning a bare "5600".
        assert response.method == "unknown"
        assert response.confidence == 0.0
        assert response.llm_used is False


class TestNoHallucination:
    def test_missing_information_returns_unknown(self):
        extractor = AnswerExtractor()
        results = [_chunk_result("Vehicle Number : MH20GC-9895", score=0.8)]

        response = extractor.extract(
            query="what is the destination city",
            results=results,
            query_type="DIRECT_FACT",
        )

        assert response.method == "unknown"
        assert response.answer == AnswerExtractor.UNKNOWN_ANSWER

    def test_no_results_returns_unknown(self):
        extractor = AnswerExtractor()
        response = extractor.extract(
            query="what was the total amount",
            results=[],
            query_type="DIRECT_FACT",
        )
        assert response.method == "unknown"


class TestBackwardCompatibility:
    def test_query_type_defaults_to_none_and_still_extracts(self):
        """Existing callers that don't pass query_type keep working."""
        extractor = AnswerExtractor()
        results = [_chunk_result("Total Amount : 5600", score=0.62)]

        response = extractor.extract(query="what was the total amount", results=results)

        assert response.answer == "5600"
        assert response.method == "exact_evidence"