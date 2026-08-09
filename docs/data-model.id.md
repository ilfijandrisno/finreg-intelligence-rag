# FinReg Intelligence RAG: Skema Basis Data & Model Provenance Kanonikal

**Bahasa:** 🇮🇩 Bahasa Indonesia · [🇬🇧 English](data-model.md)

## 1. Ringkasan Skema Relasional (PostgreSQL + pgvector)

Skema basis data dirancang untuk mempertahankan metadata regulasi resmi, versioning dokumen, node pohon hukum hirarkis, dan chunk yang siap digunakan untuk retrieval.

```mermaid
erDiagram
    REGULATIONS ||--o{ DOCUMENT_VERSIONS : "memiliki versi"
    DOCUMENT_VERSIONS ||--o{ DOCUMENT_NODES : "berisi node"
    DOCUMENT_VERSIONS ||--o{ RETRIEVAL_CHUNKS : "berisi chunk"
    DOCUMENT_NODES ||--o{ RETRIEVAL_CHUNKS : "source node"

    REGULATIONS {
        uuid id PK
        string source "BI atau OJK"
        string regulation_type "PBI atau POJK"
        string regulation_number "contoh 20/2026"
        string title
        date issuance_date
        string detail_url
    }

    DOCUMENT_VERSIONS {
        uuid id PK
        uuid document_id FK
        string version_tag
        string pdf_hash
        timestamp effective_date
    }

    DOCUMENT_NODES {
        uuid id PK
        uuid document_id FK
        uuid document_version_id FK
        uuid parent_id FK
        string node_type "BAB, PASAL, AYAT, dll."
        string node_number
        string title
        text text
        int page_start
        int page_end
        int sequence
        string path "contoh BAB I/Pasal 1/Ayat (1)"
    }

    RETRIEVAL_CHUNKS {
        uuid id PK
        uuid document_id FK
        uuid document_version_id FK
        uuid source_node_id FK
        string chunk_hash
        string source
        string regulation_type
        string regulation_number
        string title
        string structural_path "contoh BAB I/Pasal 1/Ayat (1) [Part 1/2]"
        text chunk_text
        text contextual_text
        vector embedding "vector 1536 dimensi"
        tsvector fts_document "search vector bahasa Indonesia"
        int page_start
        int page_end
        int sequence
    }
```

---

## 2. Indeks Basis Data & Optimasi Performa

### Vector Search Index
- **Jenis Indeks**: HNSW (`vector_cosine_ops`)
- **Parameter**: `m = 16`, `ef_construction = 64`
- **Kolom Target**: `retrieval_chunks.embedding` (1536 dimensi)

### Lexical Full-Text Search Index
- **Jenis Indeks**: GIN Index
- **Kolom Target**: `retrieval_chunks.fts_document` (`tsvector` dengan konfigurasi `indonesian`)

### Relational & Composite B-Tree Indexes
- `idx_retrieval_chunks_doc_ver` (`document_id`, `document_version_id`)
- `idx_retrieval_chunks_reg_num` (`regulation_type`, `regulation_number`)

---

## 3. Skema Identitas Hukum Kanonikal

Untuk evaluasi benchmark dan verifikasi provenance hukum, setiap provision ground truth dan evidence chunk hasil retrieval diidentifikasi menggunakan **Canonical Identity 4-Tuple** yang deterministik:

$$\text{Canonical Key} = (document\_id, \text{normalize}(structural\_path), page\_start, page\_end)$$

### Normalisasi Suffix Structural Path
Selama perbandingan evaluasi, suffix yang ditambahkan oleh text splitter dihapus tanpa memodifikasi record database:

```python
# 'BAB I/Pasal 1/Ayat (1) [Part 1/2]' -> 'BAB I/Pasal 1/Ayat (1)'
normalized_path = re.sub(r"\s*\[Part\s+\d+/\d+\]$", "", raw_path)
```
