"""Tests for dashboard REST endpoints: Customers, Leads, and Tickets."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import get_settings
from backend.app.services.customer_service import get_customer_service
from backend.app.services.lead_service import get_lead_service
from backend.app.services.ticket_service import get_ticket_service

client = TestClient(app)
settings = get_settings()
ADMIN_HEADERS = {"X-Admin-Key": settings.ADMIN_API_KEY}


def test_unauthorized_access_rejected():
    """Verify that dashboard endpoints reject requests missing the admin key."""
    assert client.get("/api/v1/customers").status_code == 401
    assert client.get("/api/v1/leads").status_code == 401
    assert client.get("/api/v1/tickets").status_code == 401


def test_customer_endpoints():
    cust_svc = get_customer_service()
    cust = cust_svc.get_or_create_customer(
        name="Dashboard Test Customer",
        email="dash.cust@factory.in",
        company="Factory India",
    )

    # List customers
    resp = client.get("/api/v1/customers", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["customer_id"] == cust.id for c in data)

    # Get single customer context
    resp_single = client.get(f"/api/v1/customers/{cust.id}", headers=ADMIN_HEADERS)
    assert resp_single.status_code == 200
    assert resp_single.json()["name"] == "Dashboard Test Customer"

    # Record consent
    resp_consent = client.post(f"/api/v1/customers/{cust.id}/consent")
    assert resp_consent.status_code == 200
    assert resp_consent.json()["status"] == "success"


def test_lead_endpoints():
    lead_svc = get_lead_service()
    lead = lead_svc.create_lead(
        product_interest="11kV Substation Switchgear",
        requirement_details="Outdoor containerized unit",
        required_quantity=1,
    )

    # List leads
    resp = client.get("/api/v1/leads", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert any(l["id"] == lead.id for l in data)

    # Update lead status
    patch_resp = client.patch(
        f"/api/v1/leads/{lead.id}/status",
        json={"status": "QUALIFIED"},
        headers=ADMIN_HEADERS,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "QUALIFIED"


def test_ticket_endpoints():
    ticket_svc = get_ticket_service()
    ticket, _ = ticket_svc.create_ticket(
        product_category="Motors",
        issue_description="Vibration at 1500 RPM on fan end",
    )

    # List tickets
    resp = client.get("/api/v1/tickets", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert any(t["id"] == ticket.id for t in data)

    # Resolve ticket
    resolve_resp = client.post(
        f"/api/v1/tickets/{ticket.id}/resolve",
        headers=ADMIN_HEADERS,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "RESOLVED"
