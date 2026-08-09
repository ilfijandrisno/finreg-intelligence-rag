# FinReg Intelligence RAG: Panduan Setup, Eksekusi & Pengujian Developer

**Bahasa:** 🇮🇩 Bahasa Indonesia · [🇬🇧 English](development.md)

## 1. Prasyarat Lingkungan Lokal

- **Python**: 3.11 atau lebih tinggi
- **PostgreSQL**: 16+ dengan extension `pgvector` aktif
- **Docker**: Docker Desktop (untuk PostgreSQL + pgvector dalam container)

---

## 2. Quickstart Step-by-Step

### 1. Setup Repository & Virtual Environment
```bash
git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
cd finreg-intelligence-rag
python -m venv .venv
# Pada Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Pada Linux/macOS:
source .venv/bin/activate
pip install -e .[dev]
```

### 2. Jalankan PostgreSQL Container melalui Docker
```bash
docker-compose up -d
```

### 3. Konfigurasi Environment Variables
Salin `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```

### 4. Jalankan Database Schema Migrations
```bash
alembic upgrade head
```

---

## 3. Menjalankan API & Ingestion Pipeline

### 1. Ingest Regulasi PDF
```bash
python -m finreg.documents.cli ingest data/sample_pbi.pdf --source BI --type PBI --number 20/2026
```

### 2. Jalankan FastAPI Server
```bash
uvicorn finreg.api.main:app --reload --host 0.0.0.0 --port 8000
```
- Interactive Swagger API Docs: `http://localhost:8000/docs`
- Health Check: `curl http://localhost:8000/health`
- Readiness Check: `curl http://localhost:8000/readiness`

---

## 4. Menjalankan Test & Offline Benchmark CLI

### 1. Jalankan Pytest Suite Lengkap
```bash
pytest
```

### 2. Jalankan Offline Benchmark CLI
```bash
python -m finreg.evaluation.cli \
  --dataset-path data/evaluation/benchmark_gold_dataset.json \
  --output-dir data/evaluation/reports
```
Report akan disimpan di:
- `data/evaluation/reports/benchmark_report.json`
- `data/evaluation/reports/benchmark_report.md`
