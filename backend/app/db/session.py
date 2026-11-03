"""SQLAlchemy engine and session factory supporting PostgreSQL and SQLite persistence."""

from contextlib import contextmanager
import logging
from pathlib import Path
from typing import Generator, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import get_settings
from backend.app.db.models import Base

logger = logging.getLogger("niel.db")
settings = get_settings()

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    DB_FILE = settings.DATA_DIR / "niel_sessions.db"
    DATABASE_URL = f"sqlite:///{DB_FILE}"

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # Production PostgreSQL connection pool configuration
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_db_health(db_session: Optional[Session] = None) -> bool:
    """Check connectivity to the database by executing a lightweight query."""
    try:
        if db_session:
            db_session.execute(text("SELECT 1"))
        else:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return False


@contextmanager
def transaction_scope(db_session: Optional[Session] = None) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of database operations."""
    session = db_session or SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if db_session is None:
            session.close()


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
        pass


def init_db(engine_override=None):
    """Create all database tables and apply pending migrations."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)
    run_migrations(target_engine)


# Auto-initialize database tables on startup
init_db()


def get_db():
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
