"""Customer profile management API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.db.models import Customer
from backend.app.db.session import get_db
from backend.app.security.auth import verify_admin_key
from backend.app.services.customer_service import get_customer_service

router = APIRouter(prefix="/customers", tags=["Customers"])


class CustomerUpdateRequest(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    interests: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None


@router.get("", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_admin_key)])
def list_customers(
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    """List recent registered customers (Admin only)."""
    customers = db.query(Customer).order_by(Customer.created_at.desc()).limit(limit).all()
    cust_svc = get_customer_service()
    return [cust_svc.get_customer_context(c.id, db=db) for c in customers]


@router.get("/{customer_id}", response_model=Dict[str, Any], dependencies=[Depends(verify_admin_key)])
def get_customer(customer_id: str, db=Depends(get_db)):
    """Retrieve full customer profile and operational context."""
    cust_svc = get_customer_service()
    ctx = cust_svc.get_customer_context(customer_id, db=db)
    if not ctx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return ctx


@router.post("/{customer_id}/consent", response_model=Dict[str, Any])
def record_customer_consent(customer_id: str, db=Depends(get_db)):
    """Record customer privacy consent timestamp."""
    cust_svc = get_customer_service()
    customer = cust_svc.record_consent(customer_id, db=db)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {"status": "success", "customer_id": customer.id, "consented_at": customer.consented_at.isoformat()}


@router.delete("/{customer_id}", dependencies=[Depends(verify_admin_key)])
def delete_customer(customer_id: str, db=Depends(get_db)):
    """GDPR / Right-to-be-forgotten customer erasure."""
    cust_svc = get_customer_service()
    success = cust_svc.delete_customer_data(customer_id, db=db)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {"status": "deleted", "customer_id": customer_id}

