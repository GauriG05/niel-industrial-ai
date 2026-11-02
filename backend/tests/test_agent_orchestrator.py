"""Integration and unit tests for ToolDispatcher and AgentOrchestrator."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.agent.tools import ToolDispatcher
from backend.app.db.models import Base
from backend.app.services.customer_service import CustomerService
from backend.app.services.intent_service import IntentService
from backend.app.services.lead_service import LeadService
from backend.app.services.rag_service import get_rag_service
from backend.app.services.session_service import SessionService
from backend.app.services.ticket_service import TicketService


@pytest.fixture
def agent_system():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session_svc = SessionService(session_factory=TestingSession)
    cust_svc = CustomerService(session_factory=TestingSession)
    lead_svc = LeadService(session_factory=TestingSession)
    ticket_svc = TicketService(session_factory=TestingSession)
    intent_svc = IntentService()
    rag_svc = get_rag_service()

    dispatcher = ToolDispatcher()
    dispatcher.session_service = session_svc
    dispatcher.customer_service = cust_svc
    dispatcher.lead_service = lead_svc
    dispatcher.ticket_service = ticket_svc
    dispatcher.rag_service = rag_svc

    orchestrator = AgentOrchestrator(
        intent_service=intent_svc,
        tool_dispatcher=dispatcher,
        rag_service=rag_svc,
        session_service=session_svc,
        customer_service=cust_svc,
    )

    yield orchestrator, dispatcher, session_svc, cust_svc, TestingSession

    Base.metadata.drop_all(bind=engine)


def test_tool_dispatcher_customer_profile_flow(agent_system):
    _, dispatcher, session_svc, cust_svc, _ = agent_system

    session_id = session_svc.create_session()

    # Save customer info
    save_res = dispatcher.execute_tool(
        name="save_customer_information",
        arguments={
            "name": "Kavita Rao",
            "email": "kavita@powergrid.in",
            "company": "PowerGrid Solutions",
            "interests": ["Switchgear", "Transformers"],
            "preferences": {"voltage": "11kV"},
        },
        session_id=session_id,
    )
    assert save_res["status"] == "success"
    cid = save_res["customer_id"]

    # Retrieve profile
    prof_res = dispatcher.execute_tool(
        name="get_customer_profile",
        arguments={"customer_id": cid},
    )
    assert prof_res["status"] == "success"
    profile = prof_res["profile"]
    assert profile["name"] == "Kavita Rao"
    assert "Switchgear" in profile["interests"]
    assert profile["has_consented"] is True


def test_orchestrator_handles_safety_hazard(agent_system):
    orchestrator, _, session_svc, _, _ = agent_system
    session_id = session_svc.create_session()

    query = "The 75kW motor is smoking and emitting sparks from the terminal box!"
    response = orchestrator.handle_request(
        question=query,
        session_id=session_id,
    )

    assert response.escalated is True
    assert response.ticket_id is not None
    assert response.ticket_id.startswith("TK-")
    assert "CRITICAL SAFETY WARNING" in response.answer
    assert "isolate power" in response.answer.lower()
    assert session_svc.is_human_active(session_id) is True


def test_orchestrator_handles_complaint_and_ticket(agent_system):
    orchestrator, _, session_svc, _, _ = agent_system
    session_id = session_svc.create_session()

    query = "Our 2000kVA transformer has a broken oil gasket and is leaking oil severely."
    response = orchestrator.handle_request(
        question=query,
        session_id=session_id,
    )

    assert response.ticket_id is not None
    assert response.ticket_id.startswith("TK-")
    assert response.ticket_id in response.answer
    assert "registered with NIEL Customer Service" in response.answer


def test_orchestrator_handles_quotation_and_lead(agent_system):
    orchestrator, _, session_svc, _, _ = agent_system
    session_id = session_svc.create_session()

    query = "Please send a quotation for 5 units of 75kW IE3 motors."
    response = orchestrator.handle_request(
        question=query,
        session_id=session_id,
    )

    assert response.lead_id is not None
    assert response.intent in ("QUOTATION_REQUEST", "SALES_ENQUIRY")
    assert "Sales Lead #" in response.answer


def test_orchestrator_handles_connect_to_human_with_context(agent_system):
    orchestrator, _, session_svc, _, _ = agent_system
    session_id = session_svc.create_session()

    # Step 1: User asks about a 11kV distribution transformer
    session_svc.add_message(session_id, "user", "What are the specs of your 11kV distribution transformers?")
    session_svc.add_message(session_id, "assistant", "NIEL offers 11kV distribution transformers up to 2500 kVA.")

    # Step 2: User requests human connection
    query = "please connect me to human"
    response = orchestrator.handle_request(
        question=query,
        session_id=session_id,
    )

    assert response.escalated is True
    assert response.whatsapp_url is not None
    assert "wa.me/919741307999" in response.whatsapp_url
    assert "wa.me/919741307999" in response.answer
    # Context should be included in WhatsApp url
    assert "transformer" in response.whatsapp_url.lower() or "11kv" in response.whatsapp_url.lower()


def test_orchestrator_handles_connect_to_sales_person(agent_system):
    orchestrator, _, session_svc, _, _ = agent_system
    session_id = session_svc.create_session()

    query = "please connect me to sales person"
    response = orchestrator.handle_request(
        question=query,
        session_id=session_id,
    )

    assert response.escalated is True
    assert response.lead_id is not None
    assert response.whatsapp_url is not None
    assert "wa.me/919741307999" in response.whatsapp_url
    assert "sales" in response.answer.lower()


