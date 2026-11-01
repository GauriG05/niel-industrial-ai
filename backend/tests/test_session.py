"""Integration and unit tests for SessionService and server-side conversation memory."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.session_service import get_session_service
from backend.app.services.rag_service import get_rag_service
from backend.app.retrieval.faiss_store import get_faiss_store
from backend.app.schemas.documents import DocumentSummary
from backend.app.ingestion.hasher import compute_sha256_bytes
from backend.app.ingestion.extractor import extract_pages_from_pdf
from backend.app.ingestion.chunker import process_document_to_chunks
from backend.app.services.openai_service import get_openai_service

client = TestClient(app)

SAMPLE_PDF_PATH = "data/docs/NIEL_Industrial_Motors_Catalogue_2026.pdf"


@pytest.fixture(scope="module", autouse=True)
def setup_test_index():
    """Ensure the sample NIEL catalogue is indexed for QA tests."""
    with open(SAMPLE_PDF_PATH, "rb") as f:
        content = f.read()

    doc_id = compute_sha256_bytes(content)
    pages = extract_pages_from_pdf(content)
    chunks = process_document_to_chunks(
        pages,
        doc_id,
        "NIEL_Industrial_Motors_Catalogue_2026.pdf",
        chunk_size=500,
        chunk_overlap=100,
    )

    openai_service = get_openai_service()
    embeddings = openai_service.get_embeddings_batch([c.text for c in chunks])

    store = get_faiss_store()
    store.clear()
    summary = DocumentSummary(
        doc_id=doc_id,
        filename="NIEL_Industrial_Motors_Catalogue_2026.pdf",
        page_count=len(pages),
        chunk_count=len(chunks),
        created_at="2026-10-30T00:00:00Z",
        file_size_bytes=len(content),
    )
    store.add_document_chunks(summary, chunks, embeddings)
    yield
    store.clear()


def test_session_service_crud_and_history():
    """Verify session creation, message logging, and turn truncation."""
    service = get_session_service()
    sid = service.create_session()
    assert sid is not None

    # Verify initial human_active is False
    assert service.is_human_active(sid) is False

    # Toggle human_active
    service.set_human_active(sid, True)
    assert service.is_human_active(sid) is True
    service.set_human_active(sid, False)
    assert service.is_human_active(sid) is False

    # Add messages
    service.add_message(sid, "user", "Hello assistant", request_id="r1")
    service.add_message(sid, "assistant", "Hello! How can I help?", request_id="r1")

    history = service.get_recent_history(sid, max_turns=8)
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello assistant"}
    assert history[1] == {"role": "assistant", "content": "Hello! How can I help?"}


def test_rag_service_multiturn_using_server_side_history():
    """Verify that multi-turn follow-up QA succeeds using ONLY server-stored history via session_id."""
    service = get_session_service()
    sid = service.create_session()
    rag_service = get_rag_service()

    # Turn 1: Ask motor question with session_id, no client history
    resp1 = rag_service.answer_question(
        question="What power ratings are documented for NIEL motors?",
        session_id=sid,
        conversation_history=None,
    )
    assert resp1.evidence_sufficient is True
    assert "0.75 kW to 315 kW" in resp1.answer

    # Verify Turn 1 was persisted on server
    history1 = service.get_recent_history(sid, max_turns=10)
    assert len(history1) == 2
    assert history1[0]["role"] == "user"
    assert history1[1]["role"] == "assistant"

    # Turn 2: Follow-up question relying on prior turn topic, without passing conversation_history
    resp2 = rag_service.answer_question(
        question="What about its IP rating?",
        session_id=sid,
        conversation_history=None,
    )
    assert resp2.evidence_sufficient is True
    assert "IP55" in resp2.answer

    # Verify Turn 2 was persisted on server (4 turns total)
    history2 = service.get_recent_history(sid, max_turns=10)
    assert len(history2) == 4
    assert history2[2]["role"] == "user"
    assert history2[2]["content"] == "What about its IP rating?"
    assert history2[3]["role"] == "assistant"


def test_rest_chat_endpoint_with_session_id():
    """Verify POST /api/v1/chat endpoint persists and retrieves conversation turns via session_id."""
    service = get_session_service()
    sid = service.create_session()

    # First turn via API
    r1 = client.post(
        "/api/v1/chat",
        json={
            "question": "What power ratings are documented for NIEL motors?",
            "session_id": sid,
        },
    )
    assert r1.status_code == 200
    assert "0.75 kW to 315 kW" in r1.json()["answer"]

    # Second turn via API with no conversation_history
    r2 = client.post(
        "/api/v1/chat",
        json={
            "question": "What mounting types are listed for these motors?",
            "session_id": sid,
        },
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["evidence_sufficient"] is True
    assert "B3" in data2["answer"] or "B5" in data2["answer"]

    # Verify messages in server DB
    history = service.get_recent_history(sid, max_turns=10)
    assert len(history) == 4
