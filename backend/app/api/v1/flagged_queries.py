"""Administrative API endpoints for reviewing and resolving flagged queries touching unverified specs."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from backend.app.security.auth import verify_admin_key
from backend.app.services.flag_service import get_flag_service

router = APIRouter(prefix="/flagged-queries", tags=["Engineering Review"])


class FlaggedQueryOut(BaseModel):
    id: int
    timestamp: str
    user_question: str
    product_category: str
    unverified_field: str
    session_id: Optional[str] = None
    resolved: bool

    model_config = ConfigDict(from_attributes=True)


class FlaggedQueriesListResponse(BaseModel):
    total: int
    flagged_queries: List[FlaggedQueryOut]


class ResolveFlaggedQueryRequest(BaseModel):
    resolved: bool = Field(default=True, description="Mark whether this unverified spec query has been resolved")


@router.get("", response_model=FlaggedQueriesListResponse)
def list_flagged_queries(
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_key: str = Depends(verify_admin_key),
):
    """
    Retrieve flagged user queries touching unverified product specifications.
    Restricted to engineering administration via X-Admin-Key header.
    """
    service = get_flag_service()
    entries = service.list_flagged_queries(resolved=resolved, limit=limit, offset=offset)
    out = [
        FlaggedQueryOut(
            id=e.id,
            timestamp=e.timestamp.isoformat(),
            user_question=e.user_question,
            product_category=e.product_category,
            unverified_field=e.unverified_field,
            session_id=e.session_id,
            resolved=e.resolved,
        )
        for e in entries
    ]
    return FlaggedQueriesListResponse(total=len(out), flagged_queries=out)


@router.patch("/{query_id}", response_model=FlaggedQueryOut)
def update_flagged_query_resolution(
    query_id: int,
    payload: ResolveFlaggedQueryRequest,
    admin_key: str = Depends(verify_admin_key),
):
    """
    Update the resolution status of a flagged query entry.
    Restricted to engineering administration via X-Admin-Key header.
    """
    service = get_flag_service()
    updated = service.resolve_flagged_query(flag_id=query_id, resolved=payload.resolved)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flagged query with ID {query_id} not found.",
        )
    return FlaggedQueryOut(
        id=updated.id,
        timestamp=updated.timestamp.isoformat(),
        user_question=updated.user_question,
        product_category=updated.product_category,
        unverified_field=updated.unverified_field,
        session_id=updated.session_id,
        resolved=updated.resolved,
    )
