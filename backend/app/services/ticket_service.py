"""Support ticket management service with safety guardrails and tracking code generation."""

import logging
import random
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.db.models import SupportTicket
from backend.app.db.session import SessionLocal

logger = logging.getLogger(__name__)

CRITICAL_SAFETY_KEYWORDS = [
    "smoke", "smoking", "fire", "spark", "sparking", "shock", "electric shock",
    "burning", "burned out", "explosion", "exploded", "flame", "blast", "live wire"
]

HIGH_SEVERITY_KEYWORDS = [
    "tripping", "tripped", "overheating", "high temperature", "shutdown",
    "stopped running", "stalled", "stuck", "production halted", "line stopped"
]

SAFETY_ADVISORY = (
    "CRITICAL SAFETY ADVISORY: Do not attempt uncertified DIY maintenance or live circuit adjustments "
    "on high-voltage electrical equipment. Immediately isolate power at the main switchboard and await "
    "authorized NIEL service engineers."
)


class TicketService:
    """Manages support ticket generation, safety evaluation, and resolution status."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def _get_db(self) -> Session:
        return self.session_factory()

    def generate_ticket_id(self, db: Optional[Session] = None) -> str:
        """Generate a collision-resistant ticket identifier formatted as TK-2026-XXXX."""
        year = datetime.now(timezone.utc).year

        def _execute(session: Session) -> str:
            for _ in range(100):
                suffix = f"{random.randint(1000, 9999)}"
                candidate_id = f"TK-{year}-{suffix}"
                if not session.query(SupportTicket).filter_by(id=candidate_id).first():
                    return candidate_id
            return f"TK-{year}-{random.randint(10000, 99999)}"

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def evaluate_severity_and_safety(
        self,
        issue_description: str,
        product_category: str = "",
    ) -> Tuple[str, Optional[str]]:
        """
        Evaluate issue severity (CRITICAL, HIGH, MEDIUM, LOW) and attach safety advisory if warranted.
        """
        text = f"{issue_description} {product_category}".lower()

        # Check critical hazards
        if any(re.search(rf"\b{kw}\b", text) for kw in CRITICAL_SAFETY_KEYWORDS):
            return "CRITICAL", SAFETY_ADVISORY

        # Check high severity production impacts
        if any(re.search(rf"\b{kw}\b", text) for kw in HIGH_SEVERITY_KEYWORDS):
            return "HIGH", None

        # Check medium severity warnings
        medium_keywords = ["vibration", "abnormal noise", "oil leak", "alarm", "temperature rise", "bearing"]
        if any(re.search(rf"\b{kw}\b", text) for kw in medium_keywords):
            return "MEDIUM", None

        return "LOW", None

    def create_ticket(
        self,
        product_category: str,
        issue_description: str,
        customer_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity_override: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Tuple[SupportTicket, Optional[str]]:
        """Create a new support ticket and enforce safety warnings when applicable."""
        auto_severity, safety_advisory = self.evaluate_severity_and_safety(
            issue_description=issue_description,
            product_category=product_category,
        )
        severity = severity_override.upper() if severity_override else auto_severity

        def _execute(session: Session) -> Tuple[SupportTicket, Optional[str]]:
            tid = self.generate_ticket_id(session)
            ticket = SupportTicket(
                id=tid,
                customer_id=customer_id,
                session_id=session_id,
                product_category=product_category,
                issue_description=issue_description,
                severity=severity,
                status="OPEN",
                created_at=datetime.now(timezone.utc),
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket, safety_advisory

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def get_ticket(self, ticket_id: str, db: Optional[Session] = None) -> Optional[SupportTicket]:
        """Fetch a ticket by its ID."""
        def _execute(session: Session) -> Optional[SupportTicket]:
            return session.query(SupportTicket).filter_by(id=ticket_id).first()

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def list_tickets(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> List[SupportTicket]:
        """List tickets with optional status and severity filters."""
        def _execute(session: Session) -> List[SupportTicket]:
            query = session.query(SupportTicket)
            if status:
                query = query.filter_by(status=status.upper())
            if severity:
                query = query.filter_by(severity=severity.upper())
            return query.order_by(SupportTicket.created_at.desc()).limit(limit).all()

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def resolve_ticket(self, ticket_id: str, db: Optional[Session] = None) -> Optional[SupportTicket]:
        """Mark a ticket as RESOLVED with timestamp."""
        def _execute(session: Session) -> Optional[SupportTicket]:
            ticket = session.query(SupportTicket).filter_by(id=ticket_id).first()
            if not ticket:
                return None
            ticket.status = "RESOLVED"
            ticket.resolved_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(ticket)
            return ticket

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)


_ticket_service_instance: Optional[TicketService] = None


def get_ticket_service() -> TicketService:
    """Singleton accessor for TicketService."""
    global _ticket_service_instance
    if _ticket_service_instance is None:
        _ticket_service_instance = TicketService()
    return _ticket_service_instance

