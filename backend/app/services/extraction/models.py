"""
Response models for the answer extraction layer.

Contains the AnswerResponse dataclass that carries full provenance
and routing information alongside the extracted answer.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class EvidenceInfo:
    """A single piece of evidence used to support an answer."""

    source_type: str  # "fact" | "chunk"
    retrieval_method: str  # "structured" | "lexical" | "semantic" | "hybrid"
    document_name: str
    page_number: Optional[int] = None
    field: Optional[str] = None
    value: Optional[str] = None
    text: str = ""
    score: float = 0.0
    section: Optional[str] = None
    copy_type: Optional[str] = None
    chunking_strategy: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProvenanceInfo:
    """Provenance metadata describing how the answer was determined."""

    extraction_priority: str  # which priority level was used
    total_evidence: int = 0
    supporting_evidence: int = 0
    conflicting_evidence: int = 0
    best_score: float = 0.0
    evidence_agreement: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AnswerResponse:
    """
    The full response from the answer extraction pipeline.

    Contains the final answer along with method, confidence,
    provenance, and routing metadata.
    """

    answer: str
    method: str
    # "structured_fact" | "exact_match" | "lexical_match"
    # | "hybrid_match" | "unknown"
    confidence: float
    llm_used: bool
    evidence: list[EvidenceInfo]
    query: str
    normalized_query: str
    query_type: str
    retrieval_strategy: str
    llm_allowed: bool
    provenance: ProvenanceInfo

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "method": self.method,
            "confidence": self.confidence,
            "llm_used": self.llm_used,
            "evidence": [e.to_dict() for e in self.evidence],
            "query": self.query,
            "normalized_query": self.normalized_query,
            "query_type": self.query_type,
            "retrieval_strategy": self.retrieval_strategy,
            "llm_allowed": self.llm_allowed,
            "provenance": self.provenance.to_dict(),
        }