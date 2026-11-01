"""Customer service for managing persistent customer profiles, consent, and memory context."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.db.models import Customer, ChatSession, SalesLead, SupportTicket
from backend.app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class CustomerService:
    """Provides methods for managing customer records, consented preferences, and profile context."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def _get_db(self) -> Session:
        return self.session_factory()

    def get_or_create_customer(
        self,
        customer_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Customer:
        """
        Retrieve an existing customer by ID, email, or phone, or create a new profile.
        If existing customer is found, non-null fields provided will update missing attributes.
        """
        def _execute(session: Session) -> Customer:
            customer = None
            if customer_id:
                customer = session.query(Customer).filter_by(id=customer_id).first()
            if not customer and email:
                customer = session.query(Customer).filter(Customer.email.ilike(email.strip())).first()
            if not customer and phone:
                customer = session.query(Customer).filter_by(phone=phone.strip()).first()

            if customer:
                # Update attributes if provided and previously missing
                changed = False
                if name and not customer.name:
                    customer.name = name.strip()
                    changed = True
                if email and not customer.email:
                    customer.email = email.strip()
                    changed = True
                if phone and not customer.phone:
                    customer.phone = phone.strip()
                    changed = True
                if company and not customer.company:
                    customer.company = company.strip()
                    changed = True
                if changed:
                    customer.updated_at = datetime.now(timezone.utc)
                    session.commit()
                    session.refresh(customer)
                return customer

            # Create new customer profile
            cid = customer_id or f"cust-{uuid.uuid4().hex[:12]}"
            new_customer = Customer(
                id=cid,
                name=name.strip() if name else None,
                email=email.strip().lower() if email else None,
                phone=phone.strip() if phone else None,
                company=company.strip() if company else None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(new_customer)
            session.commit()
            session.refresh(new_customer)
            return new_customer

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def update_customer_profile(
        self,
        customer_id: str,
        name: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        interests: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Optional[Customer]:
        """Update customer personal info, industry, product interests, and preferences."""
        def _execute(session: Session) -> Optional[Customer]:
            customer = session.query(Customer).filter_by(id=customer_id).first()
            if not customer:
                return None

            if name:
                customer.name = name.strip()
            if company:
                customer.company = company.strip()
            if industry:
                customer.industry = industry.strip()

            # Merge product interests list
            if interests is not None:
                current_interests = []
                if customer.interests_json:
                    try:
                        current_interests = json.loads(customer.interests_json)
                    except Exception:
                        current_interests = []
                
                # Case-insensitive dedup
                seen = {item.strip().lower() for item in current_interests if isinstance(item, str)}
                for item in interests:
                    if isinstance(item, str) and item.strip() and item.strip().lower() not in seen:
                        current_interests.append(item.strip())
                        seen.add(item.strip().lower())
                customer.interests_json = json.dumps(current_interests)

            # Merge preferences dictionary
            if preferences is not None:
                current_prefs = {}
                if customer.preferences_json:
                    try:
                        current_prefs = json.loads(customer.preferences_json)
                    except Exception:
                        current_prefs = {}
                current_prefs.update(preferences)
                customer.preferences_json = json.dumps(current_prefs)

            customer.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(customer)
            return customer

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def record_consent(self, customer_id: str, db: Optional[Session] = None) -> Optional[Customer]:
        """Record customer consent timestamp for storing contact preferences."""
        def _execute(session: Session) -> Optional[Customer]:
            customer = session.query(Customer).filter_by(id=customer_id).first()
            if not customer:
                return None
            customer.consented_at = datetime.now(timezone.utc)
            customer.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(customer)
            return customer

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def delete_customer_data(self, customer_id: str, db: Optional[Session] = None) -> bool:
        """
        Delete customer record for GDPR / Right-to-be-forgotten requests.
        Unlinks associated chat sessions without deleting conversation records.
        """
        def _execute(session: Session) -> bool:
            customer = session.query(Customer).filter_by(id=customer_id).first()
            if not customer:
                return False

            # Nullify customer_id in linked sessions
            sessions = session.query(ChatSession).filter_by(customer_id=customer_id).all()
            for s in sessions:
                s.customer_id = None

            session.delete(customer)
            session.commit()
            return True

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)

    def get_customer_context(self, customer_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """
        Produce a concise context summary dictionary of the customer for agent prompt injection.
        """
        def _execute(session: Session) -> Optional[Dict[str, Any]]:
            customer = session.query(Customer).filter_by(id=customer_id).first()
            if not customer:
                return None

            interests = []
            if customer.interests_json:
                try:
                    interests = json.loads(customer.interests_json)
                except Exception:
                    interests = []

            preferences = {}
            if customer.preferences_json:
                try:
                    preferences = json.loads(customer.preferences_json)
                except Exception:
                    preferences = {}

            tickets = session.query(SupportTicket).filter_by(customer_id=customer_id).order_by(SupportTicket.created_at.desc()).all()
            leads = session.query(SalesLead).filter_by(customer_id=customer_id).order_by(SalesLead.created_at.desc()).all()

            open_tickets = [t for t in tickets if t.status not in ("RESOLVED", "CLOSED")]

            return {
                "customer_id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "company": customer.company,
                "industry": customer.industry,
                "interests": interests,
                "preferences": preferences,
                "has_consented": customer.consented_at is not None,
                "open_tickets_count": len(open_tickets),
                "recent_tickets": [
                    {
                        "id": t.id,
                        "product_category": t.product_category,
                        "status": t.status,
                        "severity": t.severity,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                    }
                    for t in tickets[:3]
                ],
                "recent_leads": [
                    {
                        "id": l.id,
                        "product_interest": l.product_interest,
                        "status": l.status,
                        "priority": l.priority,
                        "created_at": l.created_at.isoformat() if l.created_at else None,
                    }
                    for l in leads[:3]
                ],
            }

        if db is not None:
            return _execute(db)
        with self._get_db() as session:
            return _execute(session)


_customer_service_instance: Optional[CustomerService] = None


def get_customer_service() -> CustomerService:
    """Singleton accessor for CustomerService."""
    global _customer_service_instance
    if _customer_service_instance is None:
        _customer_service_instance = CustomerService()
    return _customer_service_instance

