"""SQLAlchemy engine and session factory for SQLite persistence."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import get_settings
from backend.app.db.models import Base

settings = get_settings()
DB_FILE = settings.DATA_DIR / "niel_sessions.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(engine_override=None):
    """Create all database tables if not already present."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)


# Auto-initialize SQLite database tables on startup
init_db()


def get_db():
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
