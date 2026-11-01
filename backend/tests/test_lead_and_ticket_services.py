"""Tests for LeadService and TicketService: scoring, tracking, safety guardrails, and life cycle."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import Base
from backend.app.services.customer_service import CustomerService
from backend.app.services.lead_service import LeadService
from backend.app.services.ticket_service import TicketService


@pytest.fixture
def test_env():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    lead_svc = LeadService(session_factory=TestingSession)
    ticket_svc = TicketService(session_factory=TestingSession)
    cust_svc = CustomerService(session_factory=TestingSession)

    yield lead_svc, ticket_svc, cust_svc

    Base.metadata.drop_all(bind=engine)


def test_lead_priority_scoring_bulk(test_env):
    lead_svc, _, _ = test_env

    # 15 units of 315kW Motor -> URGENT priority and high score
    priority, score = lead_svc.calculate_priority_and_score(
        product_interest="315kW IE3 Premium Efficiency Motor",
        required_quantity=15,
        company="National Cement Corp",
    )
    assert priority == "URGENT"
    assert score >= 85


def test_lead_creation_and_status_update(test_env):
    lead_svc, _, cust_svc = test_env

    cust = cust_svc.get_or_create_customer(email="purchase@powergen.in", company="PowerGen")
    lead = lead_svc.create_lead(
        product_interest="2000kVA Transformer",
        customer_id=cust.id,
        required_quantity=2,
        location="Bengaluru",
    )

    assert lead.id is not None
    assert lead.product_interest == "2000kVA Transformer"
    assert lead.status == "NEW"

    updated = lead_svc.update_lead_status(lead.id, "QUALIFIED")
    assert updated.status == "QUALIFIED"

    leads_list = lead_svc.list_leads(status="QUALIFIED")
    assert len(leads_list) == 1
    assert leads_list[0].id == lead.id


def test_ticket_safety_guardrail_on_fire_hazard(test_env):
    _, ticket_svc, _ = test_env

    ticket, advisory = ticket_svc.create_ticket(
        product_category="Switchgear Panels",
        issue_description="Main breaker is smoking and sparking under load!",
    )

    assert ticket.id.startswith("TK-")
    assert ticket.severity == "CRITICAL"
    assert advisory is not None
    assert "CRITICAL SAFETY ADVISORY" in advisory
    assert "Do not attempt uncertified DIY maintenance" in advisory


def test_ticket_resolution_flow(test_env):
    _, ticket_svc, _ = test_env

    ticket, _ = ticket_svc.create_ticket(
        product_category="Motors",
        issue_description="Minor grease leakage around drive-end bearing cover.",
    )
    assert ticket.severity == "MEDIUM"
    assert ticket.status == "OPEN"
    assert ticket.resolved_at is None

    resolved = ticket_svc.resolve_ticket(ticket.id)
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None

