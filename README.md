# FinReg Intelligence — Indonesia Financial Regulation RAG

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue.svg)](https://github.com/pgvector/pgvector)

> **Language**: [English](README.md) | [Bahasa Indonesia](README.id.md)

---

## 1. Project Overview

**FinReg Intelligence** is an enterprise-oriented, production-engineered Retrieval-Augmented Generation (RAG) platform designed to query, compare, retrieve, and ground artificial intelligence responses directly in official Indonesian financial regulations.

The system targets regulatory acts, regulations, circular letters, and guidance published by **Bank Indonesia (BI)** and **Otoritas Jasa Keuangan (OJK)**, delivering verifiable citations down to specific articles (*Pasal*), clauses (*Ayat*), and official source documents.

---

## 2. Problem Statement

Navigating Indonesian financial regulations presents significant complexity for financial institutions, fintech operators, compliance officers, and legal analysts:

- **Fragmented Sources**: Regulations are published across separate portals (Bank Indonesia and OJK) as unstructured PDF documents.
- **Complex Regulatory Lineage**: Regulations frequently amend, supersede, or partially revoke previous acts, creating risk of relying on outdated provisions.
- **LLM Hallucination Risk**: General-purpose AI models often hallucinate regulatory advice, cite non-existent articles, or confuse Bank Indonesia monetary policy with OJK microprudential supervision.
- **Lack of Verifiable Grounding**: Standard RAG approaches frequently omit precise legal citations, making answers unusable for compliance auditing.

---

## 3. Project Goals

1. **Verifiable Precision**: Ground every generated answer in verifiable excerpts with exact regulation numbers, articles, clauses, and source URLs.
2. **Regulatory Lineage Awareness**: Explicitly model relationships between regulations (amendments, revocations, implementations).
3. **Production Engineering Rigor**: Built with clean Python modularity, typed configurations, decoupled domain interfaces, containerized infrastructure, and automated testing.
4. **Vendor-Agnostic Design**: Ensure zero lock-in to specific LLM or vector database vendors through clean protocol abstractions.

---

## 4. High-Level Architecture

The platform follows a modular layered architecture:

```
+-------------------------------------------------------------------+
|               Official Regulatory Data Sources                    |
|             (Bank Indonesia & OJK Public Portals)                 |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                     Ingestion & Processing                        |
|  - Source Adapters (BankIndonesiaAdapter & OjkAdapter)            |
|  - Checksum & source metadata tracking                            |
|  - Resilient DownloadManager (httpx + backoff + rate-limiting)    |
|  - Deterministic Raw File Storage (data/raw/...)                  |
|  - PostgreSQL Ingestion Registry (regulations, documents, ver)    |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                      Storage Layer                                |
|  - Relational Metadata: PostgreSQL 16                             |
|  - Vector Storage: pgvector (Cosine / L2 / Inner Product)         |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                  Hybrid Retrieval & Reranking                     |
|  - Dense Vector Search + Sparse Keyword Retrieval (BM25)          |
|  - Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranking         |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                     API & Grounded Answer                         |
|  - FastAPI Service                                                |
|  - LLM Answer Generation with Verifiable Citations                |
+-------------------------------------------------------------------+
```

---

## 5. RAG & Ingestion Capabilities

- **Official Ingestion Pipeline (Phase 2 Implemented)**: Source adapters for **Bank Indonesia (PBI)** and **Otoritas Jasa Keuangan (POJK)**. Supports pagination discovery, metadata parsing, attachment resolution, resilient downloading with rate-limiting and exponential backoff, SHA-256 checksumming, deterministic local storage, PostgreSQL database persistence, and idempotency guarantees via a partial unique index (`uq_document_versions_current`).
- **Hybrid Dense-Sparse Retrieval (Planned)**: Combines semantic vector similarity with keyword BM25 retrieval for precise legal terminology matching.
- **Regulatory Citation Extraction (Planned)**: Generates answers accompanied by structured legal citations.
- **Cross-Regulation Lineage Lookup (Planned)**: Traces whether a cited article has been amended or revoked by subsequent regulations.
- **RAG Triad Evaluation (Planned)**: Evaluates faithfulness, context precision, and answer relevance via automated evaluation metrics.

---

## 6. Official Data Sources

The ingestion pipeline connects directly to official public regulatory portals:
- **Bank Indonesia (BI)**: Peraturan Bank Indonesia (PBI) — [https://www.bi.go.id](https://www.bi.go.id)
- **Otoritas Jasa Keuangan (OJK)**: Peraturan OJK (POJK) — [https://www.ojk.go.id](https://www.ojk.go.id)

*(Note: PADG, SEOJK, PADK source types will be introduced in future phases. Binary PDFs are downloaded dynamically and are never committed to version control.)*

---

## 7. Technology Stack

- **Core Language**: Python 3.11+
- **API Framework**: FastAPI, Uvicorn
- **HTTP Client & HTML Parsing**: HTTPX, BeautifulSoup4
- **Configuration & Validation**: Pydantic v2, Pydantic Settings
- **Primary Relational DB**: PostgreSQL 16
- **Vector Storage**: pgvector
- **Database ORM & Migrations**: SQLAlchemy 2.0, Alembic
- **Testing & Quality**: pytest, pytest-asyncio, Ruff, mypy
- **Container Infrastructure**: Docker, Docker Compose

---

## 8. Repository Structure

```
finreg-intelligence-rag/
│
├── README.md                  # Project documentation (English)
├── README.id.md               # Project documentation (Indonesian)
├── LICENSE                    # MIT License
├── .gitignore                 # Git ignore rules (ignores data/raw and data/metadata)
├── .env.example               # Environment variables template
├── pyproject.toml             # Python build configuration and dependencies
├── docker-compose.yml         # Local PostgreSQL 16 + pgvector setup
├── alembic.ini                # Alembic database migration config
│
├── src/
│   └── finreg/
│       ├── __init__.py        # Package version initialization
│       ├── config/            # Typed Pydantic application settings
│       ├── database/          # SQLAlchemy connection & ORM models (regulations, documents, versions)
│       ├── domain/            # Infrastructure-independent domain models
│       ├── ingestion/         # Source adapters (BI, OJK), downloader, storage, service, CLI
│       │   ├── adapters/      # BankIndonesiaAdapter, OjkAdapter, Base HTTP helper
│       │   ├── downloader.py  # DownloadManager with retries, backoff & rate-limiting
│       │   ├── storage.py     # LocalStorageManager for raw PDFs and metadata JSON
│       │   ├── service.py     # IngestionService orchestrator & dry-run semantics
│       │   └── cli.py         # CLI entrypoint (python -m finreg.ingestion.cli)
│       ├── documents/         # Document processing structures
│       ├── retrieval/         # Embedding, Retriever, & Reranker protocols
│       ├── generation/        # LLM Provider protocol abstractions
│       ├── evaluation/        # Evaluation metric interfaces
│       ├── api/               # FastAPI application foundation
│       └── observability/    # Structured logging setup
│
├── migrations/                # Alembic migration revisions (001_baseline, 002_ingestion_registry)
├── scripts/                   # Helper & smoke test scripts (smoke_test_ingestion.py)
├── tests/                     # Test suite (unit, integration, fixtures)
│   ├── fixtures/              # HTML test fixtures (BI & OJK listing/detail pages)
│   ├── integration/           # Integration tests for ingestion service & DB idempotency
│   └── unit/                  # Unit tests for settings, domain models, adapters, downloader
├── docs/                      # Architectural & data model documentation
│   ├── architecture.md
│   ├── architecture.id.md
│   ├── data-model.md
│   ├── data-model.id.md
│   ├── development.md
│   └── development.id.md
│
├── configs/                   # Runtime configuration files
└── data/                      # Data governance README, raw PDFs (data/raw), and metadata JSON
```

---

## 9. Development Setup

### Quickstart

1. **Clone & Configure**:
   ```bash
   git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
   cd finreg-intelligence-rag
   cp .env.example .env
   ```

2. **Install Dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

3. **Start Database & Apply Migrations**:
   ```bash
   docker compose up -d
   alembic upgrade head
   ```

4. **Run Ingestion CLI**:
   ```bash
   # Run BI ingestion dry-run
   python -m finreg.ingestion.cli --source bi --limit 5 --dry-run

   # Run live ingestion for BI and OJK
   python -m finreg.ingestion.cli --source all --limit 10
   ```

5. **Run Verification Commands**:
   ```bash
   pytest
   ruff check .
   ruff format --check .
   mypy src
   ```

For detailed onboarding instructions, see [`docs/development.md`](docs/development.md).

---

## 10. Current Project Status (Phase 2)

| Feature / Subsystem | Status | Details |
|---|---|---|
| Repository Architecture & Tooling | **Implemented** | `pyproject.toml`, `docker-compose.yml`, `ruff`, `mypy`, `pytest` |
| Typed Configuration (`Pydantic Settings`) | **Implemented** | Application, Database, and Ingestion engine settings |
| Domain Entities & Value Objects | **Implemented** | `Regulation`, `Document`, `Section`, `Chunk`, `Citation` |
| Vendor-Agnostic Provider Protocols | **Implemented** | `DocumentLoader`, `DocumentParser`, `EmbeddingProvider`, `Retriever`, `Reranker`, `LLMProvider` |
| PostgreSQL 16 + pgvector Infrastructure | **Implemented** | Docker Compose container & Alembic migrations |
| Ingestion Source Adapters | **Implemented (Phase 2)** | `BankIndonesiaAdapter` (PBI) & `OjkAdapter` (POJK) |
| Resilient Downloader & Storage | **Implemented (Phase 2)** | Rate-limited HTTP downloader, exponential backoff retries, SHA-256 checksum, raw storage |
| Ingestion Registry ORM Schema | **Implemented (Phase 2)** | `regulations`, `documents`, `document_versions` with partial unique index `uq_document_versions_current` |
| Ingestion Orchestrator & CLI | **Implemented (Phase 2)** | `IngestionService` and CLI (`python -m finreg.ingestion.cli`) |
| Ingestion Test Suite & Live Smoke Test | **Implemented (Phase 2)** | Fixture-based unit tests, isolated DB integration tests, `smoke_test_ingestion.py` |
| Regulatory PDF Structure Parsing | **Implemented (Phase 3A)** | `PdfExtractor`, `TextNormalizer`, `RegulatoryStructureParser`, `StructureValidator`, `document_nodes` |
| Document Parsing CLI & Test Suite | **Implemented (Phase 3A)** | `python -m finreg.documents.cli`, non-overlapping coverage ratio, composite FK integrity |
| FastAPI Application & `GET /health` | **Implemented** | Lightweight service health telemetry endpoint |
| Vector Indexing & Hybrid Retrieval | *Planned (Phase 3B)* | Embedding generation, `pgvector` indexing, and BM25 sparse search |
| Reranking & LLM Grounded Generation | *Planned (Phase 4)* | Reranking and citation formatting |
| RAG Triad Automated Evaluation | *Planned (Phase 5)* | Faithfulness and relevance metrics |

---

## 11. Project Roadmap

- **Phase 1**: Foundation, domain models, provider protocols, database infrastructure, API health endpoint, documentation.
- **Phase 2 (Current)**: Data ingestion pipeline for BI PBI and OJK POJK, source adapters, downloader with retries/rate-limiting, SHA-256 checksumming, raw storage, database registry, idempotency via partial unique index, CLI tool.
- **Phase 3**: PDF document section parsing (Bab/Pasal/Ayat), token chunking, embedding generation, `pgvector` indexing, BM25 sparse search, and hybrid retriever fusion.
- **Phase 4**: LLM provider integration, prompt synthesis, grounded answer generation, and citation formatting.
- **Phase 5**: RAG evaluation pipeline, retrieval telemetry, and observability suite.

---

## 12. Disclaimer

*This project is an open-source engineering portfolio demonstration. It is not an official publication of Bank Indonesia or Otoritas Jasa Keuangan. Regulatory information provided by future RAG implementations must be verified against official government gazettes before legal or compliance usage.*
