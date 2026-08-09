# FinReg Intelligence RAG: Platform RAG Peraturan Keuangan Indonesia

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16+](https://img.shields.io/badge/PostgreSQL-16%2B%20%7C%20pgvector-blue)](https://github.com/pgvector/pgvector)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20API-green.svg)](https://fastapi.tiangolo.com/)

Platform Retrieval-Augmented Generation (RAG) tingkat produksi yang dirancang khusus untuk menganalisis dan menjawab kueri peraturan keuangan Indonesia dari **Bank Indonesia (BI)** dan **Otoritas Jasa Keuangan (OJK)**.

Sistem ini menggabungkan **parser hirarki hukum berbasis state-machine**, **pencarian hibrida HNSW vector + BM25 lexical**, **neural cross-encoder reranking**, dan **penjawab berbasis bukti hukum dengan validasi sitasi deterministik dan penghentian otomatis (abstention)**.

---

## 🌟 Keunggulan Rekayasa Sistem

1. **Parser Hirarki Hukum Kontekstual**:
   - Parser struktur hukum berbasis *state-machine* yang mengekstrak hirarki peraturan (`BAB`, `Pasal`, `Ayat`, `Huruf`, `Angka`) secara deterministik.
2. **Pencarian Hibrida Multi-Tahap (RRF $k=60$)**:
   - Menggabungkan indeks vektor `pgvector` HNSW (1536 dimensi) dan pencarian teks lengkap BM25 `tsvector` bahasa Indonesia menggunakan Reciprocal Rank Fusion.
3. **Pemeringkatan Ulang Neural (Cross-Encoder)**:
   - Integrasi model Cross-Encoder (`BAAI/bge-reranker-v2-m3`) dari HuggingFace untuk menyaring presisi semantik kandidat sebelum pembuatan konteks LLM.
4. **Validasi Sitasi Deterministik & Garansi Abstain**:
   - Evaluasi sitasi inline `[C1]` berbasis regex deterministik dan penghentian jawaban otomatis jika skor relevansi berada di bawah ambang batas (0.30).
5. **Layanan REST API FastAPI**:
   - Dilengkapi pelacakan kueri (`X-Request-ID`), penanganan error terstruktur, serta pemisahan proses `/health` dan basis data `/readiness`.
6. **Framework Evaluasi Kanonikal**:
   - Evaluasi multi-tahap (MRR, HitRate, nDCG, Precision, Recall, Citation Validity, Abstention Accuracy) dengan normalisasi jalur kanonikal.

---

## 📊 Ringkasan Hasil Benchmark Fase 8

| Metrik | Stage 1: Dense Vector (Phase 4A) [Non-production Mock] | Stage 2: BM25 Lexical (Phase 4B) | Stage 3: Hybrid RRF (Phase 4C) | Stage 4: Hybrid + Neural Reranker (Phase 5) |
| :--- | :---: | :---: | :---: | :---: |
| **MRR@5** | 0.0000 | **0.5000** | 0.2500 | **0.5000** |
| **nDCG@5** | 0.0000 | **0.1687** | 0.1064 | **0.1687** |
| **Precision@5** | 0.0000 | **0.1000** | 0.1000 | **0.1000** |
| **Recall@5** | 0.0000 | **0.2500** | 0.2500 | **0.2500** |

Analisis mendalam mengenai hasil evaluasi dan analisis kegagalan dapat dilihat di [docs/eval-report.md](docs/eval-report.md).

---

## 🛠 Panduan Instalasi Singkat

```bash
# Kloning Repositori
git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
cd finreg-intelligence-rag

# Jalankan Container PostgreSQL & pgvector
docker-compose up -d

# Migrasi Basis Data
alembic upgrade head

# Jalankan Pengujian Suite Pytest
pytest

# Jalankan Server FastAPI
uvicorn finreg.api.main:app --reload --port 8000
```

---

## 📚 Indeks Dokumentasi

- [Arsitektur & Alur Data](docs/architecture.id.md)
- [Skema Basis Data & Model Data](docs/data-model.id.md)
- [Panduan Pengembang & Setup](docs/development.id.md)
- [Laporan Evaluasi & Analisis Failure](docs/eval-report.md)
- [English Version / Versi Bahasa Inggris](README.md)
