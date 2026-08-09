# FinReg Intelligence RAG: Developer Setup, Execution & Testing Guide

## 1. Local Environment Prerequisites

- **Python**: 3.11 or higher
- **PostgreSQL**: 16+ with `pgvector` extension enabled
- **Docker**: Docker Desktop (for containerized PostgreSQL + pgvector)

---

## 2. Quickstart Step-by-Step

### 1. Repository Setup & Virtual Environment
```bash
git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
cd finreg-intelligence-rag
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate
pip install -e .[dev]
```

### 2. Launch PostgreSQL Container via Docker
```bash
docker-compose up -d
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 4. Run Database Schema Migrations
```bash
alembic upgrade head
```

---

## 3. Running API & Ingestion Pipelines

### 1. Ingest PDF Regulations
```bash
python -m finreg.documents.cli ingest data/sample_pbi.pdf --source BI --type PBI --number 20/2026
```

### 2. Start FastAPI Server
```bash
uvicorn finreg.api.main:app --reload --host 0.0.0.0 --port 8000
```
- Interactive Swagger API Docs: `http://localhost:8000/docs`
- Health Check: `curl http://localhost:8000/health`
- Readiness Check: `curl http://localhost:8000/readiness`

---

## 4. Running Tests & Offline Benchmark CLI

### 1. Run Complete Pytest Suite
```bash
pytest
```

### 2. Run Offline Benchmark CLI
```bash
python -m finreg.evaluation.cli \
  --dataset-path data/evaluation/benchmark_gold_dataset.json \
  --output-dir data/evaluation/reports
```
Reports will be saved to:
- `data/evaluation/reports/benchmark_report.json`
- `data/evaluation/reports/benchmark_report.md`
