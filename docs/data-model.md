# Data Model & Domain Entities — FinReg Intelligence

## Overview

This document outlines the core domain entities, value objects, and conceptual relational schema for **FinReg Intelligence**.

> [!IMPORTANT]
> In accordance with Phase 1 engineering principles, the domain models are implemented as **pure Python dataclasses/Pydantic schemas** in `src/finreg/domain/models.py` independent of database persistence. Database tables for business entities are intentionally deferred to Phase 2+.

---

## Core Domain Entities (Phase 1 Implemented)

### 1. `Regulation`
Represents an official Indonesian financial regulation entity.

- **`id`** (`UUID`): Unique primary key.
- **`issuer`** (`IssuerType`): Regulatory authority (`BI`, `OJK`, `LPS`, `KEMENKEU`).
- **`regulation_number`** (`str`): Official regulation number (e.g. `23/13/PBI/2021`, `12/POJK.03/2020`).
- **`title`** (`str`): Full title of the regulation.
- **`category`** (`str`): Regulatory classification (e.g., Peraturan BI, POJK, SE OJK).
- **`effective_date`** (`date`, optional): Enactment or effective enforcement date.
- **`is_active`** (`bool`): Active/in-force status indicator.
- **`metadata`** (`Dict[str, Any]`): Flexible JSON metadata.

### 2. `Document` & `DocumentVersion`
Tracks raw file metadata, source URLs, and version control lineage.

- **`Document`**: Link between a `Regulation` and file assets.
  - `id` (`UUID`), `regulation_id` (`UUID`), `file_name` (`str`), `file_type` (`str`), `source_url` (`HttpUrl`).
- **`DocumentVersion`**: Immutable snapshot version of a document.
  - `id` (`UUID`), `document_id` (`UUID`), `version_number` (`int`), `checksum_sha256` (`str`), `file_size_bytes` (`int`), `raw_metadata` (`Dict[str, Any]`).

### 3. `Section`
Represents the structural hierarchy of a regulation (Bab, Pasal, Ayat).

- **`id`** (`UUID`): Unique section identifier.
- **`document_version_id`** (`UUID`): Reference to parent document snapshot.
- **`parent_section_id`** (`UUID`, optional): Self-referential ID for nested sub-sections.
- **`level`** (`int`): Hierarchy depth index (1=Bab, 2=Pasal, 3=Ayat).
- **`title`** (`str`): Structural header (e.g. `Pasal 5 Ayat (1)`).
- **`content`** (`str`): Text payload of the section.
- **`order_index`** (`int`): Sequential index within document.

### 4. `Chunk`
The fundamental unit of text indexing and vector embedding.

- **`id`** (`UUID`): Unique chunk identifier.
- **`section_id`** (`UUID`): Reference to parent `Section`.
- **`content`** (`str`): Chunk text payload.
- **`token_count`** (`int`): Token length count.
- **`position_index`** (`int`): Sequential position within section.
- **`chunk_hash`** (`str`): Content hash for deduplication.

### 5. `RegulationRelationship`
Models legal relationships between regulations.

- **`id`** (`UUID`): Unique relationship identifier.
- **`source_regulation_id`** (`UUID`): Origin regulation.
- **`target_regulation_id`** (`UUID`): Target regulation.
- **`relationship_type`** (`RelationshipType`): `AMENDS`, `REVOKES`, `IMPLEMENTS`, `REFERENCES`, `SUPERSEDES`.

### 6. `Citation`
Value object representing a verifiable legal citation returned alongside RAG answers.

- **`regulation_number`** (`str`): Regulation identifier string.
- **`section_title`** (`str`): Section / article reference.
- **`text_snippet`** (`str`): Verifiable text excerpt.
- **`source_url`** (`str`, optional): Official public source web link.

---

## Database Migration Roadmap (Phase 2+)

Future phases will introduce SQLAlchemy ORM mappings and Alembic schema migrations for database persistence:

```
Phase 2:
├── Table: documents
├── Table: document_versions
├── Table: sections
└── Table: chunks

Phase 3:
├── Table: chunk_embeddings (PostgreSQL + pgvector extension)
└── Table: regulation_relationships

Phase 5:
├── Table: retrieval_logs
└── Table: evaluation_results
```
