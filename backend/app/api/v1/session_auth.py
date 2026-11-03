"""Session token issuance endpoint for secure WebSocket and API communication."""

import time
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.security.tokens import create_session_token
from backend.app.services.session_service import get_session_service

router = APIRouter(prefix="/sessions", tags=["Session Authentication"])


class SessionTokenRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None,
        description="Existing session identifier. If omitted, a new secure session is created.",
    )
    customer_id: Optional[str] = Field(
        default=None,
        description="Optional customer ID to associate with this session.",
    )


class SessionTokenResponse(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    token: str = Field(..., description="Short-lived HMAC-SHA256 signed session token")
    expires_at: int = Field(..., description="Unix timestamp when token expires")
    token_type: str = Field(default="Bearer", description="Token authentication scheme")


@router.post("/token", response_model=SessionTokenResponse)
def get_session_token(request: SessionTokenRequest):
    """
    Issue a secure, short-lived signed session token.
    Clients use this token to authenticate WebSocket connections and prove
    ownership of the session, preventing session hijacking or unauthorized eavesdropping.
    """
    settings = get_settings()
    session_service = get_session_service()

    # 1. Resolve or create session
    sid = request.session_id.strip() if request.session_id else str(uuid.uuid4())
    session_service.get_or_create(sid, customer_id=request.customer_id)

    # 2. Issue signed token
    token = create_session_token(
        session_id=sid,
        customer_id=request.customer_id,
        ttl_seconds=settings.SESSION_TOKEN_EXPIRE_SECONDS,
    )
    expires_at = int(time.time()) + settings.SESSION_TOKEN_EXPIRE_SECONDS

    return SessionTokenResponse(
        session_id=sid,
        token=token,
        expires_at=expires_at,
        token_type="Bearer",
    )

