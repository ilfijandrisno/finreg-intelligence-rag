# Phase 10: Containerization, Operational Engineering & Deployment Readiness

## 1. Executive Summary

Phase 10 establishes a production-oriented container architecture, GitHub Actions CI pipeline, Prometheus metrics observability, and environment configuration controls for the FinReg Intelligence RAG platform.

---

## 2. Docker & Container Architecture

### Multi-Stage Production `Dockerfile`
- **Base Image**: `python:3.11-slim`
- **Builder Stage**: Installs OS compilation dependencies (`gcc`, `g++`, `libpq-dev`), builds Python virtual environment wheels in `/opt/venv`.
- **Runtime Stage**: Copies `/opt/venv`, installs runtime `libpq5` and `curl`, creates non-privileged user `appuser` (UID 10001), and executes `uvicorn finreg.api.main:app` as non-root.
- **HuggingFace Model Build Decoupling**: Docker build does **not** download model weights (`BAAI/bge-reranker-v2-m3`). Runtime model loading is governed by Phase 5 `CrossEncoderRerankerProvider`.
- **Container Health Check**: Probes `http://localhost:8000/health` using `curl`.

---

## 3. Local Docker Compose Scope

`docker-compose.yml` is explicitly scoped to:
1. **Local development environment**
2. **Local integration testing environment**
3. **Portfolio/demo environment**

Production cloud deployment (AWS ECS/Fargate, Kubernetes, Terraform, CloudFormation) is intentionally outside Phase 10 scope.

---

## 4. Observability & Prometheus Metrics (`GET /metrics`)

### Endpoint & Metrics Registry
- Prometheus text exposition format (version 0.0.4) exposed at `GET /metrics`.
- **Exposed Operational Metrics**:
  - `finreg_http_requests_total`: Counter by (`method`, `endpoint`, `status_code`).
  - `finreg_http_request_duration_seconds`: Histogram of latency by (`endpoint`).
  - `finreg_rag_executions_total`: Counter by (`abstained`).
  - `finreg_rag_execution_duration_seconds`: Histogram of RAG execution latency.

### High-Cardinality Safeguards
- **`request_id` is strictly excluded from Prometheus metric labels** to prevent memory inflation.
- Request tracing is preserved via `X-Request-ID` HTTP headers and structured JSON request logs.

---

## 5. Security & Safe Logging

- **Non-Root User**: Container executes as `appuser` (UID 10001).
- **Secrets Protection**: No API keys, passwords, or connection URLs baked into Docker image. `.env` excluded via `.dockerignore`.
- **Safe Request Logs**: Request logs exclude full user query texts, legal chunk contents, LLM prompts/responses, and authorization headers.
- **Traceback Isolation**: Unhandled exceptions return safe HTTP 500 JSON responses without leaking internal stack traces.

---

## 6. GitHub Actions CI Pipeline (`.github/workflows/ci.yml`)

The CI workflow executes on `push` and `pull_request` to `main`:
1. `ruff format --check .` (Code formatting validation)
2. `ruff check .` (Lint validation)
3. `mypy src` (Static type checking)
4. `pytest` (Offline test suite execution with `ENVIRONMENT=testing`)
5. `docker build -t finreg-api:ci .` (Docker image build validation)

---

## 7. Health & Readiness API Semantics

- **`GET /health`**: Liveness probe returning `HTTP 200` `{ "status": "ok", "service": "finreg-intelligence", "version": "0.1.0" }`.
- **`GET /readiness` (200)**: Database ready returning `HTTP 200` `{ "status": "ready", "database": "connected" }`.
- **`GET /readiness` (503)**: Database disconnected returning `HTTP 503` `ErrorResponse` `{ "error_code": "SERVICE_UNAVAILABLE", "message": "Database service unreachable or disconnected", "request_id": "<X-Request-ID>" }`.
