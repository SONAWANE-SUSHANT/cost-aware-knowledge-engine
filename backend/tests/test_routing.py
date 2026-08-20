"""
Comprehensive tests for query normalization, analysis, and routing.
"""

from app.services.routing.analyzer import QueryAnalyzer
from app.services.routing.normalizer import QueryNormalizer, normalize
from app.services.routing.router import (
    QueryRouter,
    QueryType,
    RetrievalStrategy,
    route_query,
)


# ---------------------------------------------------------------------------
# Query Normalization Tests
# ---------------------------------------------------------------------------


def test_normalize_trims_whitespace():
    assert normalize("  hello world  ") == "hello world"


def test_normalize_collapses_multiple_spaces():
    assert normalize("hello   world    test") == "hello world test"


def test_normalize_preserves_identifiers():
    assert normalize("What is the vehicle number for LR-00501?") == \
        "What is the vehicle number for LR-00501"


def test_normalize_preserves_numbers():
    assert normalize("INVOICE VALUE: 125584.00") == "INVOICE VALUE: 125584.00"


def test_normalize_preserves_dates():
    assert normalize("What is the date of 15/8/2026?") == \
        "What is the date of 15/8/2026"


def test_normalize_empty_string():
    assert normalize("") == ""


def test_normalize_whitespace_only():
    assert normalize("   ") == ""


def test_normalize_does_not_rewrite():
    """Normalization must preserve semantic meaning."""
    original = "What is the vehicle number for LR-00501?"
    normalized = normalize(original)
    # Should not change word order or remove meaningful words
    assert "vehicle" in normalized
    assert "LR-00501" in normalized


# ---------------------------------------------------------------------------
# Query Analysis Tests
# ---------------------------------------------------------------------------


def test_analysis_extracts_identifiers():
    analysis = QueryAnalyzer().analyze("What is the status of LR-00501?")
    assert "LR-00501" in analysis.identifiers


def test_analysis_extracts_numbers():
    analysis = QueryAnalyzer().analyze("Show me the document with value 125584.00")
    assert "125584.00" in analysis.numbers


def test_analysis_extracts_dates():
    analysis = QueryAnalyzer().analyze("What happened on 15/8/2026?")
    assert "15/8/2026" in analysis.dates


def test_analysis_extracts_possible_fields():
    analysis = QueryAnalyzer().analyze("What is the invoice number?")
    assert len(analysis.possible_fields) > 0
    assert any("invoice" in f for f in analysis.possible_fields)


def test_analysis_question_type_what():
    analysis = QueryAnalyzer().analyze("What is the total amount?")
    assert analysis.question_type == "what"


def test_analysis_question_type_compare():
    analysis = QueryAnalyzer().analyze("Compare the totals in these documents")
    assert analysis.question_type == "comparison"


def test_analysis_question_type_why():
    analysis = QueryAnalyzer().analyze("Why is the cost different?")
    assert analysis.question_type == "why"
def test_analysis_question_type_why_price_different():
    """'Why' must not be overridden by 'different' comparison keyword."""
    analysis = QueryAnalyzer().analyze("Why is the price different?")
    assert analysis.question_type == "why"


def test_analysis_question_type_why_values_different():
    analysis = QueryAnalyzer().analyze("Why are these values different?")
    assert analysis.question_type == "why"


def test_analysis_question_type_why_document_differs():
    analysis = QueryAnalyzer().analyze("Why does this document differ?")
    assert analysis.question_type == "why"


def test_analysis_has_comparison_keywords():
    analysis = QueryAnalyzer().analyze("Compare the delivery information in these two documents")
    assert analysis.has_comparison_keywords is True


def test_analysis_has_synthesis_keywords():
    analysis = QueryAnalyzer().analyze("Explain why the total cost differs")
    assert analysis.has_synthesis_keywords is True


def test_analysis_empty_query():
    analysis = QueryAnalyzer().analyze("")
    assert analysis.normalized == ""
    assert analysis.token_count == 0


def test_analysis_document_references():
    analysis = QueryAnalyzer().analyze("Find document LR-00501")
    assert "LR-00501" in analysis.document_references


# ---------------------------------------------------------------------------
# Query Router Tests
# ---------------------------------------------------------------------------


def test_route_empty_query():
    route = route_query("")
    assert route.query_type == QueryType.UNKNOWN
    assert route.retrieval_strategy == RetrievalStrategy.NONE
    assert route.llm_allowed is False


def test_route_direct_fact_invoice():
    route = route_query("What is the invoice number?")
    assert route.query_type == QueryType.DIRECT_FACT
    assert route.retrieval_strategy == RetrievalStrategy.STRUCTURED
    assert route.llm_allowed is False


