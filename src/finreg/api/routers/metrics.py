"""Prometheus metrics endpoint router."""

from fastapi import APIRouter, Response

from finreg.observability.metrics import metrics_registry

router = APIRouter(tags=["Observability"])


@router.get(
    "/metrics",
    summary="Prometheus Metrics Exposition Endpoint",
    response_class=Response,
)
def get_metrics() -> Response:
    """Expose Prometheus-formatted text operational metrics.

    Returns:
        Response: Plaintext Prometheus metrics payload (version 0.0.4).
    """
    content = metrics_registry.generate_prometheus_text()
    return Response(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
