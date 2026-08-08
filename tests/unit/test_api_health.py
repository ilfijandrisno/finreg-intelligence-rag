"""Unit tests for FastAPI health endpoint."""

from fastapi.testclient import TestClient

from finreg.api.main import app

client = TestClient(app)


def test_get_health_endpoint() -> None:
    """Verify GET /health returns expected structured health JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "ok",
        "service": "finreg-intelligence",
        "version": "0.1.0",
    }
