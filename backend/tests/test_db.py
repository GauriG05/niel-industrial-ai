"""Unit tests for SQLite database persistence (ChatSession and ChatMessage)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.models import Base, ChatSession, ChatMessage


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for test runs."""
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def test_create_session_and_add_messages(db_session):
    """Test creating a chat session, persisting user/assistant turns, and retrieving them."""
    # 1. Create a new session
    session_id = "test-session-1234"
    chat_session = ChatSession(id=session_id, human_active=False)
    db_session.add(chat_session)
    db_session.commit()

    # Verify session was persisted
    fetched_session = db_session.query(ChatSession).filter_by(id=session_id).first()
    assert fetched_session is not None
    assert fetched_session.id == session_id
    assert fetched_session.human_active is False
    assert fetched_session.escalated_at is None

    # 2. Add user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content="What power ratings are documented for NIEL motors?",
        request_id="req-user-1",
    )
    db_session.add(user_msg)
    db_session.commit()

    # 3. Add assistant message with citations
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content="0.75 kW to 315 kW in IE3 Premium Efficiency.",
        citations_json='[{"source_filename": "NIEL_Industrial_Motors_Catalogue_2026.pdf", "page_number": 1}]',
        request_id="req-asst-1",
    )
    db_session.add(assistant_msg)
    db_session.commit()

    # 4. Read back messages and verify ordering & relationship
    db_session.refresh(chat_session)
    assert len(chat_session.messages) == 2
    assert chat_session.messages[0].role == "user"
    assert chat_session.messages[0].content == "What power ratings are documented for NIEL motors?"
    assert chat_session.messages[1].role == "assistant"
    assert "0.75 kW to 315 kW" in chat_session.messages[1].content
    assert "NIEL_Industrial_Motors_Catalogue_2026.pdf" in chat_session.messages[1].citations_json


def test_session_escalation_status(db_session):
    """Test updating session human_active status and escalated_at timestamp."""
    from datetime import datetime, timezone
    session_id = "test-session-escalation"
    chat_session = ChatSession(id=session_id, human_active=False)
    db_session.add(chat_session)
    db_session.commit()

    now = datetime.now(timezone.utc)
    chat_session.human_active = True
    chat_session.escalated_at = now
    db_session.commit()

    updated = db_session.query(ChatSession).filter_by(id=session_id).first()
    assert updated.human_active is True
    assert updated.escalated_at is not None
