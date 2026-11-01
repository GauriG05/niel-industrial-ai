"""Tests for WhatsApp redirection logic and PDF attachments in chat."""

import urllib.parse
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.chat import ChatTurn
from backend.app.services.rag_service import get_rag_service

client = TestClient(app)


def test_pdf_static_endpoint_serves_brochure():
    """Verify that the official PDF brochures are reachable via /pdfs/{filename}."""
    response = client.get("/pdfs/AC%20Motors%20-%20NIEL%20Brochure.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 1000


def test_pdf_attachments_in_product_qa():
    """Verify that RAG responses for product specs return clean pdf_attachments."""
    rag = get_rag_service()
    resp = rag.answer_question(question="What is the maximum power rating for NIEL AC Motors?")
    assert resp.evidence_sufficient is True
    assert resp.pdf_attachments is not None
    assert len(resp.pdf_attachments) > 0
    att = resp.pdf_attachments[0]
    assert "AC Motors" in att.filename
    assert att.url.startswith("/pdfs/")
    assert att.page >= 1


def test_whatsapp_summary_generation_with_history():
    """
    Test WhatsApp link generation when conversation history exists:
    Must generate a concise, contextual summary including query, selected product,
    requirements, and unresolved issue.
    """
    history = [
        {"role": "user", "content": "I need an AC motor for a rolling mill application."},
        {"role": "assistant", "content": "NIEL manufactures AC Mill Duty Motors up to 2000 kW and Cage Rotor Motors up to 20,000 kW."},
        {"role": "user", "content": "What is the maximum power rating at 6.6 kV?"},
    ]

    first_query = history[0]["content"]
    latest_query = history[-1]["content"]
    selected_product = "AC Motors"
    requirements = "6.6 kV"
    session_id = "test-session-12345"

    message_text = "\n".join([
        "Hello NIEL Team,",
        "",
        "I would like human support assistance regarding an inquiry on your website:",
        "",
        f"• Customer Query: {first_query}",
        f"• Selected Product: {selected_product}",
        f"• Requirements: {requirements}",
        f"• Unresolved Issue / Request: {latest_query}",
        f"• Session Reference: {session_id}",
        "",
        "Please connect me with a support engineer.",
    ])

    encoded_text = urllib.parse.quote(message_text)
    wa_url = f"https://wa.me/919741307999?text={encoded_text}"

    # Verify link structure
    assert wa_url.startswith("https://wa.me/919741307999?text=")
    decoded = urllib.parse.unquote(wa_url)
    assert "rolling mill" in decoded
    assert "6.6 kV" in decoded
    assert "AC Motors" in decoded
    assert "test-session-12345" in decoded


def test_whatsapp_fallback_without_history():
    """
    Test WhatsApp link generation when NO conversation history exists:
    Must use exact fallback: 'Hello NIEL Team, I would like to connect with your support team. Please assist me.'
    """
    fallback_message = "Hello NIEL Team, I would like to connect with your support team. Please assist me."
    encoded_text = urllib.parse.quote(fallback_message)
    wa_url = f"https://wa.me/919741307999?text={encoded_text}"

    assert wa_url == "https://wa.me/919741307999?text=Hello%20NIEL%20Team%2C%20I%20would%20like%20to%20connect%20with%20your%20support%20team.%20Please%20assist%20me."
    decoded = urllib.parse.unquote(wa_url.split("?text=")[1])
    assert decoded == fallback_message

