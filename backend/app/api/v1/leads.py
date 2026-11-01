"""Sales leads management API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.security.auth import verify_admin_key
from backend.app.services.lead_service import get_lead_service

router = APIRouter(prefix="/leads", tags=["Sales Leads"])


class UpdateLeadStatusRequest(BaseModel):
    status: str = Field(..., description="Lead status: NEW, QUALIFIED, CONTACTED, CLOSED")


@router.get("", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_admin_key)])
def list_leads(
    status: Optional[str] = Query(None, description="Filter by status (NEW, QUALIFIED, CONTACTED, CLOSED)"),
    priority: Optional[str] = Query(None, description="Filter by priority (URGENT, HIGH, MEDIUM, LOW)"),
    limit: int = Query(50, ge=1, le=200),
):
    """List commercial sales leads with optional filtering (Admin only)."""
    lead_svc = get_lead_service()
    leads = lead_svc.list_leads(status=status, priority=priority, limit=limit)
    return [
        {
            "id": l.id,
            "customer_id": l.customer_id,
            "session_id": l.session_id,
            "product_interest": l.product_interest,
            "requirement_details": l.requirement_details,
            "required_quantity": l.required_quantity,
            "location": l.location,
            "status": l.status,
            "priority": l.priority,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leads
    ]


@router.get("/{lead_id}", response_model=Dict[str, Any], dependencies=[Depends(verify_admin_key)])
def get_lead(lead_id: int):
    """Get single sales lead details."""
    lead_svc = get_lead_service()
    lead = lead_svc.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales lead not found")
    return {
        "id": lead.id,
        "customer_id": lead.customer_id,
        "session_id": lead.session_id,
        "product_interest": lead.product_interest,
        "requirement_details": lead.requirement_details,
        "required_quantity": lead.required_quantity,
        "location": lead.location,
        "status": lead.status,
        "priority": lead.priority,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }


@router.patch("/{lead_id}/status", response_model=Dict[str, Any], dependencies=[Depends(verify_admin_key)])
def update_lead_status(lead_id: int, payload: UpdateLeadStatusRequest):
    """Update sales lead qualification status."""
    lead_svc = get_lead_service()
    updated = lead_svc.update_lead_status(lead_id, payload.status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales lead not found")
    return {
        "id": updated.id,
        "status": updated.status,
        "priority": updated.priority,
    }

