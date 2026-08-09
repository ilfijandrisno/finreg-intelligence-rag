"""API tests for /health (liveness) and /readiness probes."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from finreg.api.main import app

client = TestClient(app)


def test_get_health_liveness() -> None:
    """Verify GET /health returns HTTP 200 OK and X-Request-ID header."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "finreg-intelligence"
    assert "version" in data
    assert "X-Request-ID" in response.headers


def test_get_readiness_success() -> None:
    """Verify GET /readiness returns HTTP 200 OK when database is reachable."""
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "X-Request-ID" in response.headers


def test_get_readiness_database_failure() -> None:
    """Verify GET /readiness returns HTTP 503 Service Unavailable when database connection fails."""
    with patch("finreg.api.routers.health.get_engine") as mock_get_engine:
        mock_get_engine.side_effect = Exception("PostgreSQL connection refused")
        response = client.get("/readiness")

    assert response.status_code == 503
    data = response.json()
    assert data["error_code"] == "SERVICE_UNAVAILABLE"
    assert data["message"] == "Database service unreachable or disconnected"
    assert "request_id" in data
    assert "connection refused" not in data["message"].lower()
    assert "X-Request-ID" in response.headers
