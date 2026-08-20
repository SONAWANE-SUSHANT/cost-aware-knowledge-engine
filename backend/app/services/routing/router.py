"""
Query router for the Cost-Aware Knowledge Engine.

Determines the cheapest reliable path for answering a user query.
Uses deterministic rules based on query analysis. No LLM dependency.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.services.routing.analyzer import QueryAnalysis, QueryAnalyzer


class QueryType(str, Enum):
    """
    Categories of user queries.
    Ordered from cheapest to most expensive.
    """
    DIRECT_FACT = "DIRECT_FACT"
    """Single known field lookup, e.g. "What is the invoice number?" """
    EXACT_LOOKUP = "EXACT_LOOKUP"
    """Exact identifier/entity lookup, e.g. "LR-00501" """
    STRUCTURED_LOOKUP = "STRUCTURED_LOOKUP"
    """Structured fact search, e.g. "What is the vehicle number for LR-00501?" """
    SEMANTIC_LOOKUP = "SEMANTIC_LOOKUP"
    """Open-ended semantic search, e.g. "What does this document say about delivery?" """
    MULTI_EVIDENCE = "MULTI_EVIDENCE"
    """Requires evidence from multiple sources, e.g. comparison queries """
    SYNTHESIS = "SYNTHESIS"
    """Requires reasoning/synthesis across evidence, e.g. "Explain why..." """
    UNKNOWN = "UNKNOWN"
    """Unsupported or ambiguous query """


class RetrievalStrategy(str, Enum):
    """The retrieval strategy to use for a given query type."""
    STRUCTURED = "structured"
    """Cheapest: direct fact lookup only."""
    EXACT = "exact"
    """Exact match on identifiers."""
    HYBRID = "hybrid"
    """Combined structured + lexical + semantic."""
    MULTI_EVIDENCE = "multi_evidence"
    """Hybrid retrieval across multiple documents."""
    NONE = "none"
    """No retrieval possible."""


@dataclass
class QueryRoute:
    """
    The routing decision for a user query.

    Attributes:
        query_type: The classified type of the query.
        retrieval_strategy: Which retrieval strategy to use.
        llm_allowed: Whether LLM-based answer generation is permitted.
        reason: Human-readable explanation of the routing decision.
        analysis: The full query analysis signals.
    """
    query_type: QueryType
    retrieval_strategy: RetrievalStrategy
    llm_allowed: bool = False
    reason: str = ""
    analysis: Optional[QueryAnalysis] = None

    def to_dict(self) -> dict:
        return {
            "query_type": self.query_type.value,
            "retrieval_strategy": self.retrieval_strategy.value,
            "llm_allowed": self.llm_allowed,
            "reason": self.reason,
        }


class QueryRouter:
    """
    Routes user queries to the cheapest reliable answering path.

    Rules are deterministic and ordered from cheapest to most expensive:
        1. UNKNOWN — empty or unsupported queries
        2. DIRECT_FACT — single field keyword, structured retrieval only
        3. EXACT_LOOKUP — exact identifier match
        4. STRUCTURED_LOOKUP — field + question word combination
        5. SYNTHESIS — reasoning/synthesis keywords present
        6. MULTI_EVIDENCE — comparison keywords present
        7. SEMANTIC_LOOKUP — everything else (default)
    """

    def __init__(self, analyzer: Optional[QueryAnalyzer] = None):
        self.analyzer = analyzer or QueryAnalyzer()

    def route(self, query: str) -> QueryRoute:
        """
        Determine the best route for a given query.
        """
        if not query or not query.strip():
            return QueryRoute(
                query_type=QueryType.UNKNOWN,
                retrieval_strategy=RetrievalStrategy.NONE,
                llm_allowed=False,
                reason="Empty query",
            )

        analysis = self.analyzer.analyze(query)

        # --- Rule 1: UNKNOWN ---
        # If the query is too short to be meaningful
        if analysis.token_count == 0:
            return QueryRoute(
                query_type=QueryType.UNKNOWN,
                retrieval_strategy=RetrievalStrategy.NONE,
                llm_allowed=False,
                reason="Query has no meaningful tokens",
                analysis=analysis,
            )

        # --- Rule 2: SYNTHESIS (most expensive, check early) ---
        if analysis.has_synthesis_keywords:
            return QueryRoute(
                query_type=QueryType.SYNTHESIS,
                retrieval_strategy=RetrievalStrategy.MULTI_EVIDENCE,
                llm_allowed=True,
                reason="Query contains synthesis/reasoning keywords",
                analysis=analysis,
            )

        # --- Rule 3: MULTI_EVIDENCE ---
        if analysis.has_comparison_keywords:
            return QueryRoute(
                query_type=QueryType.MULTI_EVIDENCE,
                retrieval_strategy=RetrievalStrategy.MULTI_EVIDENCE,
                llm_allowed=True,
                reason="Query contains comparison keywords",
                analysis=analysis,
            )

        # --- Rule 4: EXACT_LOOKUP ---
        # If the query is a single identifier (e.g., "LR-00501", "MH20GC-9895")
        if (
            analysis.identifiers
            and analysis.token_count <= 3
        ):
            return QueryRoute(
                query_type=QueryType.EXACT_LOOKUP,
                retrieval_strategy=RetrievalStrategy.EXACT,
                llm_allowed=False,
                reason="Query contains an exact identifier to look up",
                analysis=analysis,
            )

        # --- Rule 5: STRUCTURED_LOOKUP ---
        # Field + identifier/document reference combo
        # e.g., "What is the vehicle number for LR-00501?"
        # Checked BEFORE DIRECT_FACT because a query with both a field and
        # an identifier is more specific and needs hybrid retrieval.
        if (
            analysis.possible_fields
            and analysis.identifiers
            and analysis.token_count <= 15
        ):
            return QueryRoute(
                query_type=QueryType.STRUCTURED_LOOKUP,
                retrieval_strategy=RetrievalStrategy.HYBRID,
                llm_allowed=False,
                reason="Field + identifier query, hybrid retrieval appropriate",
                analysis=analysis,
            )

        # --- Rule 6: DIRECT_FACT ---
        # If the query is a short question about a single field
        # e.g., "What is the invoice number?", "vehicle number", "invoice number"
        if (
            analysis.possible_fields
            and analysis.token_count <= 8
            and analysis.question_type in ("what", "which", "declarative", "direct", "is", "are", "does", "do", "tell", "show", "find", "list")
        ):
            return QueryRoute(
                query_type=QueryType.DIRECT_FACT,
                retrieval_strategy=RetrievalStrategy.STRUCTURED,
                llm_allowed=False,
                reason="Likely direct fact lookup",
                analysis=analysis,
            )

        # --- Rule 7: SEMANTIC_LOOKUP (default for everything else) ---
        return QueryRoute(
            query_type=QueryType.SEMANTIC_LOOKUP,
            retrieval_strategy=RetrievalStrategy.HYBRID,
            llm_allowed=False,
            reason="General semantic query, hybrid retrieval",
            analysis=analysis,
        )


def route_query(query: str) -> QueryRoute:
    """Convenience function."""
    return QueryRouter().route(query)