"""Lightweight, thread-safe Prometheus metrics registry and HTTP metrics middleware."""

import time
from collections import defaultdict
from threading import Lock
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Key type for metrics registry: (metric_name, tuple_of_label_kv_pairs)
MetricKey = tuple[str, tuple[tuple[str, str], ...]]


class PrometheusMetricsRegistry:
    """Thread-safe Prometheus-compatible metrics registry."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[MetricKey, int] = defaultdict(int)
        self._histograms: dict[MetricKey, list[float]] = defaultdict(list)

    def inc_counter(self, name: str, labels: dict[str, str] | None = None) -> None:
        """Increment counter metric."""
        label_tuple: tuple[tuple[str, str], ...] = tuple(sorted(labels.items())) if labels else ()
        key: MetricKey = (name, label_tuple)
        with self._lock:
            self._counters[key] += 1

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record histogram value observation."""
        label_tuple: tuple[tuple[str, str], ...] = tuple(sorted(labels.items())) if labels else ()
        key: MetricKey = (name, label_tuple)
        with self._lock:
            self._histograms[key].append(value)

    def generate_prometheus_text(self) -> str:
        """Render metrics in standard Prometheus text exposition format (version 0.0.4)."""
        lines: list[str] = []

        with self._lock:
            # 1. HTTP Requests Total Counter
            lines.append(
                "# HELP finreg_http_requests_total Total count of HTTP requests processed."
            )
            lines.append("# TYPE finreg_http_requests_total counter")
            http_counters = [
                (key, count)
                for key, count in self._counters.items()
                if key[0] == "finreg_http_requests_total"
            ]
            if not http_counters:
                lines.append(
                    'finreg_http_requests_total{endpoint="none",method="none",status_code="0"} 0'
                )
            for (_name, label_tuple), count in sorted(http_counters, key=lambda x: x[0][1]):
                lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                lines.append(f"finreg_http_requests_total{{{lbl_str}}} {count}")

            # 2. HTTP Request Duration Histogram
            lines.append(
                "# HELP finreg_http_request_duration_seconds HTTP request latency in seconds."
            )
            lines.append("# TYPE finreg_http_request_duration_seconds summary")
            http_hists = [
                (key, values)
                for key, values in self._histograms.items()
                if key[0] == "finreg_http_request_duration_seconds"
            ]
            if not http_hists:
                lines.append('finreg_http_request_duration_seconds_sum{endpoint="none"} 0.0')
                lines.append('finreg_http_request_duration_seconds_count{endpoint="none"} 0')
            for (_name, label_tuple), values in sorted(http_hists, key=lambda x: x[0][1]):
                lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                v_sum = sum(values)
                v_count = len(values)
                lines.append(f"finreg_http_request_duration_seconds_sum{{{lbl_str}}} {v_sum:.6f}")
                lines.append(f"finreg_http_request_duration_seconds_count{{{lbl_str}}} {v_count}")

            # 3. RAG Executions Total Counter
            lines.append(
                "# HELP finreg_rag_executions_total Total count of RAG pipeline executions."
            )
            lines.append("# TYPE finreg_rag_executions_total counter")
            rag_counters = [
                (key, count)
                for key, count in self._counters.items()
                if key[0] == "finreg_rag_executions_total"
            ]
            if not rag_counters:
                lines.append('finreg_rag_executions_total{abstained="false"} 0')
            for (_name, label_tuple), count in sorted(rag_counters, key=lambda x: x[0][1]):
                lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                lines.append(f"finreg_rag_executions_total{{{lbl_str}}} {count}")

            # 4. RAG Execution Duration Histogram
            lines.append(
                "# HELP finreg_rag_execution_duration_seconds RAG execution latency in seconds."
            )
            lines.append("# TYPE finreg_rag_execution_duration_seconds summary")
            rag_hists = [
                (key, values)
                for key, values in self._histograms.items()
                if key[0] == "finreg_rag_execution_duration_seconds"
            ]
            if not rag_hists:
                lines.append("finreg_rag_execution_duration_seconds_sum 0.0")
                lines.append("finreg_rag_execution_duration_seconds_count 0")
            for (_name, label_tuple), values in sorted(rag_hists, key=lambda x: x[0][1]):
                lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                lbl_fmt = f"{{{lbl_str}}}" if lbl_str else ""
                v_sum = sum(values)
                v_count = len(values)
                lines.append(f"finreg_rag_execution_duration_seconds_sum{lbl_fmt} {v_sum:.6f}")
                lines.append(f"finreg_rag_execution_duration_seconds_count{lbl_fmt} {v_count}")

        return "\n".join(lines) + "\n"


# System-wide metrics registry singleton
metrics_registry = PrometheusMetricsRegistry()


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware capturing HTTP request metrics with bounded label cardinality."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time

        # Bounded endpoint template (e.g. '/api/v1/rag/generate')
        route: Any = request.scope.get("endpoint")
        endpoint = request.url.path
        if route and hasattr(route, "__name__"):
            endpoint = request.url.path

        # Strictly bounded labels: method, endpoint, status_code (No request_id or user queries!)
        labels = {
            "method": request.method,
            "endpoint": endpoint,
            "status_code": str(response.status_code),
        }

        metrics_registry.inc_counter("finreg_http_requests_total", labels)
        metrics_registry.observe_histogram(
            "finreg_http_request_duration_seconds",
            duration,
            labels={"endpoint": endpoint},
        )

        return response
