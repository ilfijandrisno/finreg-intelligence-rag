# Arsitektur Sistem — FinReg Intelligence

## Gambaran Umum

**FinReg Intelligence** adalah platform Retrieval-Augmented Generation (RAG) berstandar produksi yang dirancang untuk mendasarkan (*grounding*) jawaban kecerdasan buatan pada regulasi keuangan resmi Indonesia yang diterbitkan oleh **Bank Indonesia (BI)** dan **Otoritas Jasa Keuangan (OJK)**.

Arsitektur sistem menekankan pada modularitas, keterlacakan rekam jejak data (*data lineage*), pemisahan tegas antara model domain dan infrastruktur eksternal, serta abstraksi penyedia AI yang independen dari vendor.

---

## Alur Data Target End-to-End

```
+-------------------------------------------------------------------+
|               Sumber Regulasi Publik Resmi                        |
|                 (Portal Bank Indonesia & OJK)                     |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                      Lapisan Ingesti                              |
|   - Ambil metadata dokumen & PDF mentah                           |
|   - Hitung checksum SHA-256 & pertahankan URL sumber asli         |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                 Lapisan Pemrosesan Dokumen                        |
|   - Strukturkan regulasi ke Bab, Pasal, & Ayat                    |
|   - Hasilkan Chunk teks semantik dengan rekam jejak posisi        |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                    Penyimpanan & Indeksasi                        |
|   - Relational DB (PostgreSQL 16) untuk metadata & rekam jejak    |
|   - Vector DB (pgvector) untuk embedding vektor padat             |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                  Pencarian Hibrida & Reranking                    |
|   - Pencarian vektor semantik (pgvector)                          |
|   - Pencarian kata kunci sparse (BM25 / PostgreSQL Full-Text)     |
|   - Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranking        |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                    Generasi & Grounding                           |
|   - Sintesis prompt dengan chunk konteks hasil pencarian          |
|   - Generasi jawaban oleh LLM                                     |
|   - Ekstraksi Sitasi regulasi hukum resmi secara otomatis         |
+-------------------------------------------------------------------+
```

---

## Status Implementasi Komponen

| Komponen | Status | Detail |
|---|---|---|
| Repositori & Alat Kerja | **Terimplementasi (Fase 1)** | `pyproject.toml`, `docker-compose.yml`, `ruff`, `mypy`, `pytest` |
| Pengaturan Aplikasi | **Terimplementasi (Fase 1)** | Pengaturan `Pydantic` bertipe yang dimuat dari `.env` |
| Model Domain | **Terimplementasi (Fase 1)** | Entitas Python murni (`Regulation`, `Document`, `Section`, `Chunk`, `Citation`) |
| Abstraksi Penyedia AI | **Terimplementasi (Fase 1)** | Antarmuka `Protocol` Python untuk Loader, Parser, Embedding, Retriever, Reranker, LLM |
| Infrastruktur Basis Data | **Terimplementasi (Fase 1)** | Kontainer PostgreSQL 16 + `pgvector` & migrasi basis Alembic |
| Fondasi API | **Terimplementasi (Fase 1)** | Aplikasi FastAPI yang menyediakan endpoint ringan `GET /health` |
| Ingesti Dokumen | *Direncanakan (Fase 2)* | Web scraping, ekstraksi metadata, dan pengunduhan PDF |
| Pemrosesan Dokumen | *Direncanakan (Fase 2)* | Pemisahan struktur ke pasal/bab dan pemotongan chunk token |
| Skema Persistensi | *Direncanakan (Fase 2)* | Model ORM dan tabel bisnis (`documents`, `sections`, `chunks`, `embeddings`) |
| Indeksasi Vektor | *Direncanakan (Fase 3)* | Pembuatan embedding dan pembuatan indeks `pgvector` |
| Pencarian Hibrida | *Direncanakan (Fase 3)* | Kombinasi pencarian vektor padat dan kata kunci sparse |
| Reranking Cross-Encoder | *Direncanakan (Fase 3)* | Penilaian ulang konteks dan penyaringan |
| Generasi Tergounding | *Direncanakan (Fase 4)* | Integrasi LLM dan format sitasi |
| Evaluasi RAG | *Direncanakan (Fase 5)* | Evaluasi triad RAG (kesetiaan/faithfulness, relevansi jawaban, presisi konteks) |

---

## Prinsip Desain Utama

1. **Independensi Vendor**: Seluruh penyedia AI eksternal (embedding, LLM, reranker) berinteraksi dengan domain utama melalui protokol abstrak Python (`EmbeddingProvider`, `LLMProvider`, `Reranker`). Tidak ada keterikatan pada satu kerangka kerja atau vendor tertentu.
2. **Rekam Jejak Data yang Ketat**: Jawaban yang dihasilkan harus terhubung langsung secara tepat ke nomor regulasi, Pasal, Ayat, dan URL sumber resmi.
3. **Tanpa Overhead Kerangka Kerja Berat**: Logika inti dibangun langsung menggunakan pustaka standar Python dan kerangka kerja ringan (FastAPI, Pydantic, SQLAlchemy), menghindari penggunaan kerangka orkestrasi berat seperti LangChain atau LlamaIndex.
