"""SQLAlchemy engine and session factory for SQLite persistence."""

from pathlib import Path
from sqlalchemy import create_engine, inspect, text
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


def run_migrations(target_engine):
    """Run lightweight schema updates for SQLite if existing tables lack newer columns."""
    try:
        inspector = inspect(target_engine)
        if "chat_sessions" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("chat_sessions")]
            if "customer_id" not in columns:
                with target_engine.connect() as conn:
                    conn.execute(
                        text("ALTER TABLE chat_sessions ADD COLUMN customer_id VARCHAR(64) REFERENCES customers(id)")
                    )
                    conn.commit()
    except Exception:
        # If in-memory or transient DB during testing without existing tables, create_all handles it
        pass


def init_db(engine_override=None):
    """Create all database tables and apply pending migrations."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)
    run_migrations(target_engine)


# Auto-initialize SQLite database tables on startup
init_db()


def get_db():
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
