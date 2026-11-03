"""Tests for unverified spec detection, passive logging, and engineering review API."""

import pytest
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.knowledge.knowledge_base import get_knowledge_base
from backend.app.main import app
from backend.app.services.flag_service import get_flag_service
from backend.app.services.rag_service import get_rag_service

client = TestClient(app)
settings = get_settings()


def test_detect_unverified_fields_in_knowledge_base():
    """Verify knowledge base identifies questions touching unverified product specifications."""
    kb = get_knowledge_base()

    # 1. Question touching efficiency curve on AC cage rotor
    matches = kb.detect_unverified_fields("What is the efficiency percentage per frame size for cage rotor motors?")
    assert len(matches) > 0
    assert any("efficiency" in m["unverified_field"].lower() for m in matches)
    assert any(m["product_category"] == "AC Motors" for m in matches)

    # 2. Question touching rotor current on AC wound rotor
    matches_rotor = kb.detect_unverified_fields("What is the rotor current rating for slipring wound rotor motors?")
    assert len(matches_rotor) > 0
    assert any("rotor current" in m["unverified_field"].lower() for m in matches_rotor)

    # 3. Question touching short-circuit withstand time on power transformers
    matches_trans = kb.detect_unverified_fields("What is the short circuit withstand time in seconds for power transformers?")
    assert len(matches_trans) > 0
    assert any("short-circuit" in m["unverified_field"].lower() or "withstand" in m["unverified_field"].lower() for m in matches_trans)

    # 4. Standard verified question should not flag any unverified fields
    no_matches = kb.detect_unverified_fields("What mounting types are available for foot mounted motors?")
    assert len(no_matches) == 0


def test_flag_service_crud():
    """Verify flag service can log, retrieve, and resolve unverified spec queries."""
    flag_svc = get_flag_service()

    # Log an entry
    logged = flag_svc.log_flagged_query(
        user_question="What are the efficiency values per frame size for cage rotor?",
        product_category="AC Motors",
        unverified_field="Efficiency percentage per frame size (IE2/IE3/IE4 values)",
        session_id="test-session-flag-1",
    )
    assert logged is not None
    assert logged.id is not None
    assert logged.resolved is False

    # List entries
    entries = flag_svc.list_flagged_queries(resolved=False)
    assert any(e.id == logged.id for e in entries)

    # Resolve entry
    resolved = flag_svc.resolve_flagged_query(flag_id=logged.id, resolved=True)
    assert resolved is not None
    assert resolved.resolved is True

    # Confirm filtered list reflects resolution
    unresolved_entries = flag_svc.list_flagged_queries(resolved=False)
    assert not any(e.id == logged.id for e in unresolved_entries)


def test_flagged_queries_api_admin_auth():
    """Verify admin security on GET and PATCH /api/v1/flagged-queries."""
    # 1. Missing header -> 401
    resp_no_auth = client.get("/api/v1/flagged-queries")
    assert resp_no_auth.status_code == 401

    # 2. Wrong header -> 403
    resp_wrong_auth = client.get(
        "/api/v1/flagged-queries",
        headers={"X-Admin-Key": "invalid-secret"},
    )
    assert resp_wrong_auth.status_code == 403

    # 3. Valid admin key -> 200
    resp_valid = client.get(
        "/api/v1/flagged-queries",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
    )
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert "total" in data
    assert "flagged_queries" in data


def test_flagged_queries_api_patch_resolution():
    """Verify engineering review PATCH endpoint marks entries resolved."""
    flag_svc = get_flag_service()
    logged = flag_svc.log_flagged_query(
        user_question="What is the short circuit withstand time in seconds for power transformers?",
        product_category="Transformers",
        unverified_field="Short-circuit withstand time in seconds",
    )
    assert logged is not None

    # PATCH to resolve
    patch_resp = client.patch(
        f"/api/v1/flagged-queries/{logged.id}",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
        json={"resolved": True},
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["id"] == logged.id
    assert patch_data["resolved"] is True

    # PATCH non-existent query -> 404
    patch_404 = client.patch(
        "/api/v1/flagged-queries/999999",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
        json={"resolved": True},
    )
    assert patch_404.status_code == 404


def test_passive_logging_in_rag_service():
    """Verify that asking an unverified spec question passively logs without modifying customer response."""
    rag = get_rag_service()
    flag_svc = get_flag_service()

    before_count = len(flag_svc.list_flagged_queries(limit=1000))

    # Customer asks about an unverified spec
    query = "What is the efficiency percentage per frame size for cage rotor motors?"
    resp = rag.answer_question(question=query)

    # Customer-facing response is normal and functional
    assert resp.answer is not None
    assert len(resp.answer) > 0

    # Passive log recorded
    after_entries = flag_svc.list_flagged_queries(limit=1000)
    assert len(after_entries) >= before_count + 1
    recent_entry = after_entries[0]
    assert recent_entry.user_question == query
    assert "efficiency" in recent_entry.unverified_field.lower()

