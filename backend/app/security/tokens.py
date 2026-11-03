"""Cryptographic session token management for WebSocket and API authorization.

Uses HMAC-SHA256 with URL-safe base64 encoding to provide tamper-proof,
short-lived tokens bound to a specific session_id and optional customer_id.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from backend.app.config import get_settings


class TokenError(Exception):
    """Base exception for token errors."""
    pass


class TokenExpiredError(TokenError):
    """Raised when token has exceeded its expiration timestamp."""
    pass


class TokenInvalidError(TokenError):
    """Raised when signature or token format is invalid."""
    pass


def _b64url_encode(data: bytes) -> str:
    """Encode bytes to URL-safe base64 string without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    """Decode URL-safe base64 string with optional padding."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_session_token(
    session_id: str,
    customer_id: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
) -> str:
    """
    Generate an HMAC-SHA256 signed session token.

    :param session_id: Unique chat session UUID
    :param customer_id: Optional customer UUID bound to this session
    :param ttl_seconds: Time to live in seconds (defaults to settings.SESSION_TOKEN_EXPIRE_SECONDS)
    :return: URL-safe signed token string: '<b64_payload>.<b64_sig>'
    """
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.SESSION_TOKEN_EXPIRE_SECONDS
    now = int(time.time())

    payload = {
        "sid": session_id,
        "cid": customer_id,
        "iat": now,
        "exp": now + ttl,
    }

    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)

    secret = settings.SECRET_KEY.encode("utf-8")
    sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode an HMAC-SHA256 session token.

    :param token: The token string to verify
    :return: Decoded payload dictionary
    :raises TokenExpiredError: If the token has expired
    :raises TokenInvalidError: If the signature is invalid or token is malformed
    """
    if not token or not isinstance(token, str):
        raise TokenInvalidError("Session token cannot be empty.")

    parts = token.strip().split(".")
    if len(parts) != 2:
        raise TokenInvalidError("Malformed session token format.")

    payload_b64, sig_b64 = parts

    settings = get_settings()
    secret = settings.SECRET_KEY.encode("utf-8")

    # Verify signature in constant time
    expected_sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise TokenInvalidError("Session token signature verification failed.")

    # Decode payload
    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise TokenInvalidError(f"Failed to decode token payload: {exc}")

    # Check expiration
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or time.time() > exp:
        raise TokenExpiredError("Session token has expired. Please refresh your session.")

    return payload


def validate_session_token_for_session(token: str, expected_session_id: str) -> Dict[str, Any]:
    """
    Verify token and assert that it grants access to the specified session_id.

    :param token: The token string
    :param expected_session_id: Target session ID that the client wants to access
    :return: Decoded payload dictionary
    :raises TokenInvalidError: If session_id does not match
    """
    payload = verify_session_token(token)
    token_sid = payload.get("sid")
    if not token_sid or token_sid != expected_session_id:
        raise TokenInvalidError(
            f"Token authorization mismatch: Token is not valid for requested session."
        )
    return payload
