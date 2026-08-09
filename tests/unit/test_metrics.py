"""Unit tests for Phase 10 observability metrics and health/readiness contracts."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from finreg.api.main import app
from finreg.config.settings import Settings
from finreg.observability.metrics import metrics_registry

client = TestClient(app)


def test_get_metrics_endpoint_format() -> None:
    """Test GET /metrics returns HTTP 200 with valid Prometheus text exposition."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

    content = response.text
    assert "# HELP finreg_http_requests_total" in content
    assert "# TYPE finreg_http_requests_total counter" in content
    assert "# HELP finreg_http_request_duration_seconds" in content
    assert "# TYPE finreg_http_request_duration_seconds summary" in content


def test_metrics_counter_and_duration_increment() -> None:
    """Test HTTP requests increment metrics counters and record durations."""
    res = client.get("/health")
    assert res.status_code == 200

    metrics_text = client.get("/metrics").text
    assert (
        'finreg_http_requests_total{endpoint="/health",method="GET",status_code="200"}'
        in metrics_text
    )
    assert 'finreg_http_request_duration_seconds_count{endpoint="/health"}' in metrics_text


def test_no_high_cardinality_metric_labels() -> None:
    """Test that request_id, user queries, document_ids, and chunk_ids are excluded."""
    req_id = "test-unique-request-id-12345"
    response = client.get("/health", headers={"X-Request-ID": req_id})
    assert response.headers["X-Request-ID"] == req_id

    metrics_text = client.get("/metrics").text

    assert f'request_id="{req_id}"' not in metrics_text
    assert 'query="' not in metrics_text
    assert 'document_id="' not in metrics_text
    assert 'chunk_id="' not in metrics_text


def test_rag_metrics_recording() -> None:
    """Test RAG execution metrics recording."""
    metrics_registry.inc_counter("finreg_rag_executions_total", {"abstained": "false"})
    metrics_registry.observe_histogram("finreg_rag_execution_duration_seconds", 0.123)

    metrics_text = client.get("/metrics").text
    assert 'finreg_rag_executions_total{abstained="false"}' in metrics_text
    assert "finreg_rag_execution_duration_seconds_count" in metrics_text


def test_phase7_health_contract_preservation() -> None:
    """Test GET /health preserves exact Phase 7 API contract."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "finreg-intelligence"
    assert "version" in data


def test_phase7_readiness_200_contract_preservation() -> None:
    """Test GET /readiness preserves Phase 7 HTTP 200 ready response contract."""
    with patch("finreg.api.routers.health.get_engine") as mock_get_engine:
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine

        response = client.get("/readiness")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


def test_phase7_readiness_503_error_response_contract_preservation() -> None:
    """Test GET /readiness preserves Phase 7 HTTP 503 ErrorResponse contract."""
    with patch("finreg.api.routers.health.get_engine") as mock_get_engine:
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Database connection timeout")
        mock_get_engine.return_value = mock_engine

        req_id = "test-503-readiness-req-id"
        response = client.get("/readiness", headers={"X-Request-ID": req_id})
        assert response.status_code == 503
        assert response.headers["X-Request-ID"] == req_id

        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert data["message"] == "Database service unreachable or disconnected"
        assert data["request_id"] == req_id


def test_x_request_id_propagation() -> None:
    """Test X-Request-ID propagation across endpoints."""
    custom_id = "custom-trace-id-9999"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


def test_production_settings_fail_fast() -> None:
    """Test Settings raises ValueError in production if required API keys are missing."""
    with pytest.raises(ValueError, match="llm_api_key is required"):
        Settings(environment="production", llm_api_key=None, embedding_api_key=None)