def test_route_direct_fact_vehicle():
    route = route_query("vehicle number")
    assert route.query_type == QueryType.DIRECT_FACT
    assert route.retrieval_strategy == RetrievalStrategy.STRUCTURED
    assert route.llm_allowed is False


def test_route_exact_lookup_identifier():
    route = route_query("LR-00501")
    assert route.query_type == QueryType.EXACT_LOOKUP
    assert route.retrieval_strategy == RetrievalStrategy.EXACT
    assert route.llm_allowed is False


def test_route_exact_lookup_vehicle_number():
    route = route_query("MH20GC-9895")
def test_route_structured_lookup_invoice():
    route = route_query("What is the invoice number for INV-123?")
    assert route.query_type == QueryType.STRUCTURED_LOOKUP
    assert route.retrieval_strategy == RetrievalStrategy.HYBRID
    assert route.llm_allowed is False


def test_route_structured_lookup_status():
    route = route_query("What is the status for DOC-456?")
    assert route.query_type == QueryType.STRUCTURED_LOOKUP
    assert route.retrieval_strategy == RetrievalStrategy.HYBRID
    assert route.llm_allowed is False


def test_route_structured_lookup_amount():
    route = route_query("What is the amount for ABC-789?")

    assert route.query_type == QueryType.STRUCTURED_LOOKUP
    assert route.retrieval_strategy == RetrievalStrategy.HYBRID
    assert route.llm_allowed is False


def test_route_structured_lookup_with_doc_ref():
    route = route_query("What is the vehicle number for LR-00501?")
    assert route.query_type == QueryType.STRUCTURED_LOOKUP
    assert route.retrieval_strategy == RetrievalStrategy.HYBRID
    assert route.llm_allowed is False


def test_route_semantic_lookup():
    route = route_query("What does this document say about delivery?")
    assert route.query_type == QueryType.SEMANTIC_LOOKUP
    assert route.retrieval_strategy == RetrievalStrategy.HYBRID
    assert route.llm_allowed is False


def test_route_multi_evidence():
    route = route_query("Compare the delivery information in these two documents")
    assert route.query_type == QueryType.MULTI_EVIDENCE
    assert route.retrieval_strategy == RetrievalStrategy.MULTI_EVIDENCE
    assert route.llm_allowed is True


def test_route_synthesis():
    route = route_query("Explain why the total cost differs between these documents")
    assert route.query_type == QueryType.SYNTHESIS
    assert route.retrieval_strategy == RetrievalStrategy.MULTI_EVIDENCE
    assert route.llm_allowed is True


def test_route_synthesis_why():
    route = route_query("Why is the cost higher?")
    assert route.query_type == QueryType.SYNTHESIS
    assert route.llm_allowed is True


def test_route_unknown_single_char():
    route = route_query("?")
    assert route.query_type == QueryType.UNKNOWN


def test_route_numeric_question():
    route = route_query("What is the total amount?")
    # "amount" is a field keyword, should be direct fact
    assert route.query_type == QueryType.DIRECT_FACT
    assert route.llm_allowed is False


def test_route_date_question():
    route = route_query("What is the date?")
    assert route.query_type == QueryType.DIRECT_FACT
    assert route.llm_allowed is False


# ---------------------------------------------------------------------------
# Route Object Serialization Tests
# ---------------------------------------------------------------------------


def test_route_to_dict():
    route = route_query("What is the invoice number?")
    d = route.to_dict()
    assert d["query_type"] == "DIRECT_FACT"
    assert d["retrieval_strategy"] == "structured"
    assert d["llm_allowed"] is False
    assert "reason" in d


def test_route_llm_allowed_distinction():
    """Simple factual queries must not allow LLM, synthesis queries may."""
    fact_route = route_query("What is the invoice number?")
    synthesis_route = route_query("Explain why the total cost differs")

    assert fact_route.llm_allowed is False
    assert synthesis_route.llm_allowed is True


# ---------------------------------------------------------------------------
# Integration with Existing Retrieval
# ---------------------------------------------------------------------------


def test_route_works_with_existing_retrieval_flow():
    """
    Routing output should be compatible with the existing retrieval layer.
    """
    router = QueryRouter()
    route = router.route("What is the vehicle number?")

    # Route should indicate a cheap retrieval strategy for this fact question
    assert route.retrieval_strategy in (
        RetrievalStrategy.STRUCTURED,
        RetrievalStrategy.HYBRID,
        RetrievalStrategy.EXACT,
    )
    assert route.llm_allowed is False