"""Security authentication utilities and admin guards."""

import hmac
from fastapi import Header, HTTPException, status
from backend.app.config import get_settings


def verify_admin_key(x_admin_key: str = Header(None, alias="X-Admin-Key")) -> str:
    """
    Enforce administrative authentication for sensitive admin and data operations.
    Uses constant-time comparison to prevent timing attacks.
    Raises HTTP 401 Unauthorized if missing, or HTTP 403 Forbidden if invalid.
    """
    settings = get_settings()
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing administrative authentication header (X-Admin-Key).",
        )

    # Constant-time comparison to prevent timing-attack vulnerability
    expected_key = settings.ADMIN_API_KEY.strip()
    provided_key = x_admin_key.strip()

    if not hmac.compare_digest(expected_key.encode("utf-8"), provided_key.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid administrative credentials. Access is restricted.",
        )

    return x_admin_key


