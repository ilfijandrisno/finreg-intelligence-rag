# FinReg Intelligence RAG: Panduan Pengembang & Instalasi Lokal

## 1. Prasyarat Lingkungan Lokal

- **Python**: 3.11+
- **PostgreSQL**: 16+ dengan ekstensi `pgvector`
- **Docker**: Docker Desktop

---

## 2. Langkah Instalasi

```bash
# Kloning Repositori
git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
cd finreg-intelligence-rag

# Jalankan Container PostgreSQL & pgvector
docker-compose up -d

# Migrasi Basis Data
alembic upgrade head

# Jalankan Pengujian
pytest

# Jalankan Benchmark CLI
python -m finreg.evaluation.cli --dataset-path data/evaluation/benchmark_gold_dataset.json --output-dir data/evaluation/reports
```
