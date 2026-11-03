"""Security hardening tests: Admin auth, session tokens, WebSocket security, CSP, and rate limiting."""

import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import Settings
from backend.app.security.tokens import (
    create_session_token,
    verify_session_token,
    validate_session_token_for_session,
    TokenExpiredError,
    TokenInvalidError,
)
from backend.app.security.rate_limiter import DistributedRateLimiter

client = TestClient(app)


def test_production_fails_with_default_admin_key():
    """Verify application startup fails in production if ADMIN_API_KEY is an insecure default."""
    with pytest.raises(ValueError, match="CRITICAL SECURITY FAILURE.*ADMIN_API_KEY"):
        Settings(
            ENVIRONMENT="production",
            ADMIN_API_KEY="dev-admin-key",
            SECRET_KEY="a" * 32,
            OPENAI_API_KEY="sk-valid-production-key-for-test",
            DEBUG=False,
        )


def test_production_fails_with_short_admin_key():
    """Verify application startup fails in production if ADMIN_API_KEY is under 32 characters."""
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            ENVIRONMENT="production",
            ADMIN_API_KEY="short-key-1234",
            SECRET_KEY="b" * 32,
            OPENAI_API_KEY="sk-valid-production-key-for-test",
            DEBUG=False,
        )


def test_production_fails_with_insecure_secret_key():
    """Verify application startup fails in production if SECRET_KEY is default or too short."""
    with pytest.raises(ValueError, match="CRITICAL SECURITY FAILURE.*SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            ADMIN_API_KEY="a" * 32,
            SECRET_KEY="dev-session-secret-key-do-not-use-in-production-32b",
            OPENAI_API_KEY="sk-valid-production-key-for-test",
            DEBUG=False,
        )


def test_production_fails_with_debug_true():
    """Verify application startup fails in production if DEBUG=True."""
    with pytest.raises(ValueError, match="DEBUG mode must be disabled"):
        Settings(
            ENVIRONMENT="production",
            ADMIN_API_KEY="a" * 32,
            SECRET_KEY="b" * 32,
            OPENAI_API_KEY="sk-valid-production-key-for-test",
            DEBUG=True,
        )


def test_production_succeeds_with_secure_configuration():
    """Verify Settings initializes cleanly when all production secrets meet security requirements."""
    cfg = Settings(
        ENVIRONMENT="production",
        ADMIN_API_KEY="niel-prod-admin-super-secure-key-998877",
        SECRET_KEY="niel-prod-session-signing-secret-key-334455",
        OPENAI_API_KEY="sk-valid-mock-production-key-12345678",
        DEBUG=False,
    )
    assert cfg.ENVIRONMENT == "production"
    assert "niel-prod-admin" not in repr(cfg)  # Never expose secrets in repr
    assert "***" in repr(cfg)


def test_admin_auth_timing_safe_and_rejection():
    """Verify admin endpoints reject missing and wrong admin credentials."""
    # Missing header
    res_missing = client.get("/api/v1/customers")
    assert res_missing.status_code == 401

    # Invalid header
    res_wrong = client.get("/api/v1/customers", headers={"X-Admin-Key": "completely-wrong-key"})
    assert res_wrong.status_code == 403


def test_session_token_lifecycle():
    """Verify HMAC session token creation, verification, and expiration."""
    sid = "test-session-uuid-123"
    cid = "test-customer-uuid-456"

    # 1. Valid token
    token = create_session_token(session_id=sid, customer_id=cid, ttl_seconds=60)
    payload = verify_session_token(token)
    assert payload["sid"] == sid
    assert payload["cid"] == cid
    assert payload["exp"] > time.time()

    # 2. Token bound to session
    valid_payload = validate_session_token_for_session(token, expected_session_id=sid)
    assert valid_payload["sid"] == sid

    # 3. Token mismatch for different session
    with pytest.raises(TokenInvalidError, match="authorization mismatch"):
        validate_session_token_for_session(token, expected_session_id="different-session-id")

    # 4. Tampered signature rejected
    tampered = token[:-4] + "xxxx"
    with pytest.raises(TokenInvalidError, match="signature verification failed"):
        verify_session_token(tampered)

    # 5. Expired token rejected
    expired_token = create_session_token(session_id=sid, customer_id=cid, ttl_seconds=-5)
    with pytest.raises(TokenExpiredError, match="expired"):
        verify_session_token(expired_token)


def test_session_token_endpoint():
    """Verify POST /api/v1/sessions/token returns a signed token."""
    res = client.post("/api/v1/sessions/token", json={"session_id": "cust-session-789"})
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == "cust-session-789"
    assert "token" in data
    assert data["expires_at"] > time.time()

    # Verify the issued token is cryptographically valid
    payload = verify_session_token(data["token"])
    assert payload["sid"] == "cust-session-789"


def test_security_headers():
    """Verify tightened CSP, strict Permissions-Policy, and absence of obsolete headers."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200

    csp = res.headers.get("Content-Security-Policy", "")
    assert "'unsafe-eval'" not in csp
    assert "default-src 'self'" in csp

    perms = res.headers.get("Permissions-Policy", "")
    assert "camera=()" in perms
    assert "microphone=()" in perms
    assert "geolocation=()" in perms
    assert "payment=()" in perms
    assert "*" not in perms  # No wildcard permissions

    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "X-XSS-Protection" not in res.headers  # Obsolete header removed


def test_rate_limiter_in_memory_fallback():
    """Verify sliding window rate limiter blocks requests exceeding quota."""
    limiter = DistributedRateLimiter()

    class DummyRequest:
        class Client:
            host = "192.168.10.99"
        client = Client()

    req = DummyRequest()

    # First 3 requests with limit=3 should pass
    for _ in range(3):
        assert limiter._check_memory("rl:test:192.168.10.99", limit=3, window=60.0) is True

    # 4th request must be blocked
    assert limiter._check_memory("rl:test:192.168.10.99", limit=3, window=60.0) is False


def test_websocket_rejects_unauthorized_origin():
    """Verify WebSocket handshake closes immediately when origin is unauthorized."""
    with pytest.raises(Exception):
        with client.websocket_connect(
            "/ws/chat/test-sess",
            headers={"Origin": "https://malicious-attacker-site.com"},
        ) as ws:
            pass


def test_websocket_rejects_invalid_token():
    """Verify WebSocket rejects connection with invalid/tampered token."""
    with pytest.raises(Exception):
        with client.websocket_connect(
            "/ws/chat/test-sess?token=invalid.tampered.token",
        ) as ws:
            pass


def test_websocket_connects_with_valid_token():
    """Verify WebSocket handshake succeeds with a valid signed session token."""
    sid = "ws-valid-sess-101"
    token = create_session_token(session_id=sid, ttl_seconds=60)

    with client.websocket_connect(
        f"/ws/chat/{sid}?token={token}",
        headers={"Origin": "http://localhost:5173"},
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "session_init"
        assert msg["session_id"] == sid


def test_websocket_rejects_unauthorized_privileged_action():
    """Verify WebSocket rejects admin action 'resolve' when attempted without admin key."""
    sid = "ws-action-sess-202"
    token = create_session_token(session_id=sid, ttl_seconds=60)

    with client.websocket_connect(
        f"/ws/chat/{sid}?token={token}",
        headers={"Origin": "http://localhost:5173"},
    ) as ws:
        # Initial handshake
        ws.receive_json()

        # Send unauthorized resolve action
        ws.send_json({"action": "resolve"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "Administrative key required" in err["detail"]
