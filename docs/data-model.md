# Data Model & Domain Entities — FinReg Intelligence

## Overview

This document outlines the core domain entities, value objects, and relational database persistence schema for **FinReg Intelligence**.

---

## Relational Database Registry Schema (Phase 2 Implemented)

Phase 2 introduces database persistence tables for tracking regulatory ingestion lineage, metadata, documents, and version history.

```
                    ┌────────────────────────┐
                    │      regulations       │
                    ├────────────────────────┤
                    │ id (PK)                │
                    │ source                 │
                    │ regulation_type        │
                    │ regulation_number      │
                    │ title                  │
                    │ sector                 │
                    │ subsector              │
                    │ status                 │
                    │ published_date         │
                    │ effective_date         │
                    │ detail_url             │
                    │ summary                │
                    │ abstract               │
                    │ created_at             │
                    │ updated_at             │
                    └───────────┬────────────┘
                                │ 1
                                │
                                │ N
                    ┌───────────┴────────────┐
                    │       documents        │
                    ├────────────────────────┤
                    │ id (PK)                │
                    │ regulation_id (FK)     │
                    │ document_type          │
                    │ document_url           │
                    │ filename               │
                    │ content_type           │
                    │ content_length         │
                    │ sha256                 │
                    │ storage_path           │
                    │ retrieved_at           │
                    │ created_at             │
                    └───────────┬────────────┘
                                │ 1
                                │
                                │ N
                    ┌───────────┴────────────┐
                    │   document_versions    │
                    ├────────────────────────┤
                    │ id (PK)                │
                    │ document_id (FK)       │
                    │ sha256                 │
                    │ storage_path           │
                    │ content_length         │
                    │ first_seen_at          │
                    │ last_seen_at           │
                    │ is_current             │
                    └────────────────────────┘
```

---

## Database Table Specifications

### 1. `regulations` Table
Stores official regulation metadata ingested from BI and OJK portals.

- **`id`** (`UUID`, PK): Unique primary key.
- **`source`** (`VARCHAR(10)`): Issuing authority (`BI`, `OJK`).
- **`regulation_type`** (`VARCHAR(20)`): Classification type (`PBI`, `POJK`).
- **`regulation_number`** (`VARCHAR(100)`): Official regulation number (e.g. `23/13/PBI/2021`, `12/POJK.03/2020`).
- **`title`** (`TEXT`): Full regulation title.
- **`sector`** (`VARCHAR(150)`, optional): Financial sector taxonomy.
- **`subsector`** (`VARCHAR(150)`, optional): Subsector taxonomy.
- **`status`** (`VARCHAR(100)`, optional): Source-provided legal status string.
- **`published_date`** (`DATE`, optional): Publication date.
- **`effective_date`** (`DATE`, optional): Effective enforcement date.
- **`detail_url`** (`TEXT`): Official portal detail page URL.
- **`summary`** (`TEXT`, optional): Excerpt summary.
- **`abstract`** (`TEXT`, optional): Full abstract text.
- **`created_at`** (`TIMESTAMPTZ`): Record creation timestamp.
- **`updated_at`** (`TIMESTAMPTZ`): Record update timestamp.

**Constraints & Indexes**:
- `UNIQUE(source, regulation_type, regulation_number)` (`uq_regulations_source_type_num`)
- `INDEX(source, regulation_type)` (`idx_regulations_source_type`)
- `INDEX(detail_url)` (`idx_regulations_detail_url`)

---

### 2. `documents` Table
Tracks attachment document references associated with regulations.

- **`id`** (`UUID`, PK): Unique primary key.
- **`regulation_id`** (`UUID`, FK -> `regulations.id`): Parent regulation identifier.
- **`document_type`** (`VARCHAR(50)`): Attachment classification (`regulation`, `faq`, `abstract`, `other`).
- **`document_url`** (`TEXT`): Direct download URL.
- **`filename`** (`VARCHAR(255)`): File name string.
- **`content_type`** (`VARCHAR(100)`): MIME type (e.g. `application/pdf`).
- **`content_length`** (`BIGINT`, optional): File size in bytes.
- **`sha256`** (`VARCHAR(64)`, optional): Latest SHA-256 checksum.
- **`storage_path`** (`TEXT`, optional): Storage path to active raw PDF file.
- **`retrieved_at`** (`TIMESTAMPTZ`, optional): Timestamp of last retrieval.
- **`created_at`** (`TIMESTAMPTZ`): Record creation timestamp.

**Constraints & Indexes**:
- `UNIQUE(regulation_id, document_type, document_url)` (`uq_documents_reg_type_url`)

---

### 3. `document_versions` Table
Maintains an immutable historical record of raw document payloads.

- **`id`** (`UUID`, PK): Unique version primary key.
- **`document_id`** (`UUID`, FK -> `documents.id`): Parent document identifier.
- **`sha256`** (`VARCHAR(64)`): SHA-256 checksum of raw payload.
- **`storage_path`** (`TEXT`): Storage path (`data/raw/{source}/{type}/{doc_id}/{sha256}.pdf`).
- **`content_length`** (`BIGINT`): Byte payload size.
- **`first_seen_at`** (`TIMESTAMPTZ`): First discovery timestamp.
- **`last_seen_at`** (`TIMESTAMPTZ`): Most recent observation timestamp.
- **`is_current`** (`BOOLEAN`): True if this version represents the active version.

**Constraints & Indexes**:
- `UNIQUE(document_id, sha256)` (`uq_document_versions_doc_sha256`)
- `INDEX(sha256)` (`idx_document_versions_sha256`)
- **Partial Unique Index Invariant**:
  ```sql
  CREATE UNIQUE INDEX uq_document_versions_current ON document_versions (document_id) WHERE is_current = TRUE;
  ```
  *Enforces the critical invariant that at most one version per document can be marked as current.*

---

## Database Migration Roadmap (Phase 3+)

Future phases will introduce document parsing and vector search tables:

```
Phase 3:
├── Table: sections (Bab / Pasal / Ayat structural hierarchy)
├── Table: chunks (Positional token chunk payload)
├── Table: chunk_embeddings (PostgreSQL + pgvector vector embeddings)
└── Table: regulation_relationships (Legal lineage: amends, revokes)

Phase 5:
├── Table: retrieval_logs
└── Table: evaluation_results
```
