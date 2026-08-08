# FinReg Intelligence — Indonesia Financial Regulation RAG

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue.svg)](https://github.com/pgvector/pgvector)

> **Bahasa**: [English](README.md) | [Bahasa Indonesia](README.id.md)

---

## 1. Gambaran Umum Proyek

**FinReg Intelligence** adalah platform Retrieval-Augmented Generation (RAG) berstandar industri dan berorientasi produksi yang dirancang untuk mencari, membandingkan, mengambil, dan mendasarkan (*grounding*) jawaban kecerdasan buatan secara langsung pada regulasi keuangan resmi Indonesia.

Sistem ini menargetkan undang-undang, peraturan, surat edaran, dan panduan yang diterbitkan oleh **Bank Indonesia (BI)** dan **Otoritas Jasa Keuangan (OJK)**, serta menyajikan sitasi terverifikasi hingga ke nomor regulasi, pasal, ayat, dan dokumen sumber resmi.

---

## 2. Pernyataan Masalah

Menelusuri regulasi keuangan Indonesia memiliki kompleksitas tinggi bagi lembaga keuangan, pelaku fintech, petugas kepatuhan (*compliance officer*), dan analis hukum:

- **Sumber Terfragmentasi**: Regulasi dipublikasikan di portal terpisah (Bank Indonesia dan OJK) dalam bentuk dokumen PDF tidak terstruktur.
- **Silsilah Regulasi Kompleks**: Regulasi sering mengubah, mencabut, atau menggantikan ketentuan sebelumnya, sehingga berisiko mengacu pada aturan yang sudah tidak berlaku.
- **Risiko Halusinasi LLM**: Model AI umum sering berhalusinasi dalam memberikan jawaban hukum, mengutip pasal yang tidak ada, atau mengaburkan kebijakan moneter BI dengan pengawasan mikroprudensial OJK.
- **Kurangnya Keterlacakan Sitasi**: Pendekatan RAG standar sering mengabaikan sitasi hukum yang presisi, sehingga jawaban tidak dapat digunakan untuk audit kepatuhan.

---

## 3. Tujuan Proyek

1. **Presisi Terverifikasi**: Mendasarkan setiap jawaban yang dihasilkan pada kutipan terverifikasi beserta nomor regulasi, pasal, ayat, dan URL sumber yang tepat.
2. **Kesadaran Silsilah Regulasi**: Memodelkan secara eksplisit hubungan antar regulasi (perubahan, pencabutan, pelaksana).
3. **Standar Rekayasa Produksi**: Dibangun dengan modularitas Python yang bersih, konfigurasi bertipe, antarmuka domain yang terpisah dari infrastruktur, kontainerisasi, dan pengujian otomatis.
4. **Desain Independen Vendor**: Memastikan tidak ada keterikatan (*lock-in*) pada vendor LLM atau basis data vektor tertentu melalui abstraksi protokol yang bersih.

---

## 4. Arsitektur Tingkat Tinggi

Platform ini mengikuti arsitektur Berlapis yang Modular:

```
+-------------------------------------------------------------------+
|                   Sumber Data Regulasi Resmi                      |
|             (Portal Publik Bank Indonesia & OJK)                  |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                     Ingesti & Pemrosesan                          |
|  - Adapter Sumber (BankIndonesiaAdapter & OjkAdapter)             |
|  - Pelacakan checksum & metadata sumber                           |
|  - Downloader Andal (httpx + backoff + rate-limiting)             |
|  - Penyimpanan Berkas Mentah Deterministik (data/raw/...)         |
|  - Registri Ingesti PostgreSQL (regulations, documents, ver)      |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                      Lapisan Penyimpanan                          |
|  - Metadata Relasional: PostgreSQL 16                             |
|  - Penyimpanan Vektor: pgvector (Cosine / L2 / Inner Product)     |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                  Pencarian Hibrida & Reranking                    |
|  - Pencarian Vektor Padat + Pencarian Kata Kunci Sparse (BM25)    |
|  - Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranking         |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                   API & Jawaban Tergounding                       |
|  - Layanan FastAPI                                                |
|  - Generasi Jawaban LLM dengan Sitasi Terverifikasi               |
+-------------------------------------------------------------------+
```

---

## 5. Kapabilitas RAG & Ingesti Data

- **Alur Ingesti Resmi (Terimplementasi Fase 2)**: Adapter sumber resmi untuk **Bank Indonesia (PBI)** dan **Otoritas Jasa Keuangan (POJK)**. Mendukung penemuan paginasi, ekstraksi metadata, resolusi lampiran, pengunduhan yang andal dengan batas laju (*rate limiting*) dan *exponential backoff*, *checksum* SHA-256, penyimpanan lokal deterministik, persistensi basis data PostgreSQL, serta jaminan idempotensi via indeks unik parsial (`uq_document_versions_current`).
- **Pencarian Hibrida Padat-Sparse (Direncanakan)**: Menggabungkan kemiripan vektor semantik dengan pencarian kata kunci BM25 untuk pencocokan istilah hukum yang presisi.
- **Ekstraksi Sitasi Regulasi (Direncanakan)**: Menghasilkan jawaban yang dilengkapi dengan sitasi hukum terstruktur.
- **Pencarian Silsilah Lintas Regulasi (Direncanakan)**: Melacak apakah suatu pasal yang dikutip telah diubah atau dicabut oleh regulasi yang lebih baru.
- **Evaluasi Triad RAG (Direncanakan)**: Mengevaluasi kesetiaan (*faithfulness*), presisi konteks, dan relevansi jawaban melalui metrik evaluasi otomatis.

---

## 6. Sumber Data Resmi

Alur ingesti terhubung langsung ke portal publik regulasi resmi:
- **Bank Indonesia (BI)**: Peraturan Bank Indonesia (PBI) — [https://www.bi.go.id](https://www.bi.go.id)
- **Otoritas Jasa Keuangan (OJK)**: Peraturan OJK (POJK) — [https://www.ojk.go.id](https://www.ojk.go.id)

*(Catatan: Tipe regulasi PADG, SEOJK, dan PADK akan diperkenalkan pada fase mendatang. Berkas PDF biner diunduh secara dinamis dan tidak pernah dimasukkan ke dalam kontrol versi (Git).)*

---

## 7. Stack Teknologi

- **Bahasa Utama**: Python 3.11+
- **Kerangka Kerja API**: FastAPI, Uvicorn
- **Klien HTTP & Pemroses HTML**: HTTPX, BeautifulSoup4
- **Konfigurasi & Validasi**: Pydantic v2, Pydantic Settings
- **Basis Data Relasional Utama**: PostgreSQL 16
- **Penyimpanan Vektor**: pgvector
- **ORM & Migrasi Basis Data**: SQLAlchemy 2.0, Alembic
- **Pengujian & Kualitas**: pytest, pytest-asyncio, Ruff, mypy
- **Infrastruktur Kontainer**: Docker, Docker Compose

---

## 8. Struktur Repositori

```
finreg-intelligence-rag/
│
├── README.md                  # Dokumentasi proyek (Bahasa Inggris)
├── README.id.md               # Dokumentasi proyek (Bahasa Indonesia)
├── LICENSE                    # Lisensi MIT
├── .gitignore                 # Aturan abaikan Git (mengabaikan data/raw dan data/metadata)
├── .env.example               # Templat variabel lingkungan
├── pyproject.toml             # Konfigurasi build dan dependensi Python
├── docker-compose.yml         # Penyiapan PostgreSQL 16 + pgvector lokal
├── alembic.ini                # Konfigurasi migrasi basis data Alembic
│
├── src/
│   └── finreg/
│       ├── __init__.py        # Inisialisasi versi paket
│       ├── config/            # Pengaturan aplikasi Pydantic bertipe
│       ├── database/          # Koneksi SQLAlchemy & model ORM (regulations, documents, versions)
│       ├── domain/            # Model domain yang independen dari infrastruktur
│       ├── ingestion/         # Adapter sumber (BI, OJK), downloader, storage, service, CLI
│       │   ├── adapters/      # BankIndonesiaAdapter, OjkAdapter, Pembantu HTTP Base
│       │   ├── downloader.py  # DownloadManager dengan retries, backoff & rate-limiting
│       │   ├── storage.py     # LocalStorageManager untuk PDF mentah dan JSON metadata
│       │   ├── service.py     # Orkestrator IngestionService & semantik dry-run
│       │   └── cli.py         # Entrypoint CLI (python -m finreg.ingestion.cli)
│       ├── documents/         # Struktur pemrosesan dokumen
│       ├── retrieval/         # Protokol Embedding, Retriever, & Reranker
│       ├── generation/        # Abstraksi protokol Penyedia LLM
│       ├── evaluation/        # Antarmuka metrik evaluasi
│       ├── api/               # Fondasi aplikasi FastAPI
│       └── observability/    # Penyiapan logging terstruktur
│
├── migrations/                # Revisi migrasi basis data Alembic (001_baseline, 002_ingestion_registry)
├── scripts/                   # Skrip pengujian & smoke test (smoke_test_ingestion.py)
├── tests/                     # Suite pengujian (unit, integrasi, fixtures)
│   ├── fixtures/              # Fixture HTML (halaman listing & detail BI & OJK)
│   ├── integration/           # Pengujian integrasi untuk layanan ingesti & idempotensi DB
│   └── unit/                  # Pengujian unit untuk pengaturan, model domain, adapter, downloader
├── docs/                      # Dokumentasi arsitektur & model data
│   ├── architecture.md
│   ├── architecture.id.md
│   ├── data-model.md
│   ├── data-model.id.md
│   ├── development.md
│   └── development.id.md
│
├── configs/                   # Berkas konfigurasi tambahan saat runtime
└── data/                      # README tata kelola data, PDF mentah (data/raw), dan JSON metadata
```

---

## 9. Penyiapan Pengembangan

### Langkah Cepat Memulai

1. **Kloning & Konfigurasi**:
   ```bash
   git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
   cd finreg-intelligence-rag
   cp .env.example .env
   ```

2. **Pasang Dependensi**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Pada Windows: .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

3. **Jalankan Basis Data & Terapkan Migrasi**:
   ```bash
   docker compose up -d
   alembic upgrade head
   ```

4. **Jalankan CLI Ingesti**:
   ```bash
   # Jalankan simulasi (dry-run) ingesti BI
   python -m finreg.ingestion.cli --source bi --limit 5 --dry-run

   # Jalankan ingesti langsung untuk BI dan OJK
   python -m finreg.ingestion.cli --source all --limit 10
   ```

5. **Jalankan Perintah Verifikasi**:
   ```bash
   pytest
   ruff check .
   ruff format --check .
   mypy src
   ```

Untuk instruksi penyiapan lebih lengkap, lihat [`docs/development.id.md`](docs/development.id.md).

---

## 10. Status Proyek Saat Ini (Fase 2)

| Fitur / Subsystem | Status | Detail |
|---|---|---|
| Struktur Proyek & Alat Kerja | **Terimplementasi** | `pyproject.toml`, `docker-compose.yml`, `ruff`, `mypy`, `pytest` |
| Pengaturan Bertipe (`Pydantic Settings`) | **Terimplementasi** | Pengaturan aplikasi, basis data, dan mesin ingesti |
| Entitas Domain Murni & Value Objects | **Terimplementasi** | `Regulation`, `Document`, `Section`, `Chunk`, `Citation` |
| Protokol Penyedia AI Independen Vendor | **Terimplementasi** | `DocumentLoader`, `DocumentParser`, `EmbeddingProvider`, `Retriever`, `Reranker`, `LLMProvider` |
| Infrastruktur PostgreSQL 16 + pgvector | **Terimplementasi** | Kontainer Docker Compose & migrasi Alembic |
| Adapter Sumber Ingesti | **Terimplementasi (Fase 2)** | `BankIndonesiaAdapter` (PBI) & `OjkAdapter` (POJK) |
| Downloader & Penyimpanan Berkas Mentah | **Terimplementasi (Fase 2)** | Downloader HTTP terisi batas laju, retries backoff, checksum SHA-256, penyimpanan mentah |
| Skema ORM Registri Ingesti | **Terimplementasi (Fase 2)** | `regulations`, `documents`, `document_versions` dengan indeks unik parsial `uq_document_versions_current` |
| Orkestrator Ingesti & CLI | **Terimplementasi (Fase 2)** | `IngestionService` dan CLI (`python -m finreg.ingestion.cli`) |
| Suite Pengujian & Smoke Test | **Terimplementasi (Fase 2)** | Pengujian unit berbasis fixture, pengujian integrasi DB terisolasi, `smoke_test_ingestion.py` |
| Aplikasi FastAPI & `GET /health` | **Terimplementasi** | Endpoint telemetri kesehatan layanan |
| Pemrosesan Dokumen Bab/Pasal/Ayat | *Direncanakan (Fase 3)* | Ekstraksi struktur dan pemotongan chunk token |
| Indeksasi Vektor & Pencarian Hibrida | *Direncanakan (Fase 3)* | Generasi embedding dan pencarian hibrida `pgvector` |
| Reranking & Generasi Tergounding LLM | *Direncanakan (Fase 4)* | Reranking dan format sitasi |
| Evaluasi Otomatis Triad RAG | *Direncanakan (Fase 5)* | Metrik kesetiaan dan relevansi |

---

## 11. Peta Jalan Proyek

- **Fase 1**: Fondasi, model domain, protokol penyedia AI, infrastruktur basis data, endpoint kesehatan API, dokumentasi.
- **Fase 2 (Saat Ini)**: Alur ingesti data untuk BI PBI dan OJK POJK, adapter sumber, downloader dengan retries/rate-limiting, checksumming SHA-256, penyimpanan berkas mentah, registri basis data, idempotensi via indeks unik parsial, alat CLI.
- **Fase 3**: Parsing seksi dokumen PDF (Bab/Pasal/Ayat), pemotongan chunk token, generasi embedding, indeksasi `pgvector`, pencarian sparse BM25, dan penggabungan retriever hibrida.
- **Fase 4**: Integrasi penyedia LLM, sintesis prompt, generasi jawaban tergounding, dan format sitasi.
- **Fase 5**: Alur evaluasi RAG, telemetri pencarian, dan suite observabilitas.

---

## 12. Penyangkalan (Disclaimer)

*Proyek ini adalah demonstrasi portofolio rekayasa sumber terbuka. Ini bukan publikasi resmi dari Bank Indonesia atau Otoritas Jasa Keuangan. Informasi regulasi yang dihasilkan oleh implementasi RAG mendatang harus diverifikasi kembali dengan lembaran negara resmi sebelum digunakan untuk kebutuhan hukum atau kepatuhan.*
