"""Tests for expanded database models: Customer, SalesLead, SupportTicket, and ChatSession linkage."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from backend.app.db.models import Base, ChatSession, ChatMessage, Customer, SalesLead, SupportTicket
from backend.app.db.session import run_migrations


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for test runs."""
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def test_customer_creation_and_fields(db_session):
    """Test creating and retrieving a customer record with consent and preferences."""
    customer = Customer(
        id="cust-101",
        name="Sunita Sharma",
        email="sunita@acmeind.com",
        phone="+91-9876543210",
        company="Acme Industries",
        industry="Cement & Minerals",
        interests_json='["motors", "switchgear"]',
        preferences_json='{"contact_method": "email", "voltage_system": "415V"}',
        consented_at=datetime.now(timezone.utc),
    )
    db_session.add(customer)
    db_session.commit()

    saved = db_session.query(Customer).filter_by(id="cust-101").first()
    assert saved is not None
    assert saved.name == "Sunita Sharma"
    assert saved.company == "Acme Industries"
    assert 'motors' in saved.interests_json
    assert saved.consented_at is not None
    assert saved.created_at is not None


def test_chat_session_linked_to_customer(db_session):
    """Test linking a chat session to a customer and accessing relationship."""
    customer = Customer(
        id="cust-202",
        name="Vikram Rao",
        email="vikram@steelcorp.in",
    )
    db_session.add(customer)
    db_session.commit()

    session = ChatSession(
        id="session-user-202",
        customer_id="cust-202",
    )
    db_session.add(session)
    db_session.commit()

    db_session.refresh(customer)
    assert len(customer.sessions) == 1
    assert customer.sessions[0].id == "session-user-202"
    assert session.customer.email == "vikram@steelcorp.in"


def test_sales_lead_creation_and_relationships(db_session):
    """Test creating a sales lead associated with a customer and chat session."""
    customer = Customer(id="cust-303", name="Ananya Patel", company="Gujarat Textiles")
    session = ChatSession(id="session-lead-303", customer_id="cust-303")
    db_session.add_all([customer, session])
    db_session.commit()

    lead = SalesLead(
        customer_id=customer.id,
        session_id=session.id,
        product_interest="IE3 Premium Efficiency 75kW Motor",
        requirement_details="4 units required for spinning unit upgrade, delivery in Ahmedabad.",
        required_quantity=4,
        location="Ahmedabad, Gujarat",
        status="QUALIFIED",
        priority="HIGH",
    )
    db_session.add(lead)
    db_session.commit()

    saved_lead = db_session.query(SalesLead).filter_by(id=lead.id).first()
    assert saved_lead is not None
    assert saved_lead.required_quantity == 4
    assert saved_lead.priority == "HIGH"
    assert saved_lead.customer.company == "Gujarat Textiles"
    assert saved_lead.session.id == "session-lead-303"


def test_support_ticket_creation_and_resolution(db_session):
    """Test creating and resolving a support ticket."""
    customer = Customer(id="cust-404", name="Ramesh Kumar", company="Modern Refineries")
    session = ChatSession(id="session-ticket-404", customer_id="cust-404")
    db_session.add_all([customer, session])
    db_session.commit()

    ticket = SupportTicket(
        id="TK-2026-0042",
        customer_id=customer.id,
        session_id=session.id,
        product_category="Transformers",
        issue_description="Oil temperature alarm triggering during peak shift on 2000kVA unit.",
        severity="HIGH",
        status="OPEN",
    )
    db_session.add(ticket)
    db_session.commit()

    saved_ticket = db_session.query(SupportTicket).filter_by(id="TK-2026-0042").first()
    assert saved_ticket is not None
    assert saved_ticket.product_category == "Transformers"
    assert saved_ticket.status == "OPEN"
    assert saved_ticket.resolved_at is None

    # Resolve ticket
    saved_ticket.status = "RESOLVED"
    saved_ticket.resolved_at = datetime.now(timezone.utc)
    db_session.commit()

    refreshed = db_session.query(SupportTicket).filter_by(id="TK-2026-0042").first()
    assert refreshed.status == "RESOLVED"
    assert refreshed.resolved_at is not None


def test_schema_migration_adds_customer_id():
    """Verify that run_migrations idempotently alters existing chat_sessions table if customer_id is missing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # Create legacy table structure without customer_id
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE chat_sessions ("
                "id VARCHAR(64) PRIMARY KEY, "
                "created_at DATETIME, "
                "human_active BOOLEAN, "
                "escalated_at DATETIME"
                ")"
            )
        )
        conn.commit()

    # Verify customer_id is not yet present
    inspector = inspect(engine)
    cols = [col["name"] for col in inspector.get_columns("chat_sessions")]
    assert "customer_id" not in cols

    # Run migration
    run_migrations(engine)

    # Verify column added
    inspector_after = inspect(engine)
    cols_after = [col["name"] for col in inspector_after.get_columns("chat_sessions")]
    assert "customer_id" in cols_after

    # Second run should be idempotent and not raise error
    run_migrations(engine)

