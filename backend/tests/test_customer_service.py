"""Tests for CustomerService: profile persistence, consent, memory context, and session linking."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import Base, Customer, ChatSession, SalesLead, SupportTicket
from backend.app.services.customer_service import CustomerService
from backend.app.services.session_service import SessionService


@pytest.fixture
def isolated_services():
    """Create in-memory database and wired service instances."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    customer_svc = CustomerService(session_factory=TestingSession)
    session_svc = SessionService(session_factory=TestingSession)

    yield customer_svc, session_svc, TestingSession

    Base.metadata.drop_all(bind=engine)


def test_get_or_create_customer(isolated_services):
    customer_svc, _, _ = isolated_services

    # Create new customer
    cust1 = customer_svc.get_or_create_customer(
        email="rajesh@steelworks.com",
        name="Rajesh Patel",
        company="SteelWorks India",
    )
    assert cust1.id.startswith("cust-")
    assert cust1.email == "rajesh@steelworks.com"
    assert cust1.company == "SteelWorks India"

    # Lookup existing customer by email
    cust2 = customer_svc.get_or_create_customer(
        email="rajesh@steelworks.com",
        phone="+91-9988776655",
    )
    assert cust2.id == cust1.id
    assert cust2.phone == "+91-9988776655"


def test_update_profile_and_interests(isolated_services):
    customer_svc, _, _ = isolated_services

    cust = customer_svc.get_or_create_customer(
        name="Deepa Roy",
        email="deepa@cementpower.com",
    )

    # Initial update of interests and preferences
    updated = customer_svc.update_customer_profile(
        customer_id=cust.id,
        company="Cement Power Ltd",
        industry="Cement",
        interests=["Motors", "Switchgear"],
        preferences={"voltage": "415V", "preferred_channel": "email"},
    )
    assert updated.company == "Cement Power Ltd"
    assert "Motors" in updated.interests_json
    assert "Switchgear" in updated.interests_json

    # Second update: append interest with duplicate case insensitivity and add preference
    updated2 = customer_svc.update_customer_profile(
        customer_id=cust.id,
        interests=["motors", "Transformers"],
        preferences={"frame_size": "315M"},
    )
    import json
    interests = json.loads(updated2.interests_json)
    # Motors should only appear once (original casing preserved)
    assert len([i for i in interests if i.lower() == "motors"]) == 1
    assert "Transformers" in interests

    prefs = json.loads(updated2.preferences_json)
    assert prefs["voltage"] == "415V"
    assert prefs["frame_size"] == "315M"


def test_record_consent(isolated_services):
    customer_svc, _, _ = isolated_services

    cust = customer_svc.get_or_create_customer(email="consent.test@domain.com")
    assert cust.consented_at is None

    consented = customer_svc.record_consent(customer_id=cust.id)
    assert consented.consented_at is not None


def test_get_customer_context_with_leads_and_tickets(isolated_services):
    customer_svc, session_svc, TestingSession = isolated_services

    cust = customer_svc.get_or_create_customer(
        name="Anil Nair",
        email="anil@nairinfra.in",
        company="Nair Infrastructure",
    )
    customer_svc.update_customer_profile(
        customer_id=cust.id,
        interests=["Transformers", "Pumps"],
        preferences={"rating": "500kVA"},
    )
    customer_svc.record_consent(customer_id=cust.id)

    # Create session, lead, and ticket
    session_id = session_svc.create_session(customer_id=cust.id)

    with TestingSession() as db:
        lead = SalesLead(
            customer_id=cust.id,
            session_id=session_id,
            product_interest="500kVA Oil Cooled Transformer",
            status="QUALIFIED",
            priority="HIGH",
        )
        ticket = SupportTicket(
            id="TK-2026-9901",
            customer_id=cust.id,
            session_id=session_id,
            product_category="Transformers",
            issue_description="Oil leakage from drain valve",
            severity="MEDIUM",
            status="OPEN",
        )
        db.add_all([lead, ticket])
        db.commit()

    # Get structured context
    context = customer_svc.get_customer_context(customer_id=cust.id)
    assert context is not None
    assert context["customer_id"] == cust.id
    assert context["name"] == "Anil Nair"
    assert context["company"] == "Nair Infrastructure"
    assert context["has_consented"] is True
    assert "Transformers" in context["interests"]
    assert context["open_tickets_count"] == 1
    assert len(context["recent_tickets"]) == 1
    assert context["recent_tickets"][0]["id"] == "TK-2026-9901"
    assert len(context["recent_leads"]) == 1
    assert context["recent_leads"][0]["product_interest"] == "500kVA Oil Cooled Transformer"


def test_delete_customer_data_gdpr(isolated_services):
    customer_svc, session_svc, TestingSession = isolated_services

    cust = customer_svc.get_or_create_customer(email="delete.me@privacy.com")
    session_id = session_svc.create_session(customer_id=cust.id)

    # Session currently points to cust.id
    assert session_svc.get_session_customer_id(session_id) == cust.id

    # Execute right-to-be-forgotten deletion
    success = customer_svc.delete_customer_data(customer_id=cust.id)
    assert success is True

    # Customer record should be gone
    with TestingSession() as db:
        assert db.query(Customer).filter_by(id=cust.id).first() is None
        # Session record remains but customer_id is nullified
        session = db.query(ChatSession).filter_by(id=session_id).first()
        assert session is not None
        assert session.customer_id is None

