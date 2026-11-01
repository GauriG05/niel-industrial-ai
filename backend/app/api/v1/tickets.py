"""Support tickets management API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.security.auth import verify_admin_key
from backend.app.services.ticket_service import get_ticket_service

router = APIRouter(prefix="/tickets", tags=["Support Tickets"])


@router.get("", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_admin_key)])
def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    limit: int = Query(50, ge=1, le=200),
):
    """List support tickets with optional filtering (Admin only)."""
    ticket_svc = get_ticket_service()
    tickets = ticket_svc.list_tickets(status=status, severity=severity, limit=limit)
    return [
        {
            "id": t.id,
            "customer_id": t.customer_id,
            "session_id": t.session_id,
            "product_category": t.product_category,
            "issue_description": t.issue_description,
            "severity": t.severity,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        }
        for t in tickets
    ]


@router.get("/{ticket_id}", response_model=Dict[str, Any], dependencies=[Depends(verify_admin_key)])
def get_ticket(ticket_id: str):
    """Get single support ticket details."""
    ticket_svc = get_ticket_service()
    ticket = ticket_svc.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    return {
        "id": ticket.id,
        "customer_id": ticket.customer_id,
        "session_id": ticket.session_id,
        "product_category": ticket.product_category,
        "issue_description": ticket.issue_description,
        "severity": ticket.severity,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
    }


@router.post("/{ticket_id}/resolve", response_model=Dict[str, Any], dependencies=[Depends(verify_admin_key)])
def resolve_ticket(ticket_id: str):
    """Mark a ticket as resolved (Admin only)."""
    ticket_svc = get_ticket_service()
    resolved = ticket_svc.resolve_ticket(ticket_id)
    if not resolved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    return {
        "id": resolved.id,
        "status": resolved.status,
        "resolved_at": resolved.resolved_at.isoformat() if resolved.resolved_at else None,
    }

