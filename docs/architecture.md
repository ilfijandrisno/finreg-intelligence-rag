# System Architecture — FinReg Intelligence

## Overview

**FinReg Intelligence** is a production-oriented Retrieval-Augmented Generation (RAG) platform designed to ground artificial intelligence answers in official Indonesian financial regulations issued by **Bank Indonesia (BI)** and **Otoritas Jasa Keuangan (OJK)**.

The architecture emphasizes modularity, data lineage traceability, strict separation of domain models from external infrastructure, and vendor-agnostic provider abstractions.

---

## Target End-to-End Data Flow

```
+-------------------------------------------------------------------+
|               Official Public Regulatory Sources                  |
|                 (Bank Indonesia & OJK Portals)                    |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                      Ingestion Layer                              |
|   - Fetch document metadata & raw PDFs                           |
|   - Compute SHA-256 checksums & preserve source URLs              |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                     Document Processing Layer                     |
|   - Structure regulation into Sections, Articles (Pasal), & Clauses|
|   - Generate semantic text Chunks with positional lineage        |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                      Storage & Indexing                           |
|   - Relational DB (PostgreSQL 16) for domain metadata & lineage   |
|   - Vector DB (pgvector) for dense vector embeddings             |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                     Hybrid Retrieval & Reranking                  |
|   - Dense semantic vector search (pgvector)                       |
|   - Sparse keyword search (BM25 / PostgreSQL Full-Text)           |
|   - Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranking        |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                    Generation & Grounding                         |
|   - Prompt synthesis with retrieved context chunks                |
|   - LLM answer generation                                         |
|   - Automatic verifiable legal Citation extraction                |
+-------------------------------------------------------------------+
```

---

## Component Implementation Status

| Component | Status | Details |
|---|---|---|
| Repository & Tooling | **Implemented (Phase 1)** | `pyproject.toml`, `docker-compose.yml`, `ruff`, `mypy`, `pytest` |
| Application Settings | **Implemented (Phase 1)** | Typed `Pydantic` settings loading from `.env` |
| Domain Models | **Implemented (Phase 1)** | Pure Python entities (`Regulation`, `Document`, `Section`, `Chunk`, `Citation`) |
| Provider Abstractions | **Implemented (Phase 1)** | Python `Protocol` interfaces for Loader, Parser, Embedding, Retriever, Reranker, LLM |
| Database Infrastructure | **Implemented (Phase 1)** | PostgreSQL 16 + `pgvector` container & Alembic baseline migration |
| API Foundation | **Implemented (Phase 1)** | FastAPI application exposing lightweight `GET /health` endpoint |
| Document Ingestion | *Planned (Phase 2)* | Web scraping, metadata extraction, and PDF downloading |
| Document Processing | *Planned (Phase 2)* | Structure parsing into articles/sections and token chunking |
| Persistence Schema | *Planned (Phase 2)* | Business ORM models and tables (`documents`, `sections`, `chunks`, `embeddings`) |
| Vector Indexing | *Planned (Phase 3)* | Embedding generation and `pgvector` index creation |
| Hybrid Retrieval | *Planned (Phase 3)* | Combined dense vector search and sparse keyword retrieval |
| Cross-Encoder Reranking | *Planned (Phase 3)* | Context re-scoring and filtering |
| Grounded Generation | *Planned (Phase 4)* | LLM integration and citation formatting |
| RAG Evaluation | *Planned (Phase 5)* | RAG triad evaluation (faithfulness, answer relevance, context precision) |

---

## Key Design Principles

1. **Vendor Agnosticism**: All external AI providers (embeddings, LLMs, rerankers) interact with the core domain via abstract Python protocols (`EmbeddingProvider`, `LLMProvider`, `Reranker`). No hardcoded framework or vendor lock-in.
2. **Strict Data Lineage**: Grounded answers must map directly back to exact regulation numbers, articles (*Pasal*), clauses (*Ayat*), and official source URLs.
3. **No Heavy Framework Overhead**: Core logic is built directly using standard library typing and lightweight frameworks (FastAPI, Pydantic, SQLAlchemy), avoiding opaque orchestration frameworks like LangChain or LlamaIndex.
