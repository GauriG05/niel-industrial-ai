"""Sales lead management service for capturing, scoring, and tracking B2B enquiries."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.db.models import SalesLead
from backend.app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class LeadService:
    """Manages B2B sales lead qualification, scoring, and status workflows."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def _get_db(self) -> Session:
        return self.session_factory()

    def calculate_priority_and_score(
        self,
        product_interest: str,
        requirement_details: Optional[str] = None,
        required_quantity: Optional[int] = None,
        company: Optional[str] = None,
    ) -> tuple[str, int]:
        """
        Calculate qualification priority (URGENT, HIGH, MEDIUM, LOW) and lead score (0-100).
        High capacity equipment or large volume enquiries receive higher priority.
        """
        score = 30  # Baseline for any B2B inquiry
        priority = "MEDIUM"

        # Quantity scoring
        qty = required_quantity or 1
        if qty >= 10:
            score += 35
            priority = "URGENT"
        elif qty >= 3:
            score += 20
            priority = "HIGH"

        # High capacity or industrial scope keywords
        high_val_keywords = ["315kw", "2000kva", "mcc", "pcc", "ht panel", "11kv", "substation", "turnkey"]
        text_to_check = f"{product_interest} {requirement_details or ''}".lower()
        if any(kw in text_to_check for kw in high_val_keywords):
            score += 25
            if priority != "URGENT":
                priority = "HIGH"

        # Corporate / Company presence
        if company and len(company.strip()) > 2:
            score += 15

        final_score = min(score, 100)
        return priority, final_score

    def create_lead(
        self,
        product_interest: str,
        customer_id: Optional[str] = None,
        session_id: Optional[str] = None,
        requirement_details: Optional[str] = None,
        required_quantity: Optional[int] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> SalesLead:
        """Create a new sales lead with automatic scoring and priority assignment."""
        priority, _ = self.calculate_priority_and_score(
            product_interest=product_interest,
            requirement_details=requirement_details,
            required_quantity=required_quantity,
            company=company,
        )

        def _execute(session: Session) -> SalesLead:
            lead = SalesLead(
                customer_id=customer_id,
                session_id=session_id,
                product_interest=product_interest,
                requirement_details=requirement_details,
                required_quantity=required_quantity,
                location=location,
                status="NEW",
                priority=priority,
                created_at=datetime.now(timezone.utc),
            )
            session.add(lead)
            session.commit()
            session.refresh(lead)
            return lead

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def get_lead(self, lead_id: int, db: Optional[Session] = None) -> Optional[SalesLead]:
        """Fetch lead by its primary ID."""
        def _execute(session: Session) -> Optional[SalesLead]:
            return session.query(SalesLead).filter_by(id=lead_id).first()

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def list_leads(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> List[SalesLead]:
        """List recent sales leads with optional filtering."""
        def _execute(session: Session) -> List[SalesLead]:
            query = session.query(SalesLead)
            if status:
                query = query.filter_by(status=status.upper())
            if priority:
                query = query.filter_by(priority=priority.upper())
            return query.order_by(SalesLead.created_at.desc()).limit(limit).all()

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def update_lead_status(
        self,
        lead_id: int,
        status: str,
        db: Optional[Session] = None,
    ) -> Optional[SalesLead]:
        """Update lead status (NEW, QUALIFIED, CONTACTED, CLOSED)."""
        def _execute(session: Session) -> Optional[SalesLead]:
            lead = session.query(SalesLead).filter_by(id=lead_id).first()
            if not lead:
                return None
            lead.status = status.upper()
            session.commit()
            session.refresh(lead)
            return lead

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)


_lead_service_instance: Optional[LeadService] = None


def get_lead_service() -> LeadService:
    """Singleton accessor for LeadService."""
    global _lead_service_instance
    if _lead_service_instance is None:
        _lead_service_instance = LeadService()
    return _lead_service_instance

