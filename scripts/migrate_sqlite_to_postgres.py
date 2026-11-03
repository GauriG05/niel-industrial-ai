"""Safe database migration script transferring SQLite data to PostgreSQL.

Includes automatic backup creation, transaction rollback safety,
and data verification across all tables.
"""

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
import sys
from typing import Dict, Type

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings
from backend.app.db.models import (
    Base,
    Customer,
    ChatSession,
    ChatMessage,
    SalesLead,
    SupportTicket,
    FlaggedQuery,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("db_migration")


def backup_sqlite_database(sqlite_path: Path) -> Path:
    """Create a timestamped backup of the existing SQLite database file."""
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database file not found at: {sqlite_path}")

    backup_dir = sqlite_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{sqlite_path.stem}_backup_{timestamp}.db"

    shutil.copy2(sqlite_path, backup_path)
    logger.info("Created SQLite database backup at: %s", backup_path)
    return backup_path


def migrate_data(sqlite_path: Path, postgres_url: str):
    """Safely migrate all tables and records from SQLite to PostgreSQL within a transaction."""
    logger.info("Initiating SQLite -> PostgreSQL database migration...")
    logger.info("Source SQLite: %s", sqlite_path)
    logger.info("Target PostgreSQL: %s", postgres_url.split("@")[-1] if "@" in postgres_url else postgres_url)

    # 1. Back up SQLite database
    backup_sqlite_database(sqlite_path)

    # 2. Setup engines
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    
    # Normalize url scheme if necessary
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)

    pg_engine = create_engine(
        postgres_url,
        pool_pre_ping=True,
    )

    # 3. Create target schema on PostgreSQL
    logger.info("Creating tables on PostgreSQL if not present...")
    Base.metadata.create_all(bind=pg_engine)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    # 4. Migrate in foreign-key dependency order
    tables_to_migrate = [
        ("customers", Customer),
        ("chat_sessions", ChatSession),
        ("chat_messages", ChatMessage),
        ("sales_leads", SalesLead),
        ("support_tickets", SupportTicket),
        ("flagged_queries", FlaggedQuery),
    ]

    record_counts: Dict[str, int] = {}

    with SqliteSession() as src_db, PgSession() as dst_db:
        try:
            for table_name, model_cls in tables_to_migrate:
                src_records = src_db.execute(select(model_cls)).scalars().all()
                count = len(src_records)
                record_counts[table_name] = count
                logger.info("Found %d records in '%s'", count, table_name)

                for item in src_records:
                    # Detach from source session and merge into destination
                    src_db.expunge(item)
                    dst_db.merge(item)

                dst_db.flush()

            # Commit destination transaction
            dst_db.commit()
            logger.info("All records successfully committed to PostgreSQL!")

        except Exception as exc:
            dst_db.rollback()
            logger.error("Error during migration, transaction rolled back safely: %s", exc)
            raise

    # 5. Verification check
    logger.info("\n--- Verification Summary ---")
    with PgSession() as check_db:
        for table_name, model_cls in tables_to_migrate:
            pg_count = len(check_db.execute(select(model_cls)).scalars().all())
            expected = record_counts[table_name]
            status = "MATCH" if pg_count >= expected else "MISMATCH"
            logger.info("  [%s] %s: Expected %d, Found %d in PostgreSQL", status, table_name, expected, pg_count)

    logger.info("Migration completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Migrate NIEL SQLite data to PostgreSQL.")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=Path("data/niel_sessions.db"),
        help="Path to source SQLite database file",
    )
    parser.add_argument(
        "--postgres-url",
        type=str,
        default=None,
        help="Target PostgreSQL connection URL (defaults to DATABASE_URL in config/env)",
    )
    args = parser.parse_args()

    settings = get_settings()
    pg_url = args.postgres_url or settings.DATABASE_URL

    if not pg_url or pg_url.startswith("sqlite"):
        logger.error("Please supply a valid PostgreSQL DATABASE_URL via argument or environment variable.")
        sys.exit(1)

    migrate_data(args.sqlite_path, pg_url)


if __name__ == "__main__":
    main()
