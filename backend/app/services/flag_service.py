"""Service for passively logging and managing flagged customer queries touching unverified product specs."""

from datetime import datetime, timezone
import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import FlaggedQuery
from backend.app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class FlagService:
    """Manages engineering review flags for queries about unverified product parameters."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def log_flagged_query(
        self,
        user_question: str,
        product_category: str,
        unverified_field: str,
        session_id: Optional[str] = None,
    ) -> Optional[FlaggedQuery]:
        """Passively log a user question touching an unverified spec field."""
        db: Session = self.session_factory()
        try:
            entry = FlaggedQuery(
                timestamp=datetime.now(timezone.utc),
                user_question=user_question,
                product_category=product_category,
                unverified_field=unverified_field,
                session_id=session_id,
                resolved=False,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            logger.info(
                "Logged flagged query ID %s for category '%s' field '%s'",
                entry.id,
                product_category,
                unverified_field,
            )
            return entry
        except Exception as exc:
            db.rollback()
            logger.error("Failed to passively log flagged query: %s", exc)
            return None
        finally:
            db.close()

    def list_flagged_queries(
        self,
        resolved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FlaggedQuery]:
        """Retrieve flagged queries for engineering review, optionally filtered by resolution status."""
        db: Session = self.session_factory()
        try:
            stmt = select(FlaggedQuery)
            if resolved is not None:
                stmt = stmt.where(FlaggedQuery.resolved == resolved)
            stmt = stmt.order_by(FlaggedQuery.timestamp.desc()).offset(offset).limit(limit)
            return list(db.scalars(stmt).all())
        finally:
            db.close()

    def resolve_flagged_query(
        self,
        flag_id: int,
        resolved: bool = True,
    ) -> Optional[FlaggedQuery]:
        """Update resolution status of a flagged query entry."""
        db: Session = self.session_factory()
        try:
            entry = db.get(FlaggedQuery, flag_id)
            if not entry:
                return None
            entry.resolved = resolved
            db.commit()
            db.refresh(entry)
            return entry
        except Exception as exc:
            db.rollback()
            logger.error("Failed to resolve flagged query ID %s: %s", flag_id, exc)
            return None
        finally:
            db.close()


_flag_service_instance: Optional[FlagService] = None


def get_flag_service() -> FlagService:
    """Singleton accessor for FlagService."""
    global _flag_service_instance
    if _flag_service_instance is None:
        _flag_service_instance = FlagService()
    return _flag_service_instance

