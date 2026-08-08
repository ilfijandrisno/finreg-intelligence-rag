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
|  - Checksum & source metadata tracking                            |
|  - Section structure parsing (Bab / Pasal / Ayat)                 |
|  - Positional token chunking                                      |
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

## 5. Planned RAG Capabilities

- **Hybrid Dense-Sparse Retrieval**: Combines semantic vector similarity with keyword BM25 retrieval for precise legal terminology matching.
- **Regulatory Citation Extraction**: Generates answers accompanied by structured legal citations.
- **Cross-Regulation Lineage Lookup**: Traces whether a cited article has been amended or revoked by subsequent regulations.
- **RAG Triad Evaluation**: Evaluates faithfulness, context precision, and answer relevance via automated evaluation metrics.

---

## 6. Planned Data Sources

The platform ingests only official public regulatory sources:
- **Bank Indonesia (BI)**: Peraturan Bank Indonesia (PBI), Surat Edaran (SE BI), Padoman Operasional.
- **Otoritas Jasa Keuangan (OJK)**: Peraturan OJK (POJK), Surat Edaran OJK (SEOJK), Peraturan Dewan Komisioner.

> *Note: Binary PDFs are fetched dynamically and never committed to version control.*

---

## 7. Technology Stack

- **Core Language**: Python 3.11+
- **API Framework**: FastAPI, Uvicorn
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
├── .gitignore                 # Git ignore rules
├── .env.example               # Environment variables template
├── pyproject.toml             # Python build configuration and dependencies
├── docker-compose.yml         # Local PostgreSQL 16 + pgvector setup
├── alembic.ini                # Alembic database migration config
│
├── src/
│   └── finreg/
│       ├── __init__.py        # Package version initialization
│       ├── config/            # Typed Pydantic application settings
│       ├── database/          # SQLAlchemy connection infrastructure
│       ├── domain/            # Infrastructure-independent domain models
│       ├── ingestion/         # Loader & Parser protocol abstractions
│       ├── documents/         # Document processing structures
│       ├── retrieval/         # Embedding, Retriever, & Reranker protocols
│       ├── generation/        # LLM Provider protocol abstractions
│       ├── evaluation/        # Evaluation metric interfaces
│       ├── api/               # FastAPI application foundation
│       └── observability/    # Structured logging setup
│
├── migrations/                # Alembic database migration revisions
├── tests/                     # Test suite (unit & integration)
├── docs/                      # Architectural & data model documentation
│   ├── architecture.md
│   ├── architecture.id.md
│   ├── data-model.md
│   ├── data-model.id.md
│   ├── development.md
│   └── development.id.md
│
├── configs/                   # Additional runtime configuration files
└── data/                      # Data governance README and local datasets
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

4. **Run FastAPI Server**:
   ```bash
   uvicorn finreg.api.main:app --reload
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

## 10. Current Project Status (Phase 1)

| Feature / Subsystem | Status |
|---|---|
| Project Structure & Tooling | **Implemented** |
| Typed Configuration (`Pydantic Settings`) | **Implemented** |
| Pure Domain Entities & Value Objects | **Implemented** |
| Vendor-Agnostic Provider Protocols | **Implemented** |
| PostgreSQL 16 + pgvector Infrastructure | **Implemented** |
| Alembic Baseline Migration | **Implemented** |
| FastAPI Application & `GET /health` | **Implemented** |
| Test Suite (Config, Domain, API Health) | **Implemented** |
| Web Scraping & PDF Ingestion | *Planned (Phase 2)* |
| Document Parsing & Chunking | *Planned (Phase 2)* |
| Vector Indexing & Hybrid Retrieval | *Planned (Phase 3)* |
| Reranking & LLM Grounded Generation | *Planned (Phase 4)* |
| RAG Triad Automated Evaluation | *Planned (Phase 5)* |

---

## 11. Project Roadmap

- **Phase 1 (Current)**: Foundation, domain models, provider protocols, database infrastructure, API health endpoint, documentation.
- **Phase 2**: Document ingestion pipeline, PDF section parsing, token chunking, and persistence schema migrations.
- **Phase 3**: Embedding generation, `pgvector` indexing, BM25 sparse search, and hybrid retriever fusion.
- **Phase 4**: LLM provider integration, prompt synthesis, grounded answer generation, and citation formatting.
- **Phase 5**: RAG evaluation pipeline, retrieval telemetry, and observability suite.

---

## 12. Disclaimer

*This project is an open-source engineering portfolio demonstration. It is not an official publication of Bank Indonesia or Otoritas Jasa Keuangan. Regulatory information provided by future RAG implementations must be verified against official government gazettes before legal or compliance usage.*
