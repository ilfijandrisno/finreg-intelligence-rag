# Fase 10: Kontainerisasi, Rekayasa Operasional & Kesiapan Deployment

**Bahasa:** 🇮🇩 Bahasa Indonesia · [🇬🇧 English](deployment-readiness.md)

## 1. Ringkasan Eksekutif

Fase 10 menetapkan arsitektur kontainer yang berorientasi produksi, pipeline CI GitHub Actions, observabilitas berbasis metrik Prometheus, dan kontrol konfigurasi lingkungan untuk platform FinReg Intelligence RAG.

---

## 2. Arsitektur Docker & Kontainer

### `Dockerfile` Produksi Multi-Stage
- **Base Image**: `python:3.11-slim`
- **Builder Stage**: memasang dependensi kompilasi OS (`gcc`, `g++`, `libpq-dev`) dan membangun wheel virtual environment Python di `/opt/venv`.
- **Runtime Stage**: menyalin `/opt/venv`, memasang `libpq5` dan `curl`, membuat user non-privileged `appuser` (UID 10001), lalu menjalankan `uvicorn finreg.api.main:app` sebagai non-root.
- **Pemisahan Build Model HuggingFace**: proses Docker build **tidak** mengunduh bobot model (`BAAI/bge-reranker-v2-m3`). Pemuatan model saat runtime dikendalikan oleh `CrossEncoderRerankerProvider` pada Fase 5.
- **Health Check Kontainer**: melakukan probe ke `http://localhost:8000/health` menggunakan `curl`.

---

## 3. Cakupan Docker Compose Lokal

`docker-compose.yml` secara eksplisit dibatasi untuk:
1. **Lingkungan pengembangan lokal**
2. **Lingkungan pengujian integrasi lokal**
3. **Lingkungan portfolio/demo**

Deployment cloud produksi (AWS ECS/Fargate, Kubernetes, Terraform, CloudFormation) sengaja berada di luar cakupan Fase 10.

---

## 4. Observabilitas & Metrik Prometheus (`GET /metrics`)

### Endpoint & Registry Metrik
- Format eksposisi teks Prometheus (versi 0.0.4) tersedia pada `GET /metrics`.
- **Metrik operasional yang diekspos**:
  - `finreg_http_requests_total`: Counter berdasarkan (`method`, `endpoint`, `status_code`).
  - `finreg_http_request_duration_seconds`: Histogram latency berdasarkan (`endpoint`).
  - `finreg_rag_executions_total`: Counter berdasarkan (`abstained`).
  - `finreg_rag_execution_duration_seconds`: Histogram latency eksekusi RAG.

### Perlindungan terhadap High Cardinality
- **`request_id` tidak dimasukkan ke label metrik Prometheus** untuk mencegah pembengkakan penggunaan memori.
- Request tracing tetap tersedia melalui HTTP header `X-Request-ID` dan structured JSON request logs.

---

## 5. Keamanan & Logging Aman

- **Non-Root User**: kontainer berjalan sebagai `appuser` (UID 10001).
- **Perlindungan Secrets**: tidak ada API key, password, atau connection URL yang ditanam ke Docker image. `.env` dikecualikan melalui `.dockerignore`.
- **Request Log Aman**: log tidak menyimpan teks query user lengkap, isi legal chunk, prompt/response LLM, maupun authorization header.
- **Isolasi Traceback**: exception yang tidak tertangani menghasilkan response JSON HTTP 500 yang aman tanpa membocorkan stack trace internal.

---

## 6. Pipeline GitHub Actions CI (`.github/workflows/ci.yml`)

Workflow CI berjalan pada `push` dan `pull_request` ke `main`:
1. `ruff format --check .` (validasi formatting kode)
2. `ruff check .` (validasi lint)
3. `mypy src` (static type checking)
4. `pytest` (eksekusi offline test suite dengan `ENVIRONMENT=testing`)
5. `docker build -t finreg-api:ci .` (validasi proses build Docker image)

---

## 7. Semantik API Health & Readiness

- **`GET /health`**: liveness probe yang mengembalikan `HTTP 200` `{ "status": "ok", "service": "finreg-intelligence", "version": "0.1.0" }`.
- **`GET /readiness` (200)**: database siap dan mengembalikan `HTTP 200` `{ "status": "ready", "database": "connected" }`.
- **`GET /readiness` (503)**: database terputus dan mengembalikan `HTTP 503` `ErrorResponse` `{ "error_code": "SERVICE_UNAVAILABLE", "message": "Database service unreachable or disconnected", "request_id": "<X-Request-ID>" }`.
