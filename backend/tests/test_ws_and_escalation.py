"""Integration tests for WebSocket realtime chat, conversation memory, and human escalation."""

import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import get_settings
from backend.app.services.session_service import get_session_service
from backend.app.services.escalation_service import get_escalation_service
from backend.app.retrieval.faiss_store import get_faiss_store
from backend.app.schemas.documents import DocumentSummary
from backend.app.ingestion.hasher import compute_sha256_bytes
from backend.app.ingestion.extractor import extract_pages_from_pdf
from backend.app.ingestion.chunker import process_document_to_chunks
from backend.app.services.openai_service import get_openai_service

client = TestClient(app)
settings = get_settings()
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


def test_websocket_chat_multiturn_flow():
    """Test full multi-turn conversation over a single WebSocket connection."""
    service = get_session_service()
    sid = service.create_session()

    with client.websocket_connect(f"/ws/chat/{sid}") as ws:
        # Handshake
        init = ws.receive_json()
        assert init["type"] == "session_init"
        assert init["session_id"] == sid
        assert init["human_active"] is False

        # Turn 1
        ws.send_text(json.dumps({"question": "What power ratings are documented for NIEL motors?"}))
        resp1 = ws.receive_json()
        assert resp1["type"] == "answer"
        assert resp1["evidence_sufficient"] is True
        assert "0.75 kW to 315 kW" in resp1["answer"]

        # Turn 2: Follow-up question relying on server memory
        ws.send_text(json.dumps({"question": "What about its IP rating?"}))
        resp2 = ws.receive_json()
        assert resp2["type"] == "answer"
        assert resp2["evidence_sufficient"] is True
        assert "IP55" in resp2["answer"]

    # Verify server DB recorded all 4 turns
    history = service.get_recent_history(sid, max_turns=10)
    assert len(history) == 4
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert history[2]["role"] == "user"
    assert history[3]["role"] == "assistant"


def test_websocket_oversized_question_handled():
    """Verify question exceeding MAX_QUESTION_LENGTH returns validation error over socket."""
    service = get_session_service()
    sid = service.create_session()

    with client.websocket_connect(f"/ws/chat/{sid}") as ws:
        ws.receive_json()  # init
        too_long = "motor " * 150
        ws.send_text(json.dumps({"question": too_long}))
        err_resp = ws.receive_json()
        assert err_resp["type"] == "error"
        assert "exceeds maximum allowed length" in err_resp["detail"]


def test_websocket_escalation_and_human_agent_flow():
    """
    Test end-to-end human escalation:
    1. Visitor asks for a human -> escalation triggered.
    2. AI stops answering; user messages broadcast to session without LLM reply.
    3. Human agent replies via admin REST endpoint -> visitor receives agent message on WebSocket.
    4. Human agent resolves session -> AI resumes answering.
    """
    service = get_session_service()
    sid = service.create_session()
    admin_headers = {"X-Admin-Key": settings.ADMIN_API_KEY}

    with client.websocket_connect(f"/ws/chat/{sid}") as ws:
        ws.receive_json()  # init

        # 1. Trigger conversational escalation
        ws.send_text(json.dumps({"question": "Can I talk to a human agent please?"}))
        esc_msg = ws.receive_json()
        assert esc_msg["type"] == "escalated"
        assert esc_msg["human_active"] is True
        assert service.is_human_active(sid) is True

        # 2. Check admin escalations endpoint lists this session
        res_list = client.get("/api/v1/escalations", headers=admin_headers)
        assert res_list.status_code == 200
        active_sids = [item["session_id"] for item in res_list.json()]
        assert sid in active_sids

        # 3. User sends a message while human is active -> AI stays silent, user message broadcast
        ws.send_text(json.dumps({"question": "Are you still there?"}))
        user_broadcast = ws.receive_json()
        assert user_broadcast["type"] == "user_message"
        assert user_broadcast["content"] == "Are you still there?"
        assert user_broadcast["human_active"] is True

        # 4. Human agent sends reply via REST API
        agent_reply_text = "Hello! I am a senior application engineer at NIEL. How can I help with your project?"
        r_reply = client.post(
            f"/api/v1/escalations/{sid}/reply",
            headers=admin_headers,
            json={"content": agent_reply_text},
        )
        assert r_reply.status_code == 200

        # Verify visitor received agent message on open socket
        socket_msg = ws.receive_json()
        assert socket_msg["type"] == "agent_message"
        assert socket_msg["role"] == "agent"
        assert socket_msg["content"] == agent_reply_text

        # 5. Check full message history from admin endpoint
        res_msgs = client.get(f"/api/v1/escalations/{sid}/messages", headers=admin_headers)
        assert res_msgs.status_code == 200
        roles = [m["role"] for m in res_msgs.json()]
        assert "user" in roles
        assert "agent" in roles

        # 6. Human agent resolves session
        r_resolve = client.post(f"/api/v1/escalations/{sid}/resolve", headers=admin_headers)
        assert r_resolve.status_code == 200
        assert r_resolve.json()["human_active"] is False
        assert service.is_human_active(sid) is False

        # Visitor receives resolution notification on socket
        res_socket = ws.receive_json()
        assert res_socket["type"] == "session_resolved"
        assert res_socket["human_active"] is False

        # 7. AI resumes answering subsequent user queries
        ws.send_text(json.dumps({"question": "What mounting types are listed for these motors?"}))
        ai_resp = ws.receive_json()
        assert ai_resp["type"] == "answer"
        assert ai_resp["evidence_sufficient"] is True
        assert "B3" in ai_resp["answer"] or "B5" in ai_resp["answer"]
