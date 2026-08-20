"""
Retrieval services for the Cost-Aware Knowledge Engine.

Provides hybrid retrieval combining structured facts, lexical chunk search,
and semantic vector search.
"""

from app.services.retrieval.hybrid_retriever import (
    HybridWeights,
    get_default_weights,
    retrieve,
)
from app.services.retrieval.lexical_retriever import retrieve_lexical_chunks
from app.services.retrieval.models import RetrievalResponse, RetrievalResult
from app.services.retrieval.semantic_retriever import retrieve_semantic_chunks
from app.services.retrieval.structured_retriever import retrieve_structured_facts

__all__ = [
    "retrieve",
    "retrieve_structured_facts",
    "retrieve_lexical_chunks",
    "retrieve_semantic_chunks",
    "HybridWeights",
    "get_default_weights",
    "RetrievalResponse",
    "RetrievalResult",
]