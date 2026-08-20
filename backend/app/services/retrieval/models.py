"""
Generic retrieval result models for the Cost-Aware Knowledge Engine.

Every retrieval result carries full provenance metadata so the answer layer
can trace exactly where each piece of evidence came from.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class RetrievalResult:
    """A single piece of evidence returned by the retrieval layer."""

    source_type: str  # "fact" | "chunk"
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    chunk_id: Optional[str] = None
    fact_id: Optional[str] = None
    text: str = ""
    field: Optional[str] = None
    value: Optional[str] = None
    score: float = 0.0
    retrieval_method: str = ""  # "structured" | "lexical" | "semantic" | "hybrid"
    # Provenance metadata
    section: Optional[str] = None
    copy_type: Optional[str] = None
    chunking_strategy: Optional[str] = None
    source_checksum: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RetrievalResponse:
    """The full response from a retrieval request."""

    query: str
    top_k: int
    results: list[RetrievalResult] = field(default_factory=list)
    total_results: int = 0

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "top_k": self.top_k,
            "total_results": self.total_results,
            "results": [r.to_dict() for r in self.results],
        }