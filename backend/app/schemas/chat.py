"""Pydantic schemas for the RAG Chat API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User question payload."""
    question: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="The user's query about NIEL products and specifications.",
        json_schema_extra={"example": "What power ratings are documented for NIEL motors?"}
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of context chunks to retrieve."
    )


class Citation(BaseModel):
    """Source reference verified against retrieved evidence."""
    source_filename: str = Field(..., description="Document filename")
    page_number: int = Field(..., description="Source page number (1-indexed)")
    chunk_id: str = Field(..., description="Unique chunk reference identifier")
    quote_snippet: Optional[str] = Field(default="", description="Explanatory excerpt or topic")


class UsageMetadata(BaseModel):
    """Token and estimated cost metrics for the request."""
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    estimated_cost_usd: float = Field(default=0.0)


class ChatResponse(BaseModel):
    """Structured response from NIEL Industrial Intelligence Assistant."""
    answer: str = Field(..., description="Grounded, factual answer or honest abstention")
    citations: List[Citation] = Field(default_factory=list, description="Verified source citations")
    evidence_sufficient: bool = Field(..., description="True if answer is backed by indexed evidence")
    clarification_needed: bool = Field(default=False, description="True if query is ambiguous")
    request_id: str = Field(..., description="Unique identifier for traceability")
    usage: Optional[UsageMetadata] = Field(default=None, description="Usage and cost tracking")

