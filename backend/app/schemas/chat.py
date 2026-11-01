"""Pydantic schemas for the RAG Chat API."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

MAX_CONVERSATION_TURNS: int = 8
MAX_TOTAL_HISTORY_CHARS: int = 4000
MAX_TURN_CONTENT_CHARS: int = 1000


class ChatTurn(BaseModel):
    """Single turn in the conversation history."""
    role: Literal["user", "assistant", "agent"] = Field(
        ...,
        description="Role of the speaker: 'user', 'assistant', or 'agent'."
    )
    content: str = Field(
        ...,
        max_length=MAX_TURN_CONTENT_CHARS,
        description="Text content of the conversation turn."
    )


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
    conversation_history: Optional[List[ChatTurn]] = Field(
        default_factory=list,
        description="Recent conversation turns for multi-turn context (capped server-side)."
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional server-side session identifier for persistent conversation memory."
    )

    @field_validator("conversation_history", mode="before")
    @classmethod
    def sanitize_and_cap_history(cls, v):
        if not v:
            return []

        # 1. Cap to last MAX_CONVERSATION_TURNS
        turns = v[-MAX_CONVERSATION_TURNS:]

        # 2. Normalize and truncate each turn's content
        sanitized = []
        for turn in turns:
            if isinstance(turn, dict):
                role = turn.get("role")
                content = str(turn.get("content", ""))[:MAX_TURN_CONTENT_CHARS]
                sanitized.append({"role": role, "content": content})
            elif isinstance(turn, ChatTurn):
                sanitized.append({"role": turn.role, "content": turn.content[:MAX_TURN_CONTENT_CHARS]})
            else:
                sanitized.append(turn)

        # 3. Cap total character length across turns, keeping the most recent turns
        total_chars = sum(len(t["content"] if isinstance(t, dict) else t.content) for t in sanitized)
        while sanitized and total_chars > MAX_TOTAL_HISTORY_CHARS:
            removed = sanitized.pop(0)
            total_chars -= len(removed["content"] if isinstance(removed, dict) else removed.content)

        return sanitized


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

