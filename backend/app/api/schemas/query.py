"""
Pydantic schemas for query and answer API endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request for the /queries/answer endpoint."""

    query: str = Field(..., min_length=1, description="The user's question")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of evidence items")


class QueryEvidence(BaseModel):
    """A single piece of evidence supporting the answer."""

    document_id: str = ""
    document_name: str = ""
    page_number: Optional[int] = None
    text: str = ""
    field: Optional[str] = None
    value: Optional[str] = None
    score: float = 0.0
    source_type: str = ""


class QueryUsage(BaseModel):
    """Token usage and estimated cost for a query."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    retrieval_cost: float = 0.0


class QueryResponse(BaseModel):
    """Standard response for the /queries/answer endpoint."""

    answer: str
    method: str
    confidence: float
    llm_used: bool
    cache_hit: bool = False
    query: str
    evidence: List[QueryEvidence] = Field(default_factory=list)
    usage: QueryUsage = Field(default_factory=QueryUsage)
