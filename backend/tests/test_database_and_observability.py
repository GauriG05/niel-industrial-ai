"""Automated tests for database resilience, PostgreSQL support, Alembic readiness, and observability."""

import logging
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from backend.app.config import get_settings
from backend.app.db.models import Base, Customer, ChatSession, ChatMessage, SalesLead, SupportTicket
from backend.app.db.session import check_db_health, transaction_scope, get_db
from backend.app.main import app
from backend.app.observability.logging_config import StructuredJsonFormatter, redact_sensitive_text
from backend.app.observability.metrics import get_metrics_collector
from backend.app.observability.tracing import trace_span
from scripts.migrate_sqlite_to_postgres import backup_sqlite_database, migrate_data


def test_db_health_check():
    """Verify database connectivity healthcheck executes cleanly."""
    assert check_db_health() is True


def test_transaction_scope_commit_and_rollback():
    """Verify transaction_scope commits on success and rolls back on exception."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Success case
    with transaction_scope(session):
        cust = Customer(id="cust-tx-1", name="Alpha Corp")
        session.add(cust)

    found = session.execute(select(Customer).filter_by(id="cust-tx-1")).scalar_one_or_none()
    assert found is not None
    assert found.name == "Alpha Corp"

    # Rollback case
    with pytest.raises(RuntimeError):
        with transaction_scope(session):
            cust2 = Customer(id="cust-tx-2", name="Beta Corp")
            session.add(cust2)
            raise RuntimeError("Simulated transaction failure")

    rolled_back = session.execute(select(Customer).filter_by(id="cust-tx-2")).scalar_one_or_none()
    assert rolled_back is None


def test_sqlite_backup_creation(tmp_path):
    """Verify sqlite backup creates timestamped copy in backups directory."""
    db_file = tmp_path / "test_sessions.db"
    db_file.write_text("dummy database content", encoding="utf-8")

    backup_file = backup_sqlite_database(db_file)
    assert backup_file.exists()
    assert backup_file.parent.name == "backups"
    assert backup_file.read_text(encoding="utf-8") == "dummy database content"


def test_sqlite_to_postgres_migration_flow(tmp_path):
    """Verify migration process safely copies records from SQLite to target DB."""
    # Source SQLite DB
    src_db_file = tmp_path / "source.db"
    src_engine = create_engine(f"sqlite:///{src_db_file}")
    Base.metadata.create_all(bind=src_engine)
    SrcSession = sessionmaker(bind=src_engine)

    with SrcSession() as src_sess:
        c = Customer(id="CUST-MIG-1", name="Steel Dynamics", email="procure@steeldynamics.com")
        s = ChatSession(id="SESS-MIG-1", customer_id="CUST-MIG-1")
        m = ChatMessage(session_id="SESS-MIG-1", role="user", content="Need 200kW motor")
        lead = SalesLead(customer_id="CUST-MIG-1", session_id="SESS-MIG-1", product_interest="AC Motors")
        ticket = SupportTicket(id="TK-MIG-1", customer_id="CUST-MIG-1", product_category="Motors", issue_description="Vibration")
        src_sess.add_all([c, s, m, lead, ticket])
        src_sess.commit()

    # Destination DB (using SQLite in-memory / separate file to simulate destination)
    dst_db_file = tmp_path / "target.db"
    dst_url = f"sqlite:///{dst_db_file}"

    migrate_data(src_db_file, dst_url)

    # Verify target has all migrated records
    dst_engine = create_engine(dst_url)
    DstSession = sessionmaker(bind=dst_engine)
    with DstSession() as dst_sess:
        assert dst_sess.execute(select(Customer).filter_by(id="CUST-MIG-1")).scalar_one_or_none() is not None
        assert dst_sess.execute(select(ChatSession).filter_by(id="SESS-MIG-1")).scalar_one_or_none() is not None
        assert dst_sess.execute(select(ChatMessage).filter_by(content="Need 200kW motor")).scalar_one_or_none() is not None
        assert dst_sess.execute(select(SalesLead).filter_by(product_interest="AC Motors")).scalar_one_or_none() is not None
        assert dst_sess.execute(select(SupportTicket).filter_by(id="TK-MIG-1")).scalar_one_or_none() is not None


def test_health_endpoint():
    """Verify /health returns detailed status of database and cache."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "database" in data
    assert "redis_cache" in data
    assert "environment" in data


def test_prometheus_metrics_endpoint():
    """Verify /metrics returns Prometheus formatted plaintext metrics."""
    client = TestClient(app)
    # Trigger a request to record metrics
    client.get("/")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "niel_http_requests_total" in body
    assert "niel_human_escalations_total" in body
    assert "niel_rag_abstentions_total" in body
    assert "niel_security_blocked_attempts_total" in body


def test_observability_middleware_request_id():
    """Verify X-Request-ID header is propagated and populated."""
    client = TestClient(app)
    # 1. Custom request ID
    custom_id = "test-req-id-12345"
    resp = client.get("/", headers={"x-request-id": custom_id})
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == custom_id

    # 2. Generated request ID when omitted
    resp2 = client.get("/")
    assert resp2.status_code == 200
    assert resp2.headers.get("x-request-id") is not None


def test_structured_json_logger_redaction():
    """Verify structured logger redacts emails, phones, and API keys."""
    text_with_secrets = (
        "Customer john.doe@example.com called +91 9845012345 with api_key=sk-secret123456789 and Bearer token1234567890."
    )
    redacted = redact_sensitive_text(text_with_secrets)
    assert "john.doe@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "9845012345" not in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "sk-secret123456789" not in redacted
    assert "token1234567890" not in redacted


def test_tracing_span_records_duration():
    """Verify trace_span measures duration and records to metrics collector."""
    metrics = get_metrics_collector()
    with trace_span("rag_retrieval") as span:
        # Simulate some minor work
        sum(i for i in range(1000))

    assert "duration_sec" in span
    assert span["duration_sec"] > 0
    # Prometheus metrics collector recorded retrieval
    assert len(metrics._rag_retrieval_durations) > 0

