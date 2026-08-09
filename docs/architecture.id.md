# FinReg Intelligence RAG: Arsitektur Sistem & Alur Data

## 1. Ringkasan Sistem

FinReg Intelligence RAG adalah platform legal technology tingkat produksi yang dirancang untuk otomasi ingestasi, indeksasi hibrida, reranking, dan pencarian jawaban berbasis bukti hukum (*grounded QA*) atas peraturan keuangan Indonesia yang diterbitkan oleh Bank Indonesia (BI) dan Otoritas Jasa Keuangan (OJK).

Platform ini menjamin provensi hukum yang ketat, sitasi inline yang terverifikasi, isolasi konteks, dan mekanisme *abstention* otomatis berbasis ambang batas skor.

---

## 2. Arsitektur Sistem End-to-End

```mermaid
flowchart TD
    subgraph Ingestion["Fase 2 & 3: Ingestasi & Pemrosesan Dokumen"]
        PDF["PDF Peraturan Mentah"] --> Extractor["PyMuPDF Reader"]
        Extractor --> Normalizer["Pembersih & Normalisasi Teks"]
        Parser --> Tree["Pohon Dokumen Hirarkis (Node)"]
        Normalizer --> Parser["Context-Aware State-Machine Parser"]
        Tree --> Chunker["Semantic Legal Chunker (Max 1500 karakter)"]
        Chunker --> DB_Chunks[("PostgreSQL: retrieval_chunks")]
    end

    subgraph Indexing["Fase 4: Indeksasi Vektor Hibrida"]
        DB_Chunks --> HNSW["Indeks Vektor HNSW (cosine)"]
        DB_Chunks --> GIN["Indeks Teks Lengkap GIN (tsvector)"]
    end

    subgraph Retrieval["Fase 4 & 5: Pencarian Hibrida Multi-Tahap"]
        UserQuery["Kueri Pengguna"] --> VectorSearch["VectorSearchService (HNSW)"]
        UserQuery --> LexicalSearch["LexicalSearchService (tsvector)"]
        VectorSearch --> RRF["Penggabungan Hybrid RRF (k=60)"]
        LexicalSearch --> RRF
        RRF --> Reranker["RerankingService (BAAI/bge-reranker-v2-m3)"]
    end

    subgraph Generation["Fase 6 & 7: RAG Terverifikasi & FastAPI"]
        Reranker --> Gate{"Skor Tertinggi >= Ambang Batas (0.30)?"}
        Gate -- Tidak --> Abstain["Jawaban Abstain (Kosong)"]
        Gate -- Ya --> PromptBuilder["Isolasi Konteks & Asamblesi Prompt"]
        PromptBuilder --> LLM["LLM Provider (gpt-4o-mini / Mock)"]
        LLM --> CitVal["Validator Sitasi (Regex [C1])"]
        CitVal --> FastApi["FastAPI REST Endpoint (/api/v1/rag/query)"]
    end
```

---

## 3. Komponen Utama

- **Parser Struktur Hukum**: Parser berbasis *state-machine* kontekstual yang mengekstrak hirarki hukum (`BAB`, `Pasal`, `Ayat`, `Huruf`, `Angka`).
- **Pencarian Hibrida RRF**: Penggabungan HNSW vector search (`pgvector`) dan BM25 full-text search (`tsvector`) dengan Reciprocal Rank Fusion ($k=60$).
- **Neural Reranking**: Model Cross-Encoder (`BAAI/bge-reranker-v2-m3`) untuk pemeringkatan ulang berbasis presisi semantik.
- **RAG Terverifikasi & Abstention**: Evaluasi sitasi berbasis regex deterministik dan penghentian jawaban otomatis jika bukti tidak mencukupi.
