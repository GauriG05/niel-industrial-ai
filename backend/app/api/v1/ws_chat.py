"""WebSocket endpoint for realtime two-way chat with session memory and human handoff.

Hardened with signed session tokens, connection limits, message rate limiting,
origin validation, and role-based action authorization.
"""

import hmac
import json
import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from backend.app.config import get_settings
from backend.app.agent.orchestrator import get_agent_orchestrator
from backend.app.security.tokens import TokenError, TokenExpiredError, TokenInvalidError, validate_session_token_for_session
from backend.app.services.rag_service import get_rag_service
from backend.app.services.session_service import get_session_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    WebSocket connection registry scoped to this server process with connection limits.
    """

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    def get_connection_count(self, session_id: str) -> int:
        """Return number of active WebSocket connections for a given session."""
        return len(self.active_connections.get(session_id, []))

    async def connect(self, session_id: str, websocket: WebSocket, max_connections: int = 5):
        """Accept connection and register under the session if within limits."""
        if self.get_connection_count(session_id) >= max_connections:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Too many active connections for this session.",
            )
            raise ConnectionRefusedError("Session connection limit reached.")

        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info("WebSocket connected for session %s (active: %d)", session_id, len(self.active_connections[session_id]))

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


def _is_origin_allowed(origin: Optional[str], allowed_origins: List[str]) -> bool:
    """Verify WebSocket Origin header matches configured CORS origins."""
    if not origin:
        # Direct non-browser clients (tests/scripts) may not provide an Origin header
        return True

    origin_clean = origin.rstrip("/")
    for allowed in allowed_origins:
        allowed_clean = allowed.rstrip("/")
        if origin_clean == allowed_clean or allowed_clean == "*":
            return True

    # Also permit default development localhost ports
    parsed = urlparse(origin_clean)
    if parsed.hostname in ("localhost", "127.0.0.1", "newindiaelectricals.com"):
        return True

    return False


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
):
    """
    Secure realtime WebSocket chat endpoint.
    - Validates Origin against allowed origins.
    - Requires short-lived HMAC-SHA256 session token to prevent unauthorized session access.
    - Enforces maximum concurrent connections per session.
    - Enforces sliding message rate limits per connection.
    - Restricts privileged admin actions (resolve, resume_ai, reset_session).
    """
    settings = get_settings()
    session_service = get_session_service()

    # 1. Validate Origin header
    origin = websocket.headers.get("origin")
    if not _is_origin_allowed(origin, settings.cors_origins):
        logger.warning("WebSocket rejected: Unauthorized origin '%s' for session %s", origin, session_id)
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Unauthorized Origin.",
        )
        return

    # 2. Authenticate session token
    # Check query param first, then Authorization header
    auth_token = token
    if not auth_token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header[7:].strip()

    is_production = settings.ENVIRONMENT.lower() == "production"
    authenticated_cid = None

    if auth_token:
        try:
            payload = validate_session_token_for_session(auth_token, session_id)
            authenticated_cid = payload.get("cid")
        except TokenExpiredError:
            logger.warning("WebSocket rejected: Expired token for session %s", session_id)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session token expired.")
            return
        except TokenError as exc:
            logger.warning("WebSocket rejected: Invalid token for session %s: %s", session_id, exc)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid session token.")
            return
    elif is_production:
        logger.warning("WebSocket rejected in production: Missing session token for session %s", session_id)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing required session token.")
        return

    # 3. Connect to manager with concurrency check
    try:
        await manager.connect(
            session_id,
            websocket,
            max_connections=settings.WS_MAX_CONNECTIONS_PER_SESSION,
        )
    except ConnectionRefusedError:
        return

    # Validate or initialize session in database
    session_service.get_or_create(session_id, customer_id=authenticated_cid)

    # Message rate limiting tracker for this socket
    message_timestamps: List[float] = []

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

            # Enforce message rate limit per connection
            now = time.time()
            message_timestamps = [ts for ts in message_timestamps if ts > now - 60.0]
            if len(message_timestamps) >= settings.WS_MAX_MESSAGES_PER_MINUTE:
                await websocket.send_json({
                    "type": "error",
                    "detail": "Message rate limit exceeded. Please wait a moment before sending another message.",
                })
                continue
            message_timestamps.append(now)

            # Parse payload
            question = ""
            action = None
            admin_key = None
            try:
                payload = json.loads(raw_text)
                if isinstance(payload, dict):
                    question = (payload.get("question") or payload.get("content") or "").strip()
                    action = payload.get("action")
                    admin_key = payload.get("admin_key")
                else:
                    question = str(payload).strip()
            except (json.JSONDecodeError, TypeError):
                question = raw_text.strip()

            # Handle explicit manual escalation action from frontend (allowed for customers)
            if action == "escalate":
                from backend.app.services.escalation_service import get_escalation_service
                esc_service = get_escalation_service()
                await esc_service.escalate_session(
                    session_id=session_id,
                    triggering_message=question or "User requested human agent.",
                )
                from urllib.parse import quote
                wa_summary = "Hello NIEL Team, I would like human support assistance regarding an inquiry on your website"
                wa_url = f"https://wa.me/919741307999?text={quote(wa_summary)}"
                await manager.broadcast_to_session(session_id, {
                    "type": "escalated",
                    "answer": (
                        "I can connect you directly with our engineering support team at New India Electricals Ltd.\n\n"
                        f"{wa_url}\n\n"
                        "Our engineers will assist you directly on WhatsApp. You can also continue asking right here!"
                    ),
                    "human_active": True,
                    "whatsapp_url": wa_url,
                })
                continue

            # Privileged actions (resolve, resume_ai, reset_session) REQUIRE admin verification
            if action in ("resolve", "resume_ai", "reset_session"):
                is_admin_authorized = False
                if admin_key and hmac.compare_digest(admin_key.strip().encode("utf-8"), settings.ADMIN_API_KEY.strip().encode("utf-8")):
                    is_admin_authorized = True

                if not is_admin_authorized:
                    await websocket.send_json({
                        "type": "error",
                        "detail": "Unauthorized: Administrative key required for this action.",
                    })
                    continue

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
                        f"{wa_url}\n\n"
                        "Our engineers will assist you directly on WhatsApp. You can also continue asking any product or technical questions right here!"
                    ),
                    "human_active": True,
                    "whatsapp_url": wa_url,
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
                        "session_id": session_id,
                        "human_active": True,
                    })
                continue

            # Normal AI question answering via Orchestrator
            orchestrator = get_agent_orchestrator()
            response = orchestrator.handle_request(
                question=question,
                top_k=settings.MAX_RETRIEVAL_CHUNKS,
                session_id=session_id,
                customer_id=authenticated_cid,
            )

            # Persist turns if not already stored by internal RAG pipeline
            last_history = session_service.get_recent_history(session_id, max_turns=1)
            if not last_history or last_history[-1].get("content") != response.answer:
                session_service.add_message(
                    session_id=session_id,
                    role="user",
                    content=question,
                )
                session_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=response.answer,
                )

            # Broadcast answer to session
            await manager.broadcast_to_session(session_id, {
                "type": "answer",
                "answer": response.answer,
                "citations": [c.model_dump() for c in response.citations],
                "pdf_attachments": [p.model_dump() for p in (response.pdf_attachments or [])],
                "site_url": response.site_url,
                "whatsapp_url": response.whatsapp_url,
                "evidence_sufficient": response.evidence_sufficient,
                "clarification_needed": response.clarification_needed,
                "request_id": response.request_id,
                "intent": response.intent,
                "ticket_id": response.ticket_id,
                "lead_id": response.lead_id,
                "escalated": response.escalated,
            })

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception as exc:
        logger.error("Unhandled WebSocket exception in session %s: %s", session_id, exc, exc_info=True)
        manager.disconnect(session_id, websocket)
