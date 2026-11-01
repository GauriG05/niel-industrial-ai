"""WebSocket endpoint for realtime two-way chat with session memory and human handoff."""

import json
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.config import get_settings
from backend.app.agent.orchestrator import get_agent_orchestrator
from backend.app.services.rag_service import get_rag_service
from backend.app.services.session_service import get_session_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    In-memory WebSocket connection registry scoped to this server process.
    Known limitation: Multi-worker or multi-server deployments require an external
    pub/sub layer (such as Redis Pub/Sub) to synchronize across processes.
    """

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept connection and register under the session."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info("WebSocket connected for session %s (count: %d)", session_id, len(self.active_connections[session_id]))

    def disconnect(self, session_id: str, websocket: WebSocket):
        """Remove disconnected socket from registry."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info("WebSocket disconnected for session %s", session_id)

    async def send_json(self, websocket: WebSocket, data: dict):
        """Send JSON payload to a specific socket."""
        await websocket.send_json(data)

    async def broadcast_to_session(self, session_id: str, data: dict):
        """Broadcast JSON payload to all active client sockets in this session."""
        if session_id in self.active_connections:
            for connection in list(self.active_connections[session_id]):
                try:
                    await connection.send_json(data)
                except Exception as exc:
                    logger.warning("Failed to broadcast message to socket in session %s: %s", session_id, exc)


manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Singleton accessor for ConnectionManager."""
    return manager


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    """
    Realtime WebSocket chat endpoint.
    - Validates/creates session on connect.
    - If a human agent is active on this session, the AI stays silent and user messages
      are persisted and routed to the human dashboard.
    - If AI is active, evaluates input with RAG pipeline and returns grounded response.
    """
    settings = get_settings()
    session_service = get_session_service()
    rag_service = get_rag_service()

    # Validate or initialize session in database
    session_service.get_or_create(session_id)

    await manager.connect(session_id, websocket)

    try:
        # Send initial session handshake
        is_human = session_service.is_human_active(session_id)
        await websocket.send_json({
            "type": "session_init",
            "session_id": session_id,
            "human_active": is_human,
        })

        while True:
            raw_text = await websocket.receive_text()

            # Parse payload
            question = ""
            action = None
            try:
                payload = json.loads(raw_text)
                if isinstance(payload, dict):
                    question = (payload.get("question") or payload.get("content") or "").strip()
                    action = payload.get("action")
                else:
                    question = str(payload).strip()
            except (json.JSONDecodeError, TypeError):
                question = raw_text.strip()

            # Handle explicit manual escalation action from frontend
            if action == "escalate":
                from backend.app.services.escalation_service import get_escalation_service
                esc_service = get_escalation_service()
                await esc_service.escalate_session(
                    session_id=session_id,
                    triggering_message=question or "User requested human agent.",
                )
                await manager.broadcast_to_session(session_id, {
                    "type": "escalated",
                    "answer": "Your conversation has been routed to a human support engineer at New India Electricals Ltd. An engineer will join shortly.",
                    "human_active": True,
                })
                continue

            # Handle resuming AI assistant from frontend
            if action in ("resolve", "resume_ai", "reset_session"):
                session_service.resolve_human(session_id)
                await manager.broadcast_to_session(session_id, {
                    "type": "session_resolved",
                    "answer": "Connected back with NIEL AI Assistant. How can I help you?",
                    "human_active": False,
                })
                continue

            if not question:
                continue

            # Length bounds check
            if len(question) > settings.MAX_QUESTION_LENGTH:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Question exceeds maximum allowed length of {settings.MAX_QUESTION_LENGTH} characters.",
                })
                continue

            # Check if text contains conversational escalation triggers
            from backend.app.services.escalation_service import get_escalation_service
            esc_service = get_escalation_service()
            if esc_service.check_escalation_trigger(question):
                await esc_service.escalate_session(
                    session_id=session_id,
                    triggering_message=question,
                )
                from urllib.parse import quote
                wa_summary = "Hello NIEL Team, I would like human support assistance regarding an inquiry on your website"
                wa_url = f"https://wa.me/919741307999?text={quote(wa_summary)}"
                await manager.broadcast_to_session(session_id, {
                    "type": "escalated",
                    "answer": (
                        "I can connect you directly with our engineering support team at New India Electricals Ltd.\n\n"
                        f"👉 Click here to chat with our team on WhatsApp (+91 97413 07999):\n{wa_url}\n\n"
                        "Our engineers will assist you directly on WhatsApp. You can also continue asking any product or technical questions right here!"
                    ),
                    "human_active": True,
                })
                continue

            # Check human agent active state
            if session_service.is_human_active(session_id):
                if question.strip().lower() in ["are you still there?", "are you there", "are you there?"]:
                    # Record user message in DB
                    session_service.add_message(
                        session_id=session_id,
                        role="user",
                        content=question,
                    )
                    # Broadcast user message to connected agents/sockets without LLM call
                    await manager.broadcast_to_session(session_id, {
                        "type": "user_message",
                        "role": "user",
                        "content": question,
                        "human_active": True,
                    })
                    continue
                else:
                    # User is continuing with product/technical inquiry or clicking pills
                    session_service.resolve_human(session_id)

            # AI handles message via Agent Orchestrator
            orchestrator = get_agent_orchestrator()
            response = orchestrator.handle_request(
                question=question,
                session_id=session_id,
            )

            await websocket.send_json({
                "type": "answer",
                "answer": response.answer,
                "citations": [c.model_dump() for c in response.citations],
                "pdf_attachments": [p.model_dump() for p in (response.pdf_attachments or [])],
                "evidence_sufficient": response.evidence_sufficient,
                "clarification_needed": response.clarification_needed,
                "request_id": response.request_id,
                "human_active": response.escalated or False,
                "ticket_id": response.ticket_id,
                "lead_id": response.lead_id,
                "intent": response.intent,
            })

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception as exc:
        logger.error("WebSocket exception for session %s: %s", session_id, exc)
        manager.disconnect(session_id, websocket)
