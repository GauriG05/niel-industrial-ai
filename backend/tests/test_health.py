"""Unit tests for health and basic service discovery endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify service discovery root returns expected metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "NIEL Industrial Intelligence AI"
    assert data["status"] == "operational"
    assert "version" in data


def test_health_endpoint():
    """Verify /api/v1/health returns healthy status and environment."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "kill_switch_active" in data


def test_ready_endpoint():
    """Verify /api/v1/ready returns readiness state."""
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ready", "initializing"]


def test_security_headers_present():
    """Verify standard protective headers are applied by middleware."""
    response = client.get("/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "strict-origin" in response.headers.get("Referrer-Policy", "")
    assert "frame-ancestors" in response.headers.get("Content-Security-Policy", "")


def test_widget_static_mounting():
    """Verify embeddable widget static file is served directly at /widget/niel-widget.js."""
    response = client.get("/widget/niel-widget.js")
    assert response.status_code == 200
    assert "text/javascript" in response.headers.get("content-type", "")
    assert "NIEL Industrial Intelligence AI" in response.text


