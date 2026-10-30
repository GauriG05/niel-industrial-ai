"""Common API response schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check payload."""
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    kill_switch_active: bool = Field(default=False)


class ErrorResponse(BaseModel):
    """Standardized error format."""
    detail: str = Field(..., description="Human-readable error explanation")
    error_code: Optional[str] = Field(default=None, description="Categorized machine error code")
