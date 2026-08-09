# FinReg Intelligence RAG: Database Schema & Canonical Provenance Model

**Language:** 🇬🇧 English · [🇮🇩 Bahasa Indonesia](data-model.id.md)

## 1. Relational Schema Overview (PostgreSQL + pgvector)

The database schema is structured to preserve official regulatory metadata, document versioning, hierarchical legal tree nodes, and retrieval-ready chunks.

```mermaid
erDiagram
    REGULATIONS ||--o{ DOCUMENT_VERSIONS : "has versions"
    DOCUMENT_VERSIONS ||--o{ DOCUMENT_NODES : "contains nodes"
    DOCUMENT_VERSIONS ||--o{ RETRIEVAL_CHUNKS : "contains chunks"
    DOCUMENT_NODES ||--o{ RETRIEVAL_CHUNKS : "source node"

    REGULATIONS {
        uuid id PK
        string source "BI or OJK"
        string regulation_type "PBI or POJK"
        string regulation_number "e.g. 20/2026"
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
        string node_type "BAB, PASAL, AYAT, etc."
        string node_number
        string title
        text text
        int page_start
        int page_end
        int sequence
        string path "e.g. BAB I/Pasal 1/Ayat (1)"
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
        string structural_path "e.g. BAB I/Pasal 1/Ayat (1) [Part 1/2]"
        text chunk_text
        text contextual_text
        vector embedding "1536-dim vector"
        tsvector fts_document "indonesian search vector"
        int page_start
        int page_end
        int sequence
    }
```

---

## 2. Database Indexes & Performance Optimization

### Vector Search Index
- **Index Type**: HNSW (`vector_cosine_ops`)
- **Parameters**: `m = 16`, `ef_construction = 64`
- **Target Column**: `retrieval_chunks.embedding` (1536 dimensions)

### Lexical Full-Text Search Index
- **Index Type**: GIN Index
- **Target Column**: `retrieval_chunks.fts_document` (`tsvector` with `indonesian` configuration)

### Relational & Composite B-Tree Indexes
- `idx_retrieval_chunks_doc_ver` (`document_id`, `document_version_id`)
- `idx_retrieval_chunks_reg_num` (`regulation_type`, `regulation_number`)

---

## 3. Canonical Legal Identity Schema

For benchmark evaluation and legal provenance verification, every ground truth provision and retrieved evidence chunk is identified by a deterministic **Canonical Identity 4-Tuple**:

$$\text{Canonical Key} = (document\_id, \text{normalize}(structural\_path), page\_start, page\_end)$$

### Structural Path Suffix Normalization
During evaluation comparisons, text-splitter suffixes are stripped without mutating database records:

```python
# 'BAB I/Pasal 1/Ayat (1) [Part 1/2]' -> 'BAB I/Pasal 1/Ayat (1)'
normalized_path = re.sub(r"\s*\[Part\s+\d+/\d+\]$", "", raw_path)
```
