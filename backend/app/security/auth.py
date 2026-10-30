"""Security authentication utilities and admin guards."""

from fastapi import Header, HTTPException, status
from backend.app.config import get_settings


def verify_admin_key(x_admin_key: str = Header(None, alias="X-Admin-Key")) -> str:
    """
    Enforce administrative authentication for document upload/delete operations.
    Raises HTTP 401 Unauthorized if missing or invalid.
    """
    settings = get_settings()
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing administrative authentication header (X-Admin-Key).",
        )
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid administrative credentials. Document management is restricted.",
        )
    return x_admin_key

