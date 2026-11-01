"""Session service for server-side chat session management and message persistence."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from backend.app.db.models import ChatMessage, ChatSession
from backend.app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class SessionService:
    """Manages chat sessions, turn persistence, and escalation state."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def _get_db(self) -> Session:
        return self.session_factory()

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session record and return the session ID."""
        sid = session_id or str(uuid.uuid4())
        with self._get_db() as db:
            existing = db.query(ChatSession).filter_by(id=sid).first()
            if not existing:
                chat_session = ChatSession(
                    id=sid,
                    created_at=datetime.now(timezone.utc),
                    human_active=False,
                )
                db.add(chat_session)
                db.commit()
        return sid

    def get_or_create(self, session_id: Optional[str] = None) -> ChatSession:
        """Retrieve an existing session or initialize a new one."""
        sid = session_id or str(uuid.uuid4())
        with self._get_db() as db:
            session = db.query(ChatSession).filter_by(id=sid).first()
            if not session:
                session = ChatSession(
                    id=sid,
                    created_at=datetime.now(timezone.utc),
                    human_active=False,
                )
                db.add(session)
                db.commit()
                db.refresh(session)
            return session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[List[Any]] = None,
        request_id: Optional[str] = None,
    ) -> ChatMessage:
        """Persist a conversation turn for a given session."""
        self.get_or_create(session_id)

        citations_json = None
        if citations:
            try:
                dumped = [c.model_dump() if hasattr(c, "model_dump") else c for c in citations]
                citations_json = json.dumps(dumped)
            except Exception as exc:
                logger.warning("Failed to serialize citations to JSON: %s", exc)

        with self._get_db() as db:
            msg = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                created_at=datetime.now(timezone.utc),
                citations_json=citations_json,
                request_id=request_id,
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)
            return msg

    def get_recent_history(
        self,
        session_id: str,
        max_turns: int = 8,
    ) -> List[Dict[str, str]]:
        """
        Retrieve recent conversation turns for the session in chronological order.
        Returns a list of dicts: [{"role": ..., "content": ...}].
        """
        with self._get_db() as db:
            messages = (
                db.query(ChatMessage)
                .filter_by(session_id=session_id)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                .limit(max_turns)
                .all()
            )
            # Reverse descending slice to restore chronological order
            chronological = list(reversed(messages))
            return [{"role": m.role, "content": m.content} for m in chronological]

    def set_human_active(self, session_id: str, active: bool):
        """Set whether a human agent is currently actively handling this session."""
        self.get_or_create(session_id)
        with self._get_db() as db:
            session = db.query(ChatSession).filter_by(id=session_id).first()
            if session:
                session.human_active = active
                if active:
                    session.escalated_at = datetime.now(timezone.utc)
                db.commit()

    def is_human_active(self, session_id: str) -> bool:
        """Check if a human agent has escalated and taken control of the session."""
        with self._get_db() as db:
            session = db.query(ChatSession).filter_by(id=session_id).first()
            if not session:
                return False
            return bool(session.human_active)

    def list_escalated_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions currently flagged as human_active."""
        with self._get_db() as db:
            sessions = (
                db.query(ChatSession)
                .filter_by(human_active=True)
                .order_by(ChatSession.escalated_at.desc())
                .all()
            )
            result = []
            for s in sessions:
                # Get last message as preview
                last_msg = (
                    db.query(ChatMessage)
                    .filter_by(session_id=s.id)
                    .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                    .first()
                )
                result.append({
                    "session_id": s.id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "escalated_at": s.escalated_at.isoformat() if s.escalated_at else None,
                    "human_active": s.human_active,
                    "last_message": last_msg.content if last_msg else None,
                    "last_message_role": last_msg.role if last_msg else None,
                })
            return result

    def get_full_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get complete chronological history with metadata for human agent dashboard."""
        with self._get_db() as db:
            messages = (
                db.query(ChatMessage)
                .filter_by(session_id=session_id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                .all()
            )
            return [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "request_id": m.request_id,
                }
                for m in messages
            ]


_session_service_instance: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """Singleton accessor for SessionService."""
    global _session_service_instance
    if _session_service_instance is None:
        _session_service_instance = SessionService()
    return _session_service_instance
