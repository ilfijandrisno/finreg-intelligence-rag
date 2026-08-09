# FinReg Intelligence RAG: Enterprise Indonesian Financial Regulatory RAG Platform

**Language:** 🇬🇧 English · [🇮🇩 Bahasa Indonesia](README.id.md)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16+](https://img.shields.io/badge/PostgreSQL-16%2B%20%7C%20pgvector-blue)](https://github.com/pgvector/pgvector)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20API-green.svg)](https://fastapi.tiangolo.com/)
[![Ruff / Mypy Clean](https://img.shields.io/badge/Code%20Quality-Ruff%20%7C%20Mypy%20Strict-brightgreen)](https://github.com/astral-sh/ruff)
[![Docker Multi-Stage](https://img.shields.io/badge/Docker-Multi--Stage%20Non--Root-blue.svg)](Dockerfile)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, production-oriented Retrieval-Augmented Generation (RAG) platform engineered specifically for complex Indonesian financial regulations issued by **Bank Indonesia (BI)** and the **Financial Services Authority (OJK)**.

The system combines **hierarchical legal state-machine parsing**, **hybrid HNSW vector + BM25 lexical search**, **neural cross-encoder reranking**, **grounded generation with strict citation validation**, and a **containerized, CI-validated operational foundation**.

---

## 🌟 Engineering Highlights

1. **Context-Aware State-Machine Structural Parser**:
   - Custom AST-style legal parser that processes complex Indonesian regulatory structures (`BAB`, `Pasal`, `Ayat`, `Huruf`, `Angka`) into explicit hierarchical trees without third-party LLM parsing latency.
2. **Multi-Stage Hybrid Search (RRF $k=60$)**:
   - Merges 1536-dimensional dense vector embeddings (`pgvector` HNSW index) and Indonesian BM25 full-text search (`tsvector` GIN index) via Reciprocal Rank Fusion, preserving exact legal article lookup and semantic paraphrases.
3. **Neural Cross-Encoder Reranking**:
   - Integrates `BAAI/bge-reranker-v2-m3` via HuggingFace CrossEncoder to score candidate precision before LLM context assembly.
4. **Deterministic Grounding & Abstention Safeguards**:
   - Replaces non-deterministic LLM-as-a-judge approaches with deterministic regex citation parsing (`[C1]`), token budgeting, context leak prevention, prompt injection defenses, legal conflict handling, and early score-threshold abstention.
5. **Production Operational & Container Foundation**:
   - Multi-stage non-root `Dockerfile` (`python:3.11-slim`, `appuser` UID 10001), multi-container `docker-compose.yml`, GitHub Actions CI workflow, Prometheus metrics (`GET /metrics`), request tracing (`X-Request-ID`), and backward-compatible process `/health` vs PostgreSQL database `/readiness` checks.
6. **Auditable Evaluation Benchmark**:
   - Custom evaluation engine supporting MRR@K, HitRate@K, graded nDCG@K, Precision/Recall, Citation Validity, and Abstention Accuracy with evaluation-layer canonical path normalization.

---

## 🏛 System Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Ingestion["PDF Ingestion & Structural Parsing"]
        PDF["Raw Regulation PDF"] --> Extractor["PyMuPDF Extractor"]
        Extractor --> Normalizer["Line Normalizer"]
        Normalizer --> Parser["Context-Aware State-Machine Parser"]
        Parser --> Tree["Hierarchical Document Tree"]
        Tree --> Chunker["Semantic Legal Chunker (Max 1500 chars)"]
        Chunker --> DB[("PostgreSQL Database")]
    end

    subgraph Indexing["Multi-Vector Indexing"]
        DB --> HNSW["HNSW Vector Index (pgvector)"]
        DB --> GIN["Full-Text Search GIN Index (tsvector)"]
    end

    subgraph Retrieval["Multi-Stage Search & Reranking"]
        UserQuery["User Query"] --> VectorSearch["Vector Search (HNSW)"]
        UserQuery --> LexicalSearch["Lexical Search (BM25 GIN)"]
        VectorSearch --> RRF["Hybrid RRF Fusion (k=60)"]
        LexicalSearch --> RRF
        RRF --> Reranker["Cross-Encoder (BAAI/bge-reranker-v2-m3)"]
    end

    subgraph Generation["Grounded RAG & Safety"]
        Reranker --> Gate{"Top Score >= Threshold (0.30)?"}
        Gate -- No --> Abstain["Abstain (Empty Answer)"]
        Gate -- Yes --> LLM["LLM Provider (gpt-4o-mini / Mock)"]
        LLM --> CitVal["Regex Citation Validator ([C1])"]
        CitVal --> API["FastAPI Endpoint (/api/v1/rag/query)"]
    end

    subgraph Operations["Phase 10: Operations & Observability"]
        API --> Tracing["RequestTracingMiddleware (X-Request-ID)"]
        API --> Metrics["PrometheusMetricsMiddleware (GET /metrics)"]
        API --> Health["Process Liveness (GET /health)"]
        API --> Ready["Database Readiness (GET /readiness)"]
    end
```

Detailed architecture diagrams, sequence flowcharts, and state machines are documented in [docs/architecture.md](docs/architecture.md).

---

## 📊 Phase 8 Empirical Evaluation Benchmark Results

The system includes a custom mathematical evaluation engine executed via `python -m finreg.evaluation.cli`.

> **Note on Test Environment & Capabilities**:
> - **Production Capabilities**: `OpenAIEmbeddingProvider` (`text-embedding-3-small`), `CrossEncoderRerankerProvider` (`BAAI/bge-reranker-v2-m3`), `OpenAILLMProvider` (`gpt-4o-mini`).
> - **Offline Benchmark Fallbacks**: `MockEmbeddingProvider` (deterministic hash-seeded pseudo-random vectors) and `MockLLMProvider` (offline test stub).

### Retrieval Stage Metrics (In-Domain Population: $N=2$)

| Metric | Stage 1: Dense Vector (Phase 4A) [Non-production Mock] | Stage 2: BM25 Lexical (Phase 4B) | Stage 3: Hybrid RRF (Phase 4C) | Stage 4: Hybrid + Neural Reranker (Phase 5) |
| :--- | :---: | :---: | :---: | :---: |
| **MRR@1 / HitRate@1** | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| **MRR@5 / HitRate@5** | 0.0000 | **0.5000** | 0.2500 | **0.5000** |
| **nDCG@5** | 0.0000 | **0.1687** | 0.1064 | **0.1687** |
| **Precision@5** | 0.0000 | **0.1000** | 0.1000 | **0.1000** |
| **Recall@5** | 0.0000 | **0.2500** | 0.2500 | **0.2500** |

### Phase 6 Generation & Safety Metrics ($N=3$)

| Metric Name | Score | Technical Analysis |
| :--- | :---: | :--- |
| **Citation Validity** | **100.00%** | 100% of generated citation tags strictly follow `[C1]` regex syntax |
| **Citation Precision** | **50.00%** | 50% of cited context blocks match target canonical legal evidence |
| **Citation Recall** | **25.00%** | 25% of target gold evidence provisions cited in generation |
| **Grounding Coverage** | **100.00%** | 100% of answer claims contain valid citations |
| **Gold Claim Coverage** | **0.00%** | LLM cited `Pasal 16` (p. 7) instead of target `Pasal 1` (p. 2) for Claim 1 |
| **Unsupported Claim Rate** | **0.00%** | Zero ungrounded claims generated |
| **Abstention Accuracy** | **100.00%** | 100% accurate abstention on out-of-domain queries |

Full benchmark breakdowns, canonical identity traces, and failure analysis are documented in [docs/eval-report.md](docs/eval-report.md).

---

## 🛠 Local Setup, Docker & Reproducibility

### 1. Requirements & Docker Compose Execution
```bash
# Clone Repository
git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
cd finreg-intelligence-rag

# Start PostgreSQL 16 + pgvector & FastAPI Container Stack
docker compose up -d --build
```

### 2. Operational Probes & Metrics
```bash
# Check Liveness Probe (HTTP 200)
curl http://localhost:8000/health

# Check Database Readiness Probe (HTTP 200 / 503)
curl http://localhost:8000/readiness

# Scrape Prometheus Metrics (HTTP 200)
curl http://localhost:8000/metrics
```

### 3. Verify Code Quality & Offline Tests
```bash
# Run Pytest Suite inside Container (or local venv)
pytest

# Run Code Quality Checks
ruff check .
mypy src

# Execute Benchmark CLI
python -m finreg.evaluation.cli --dataset-path data/evaluation/benchmark_gold_dataset.json --output-dir data/evaluation/reports
```

---

## 📚 Documentation Index

- [Architecture & Data Flow](docs/architecture.md)
- [Database Schema & Data Model](docs/data-model.md)
- [Developer Setup & CLI Guide](docs/development.md)
- [Phase 10 Containerization & Deployment Readiness](docs/deployment-readiness.md) · [🇮🇩 ID](docs/deployment-readiness.id.md)
- [Evaluation Report & Failure Analysis](docs/eval-report.md) · [🇮🇩 ID](docs/eval-report.id.md)
- [ADR 001: Hybrid RRF Retrieval](docs/adr/001-hybrid-rrf-retrieval.md) · [🇮🇩 ID](docs/adr/001-hybrid-rrf-retrieval.id.md)
- [ADR 002: Deterministic Grounding & Abstention](docs/adr/002-deterministic-grounding.md) · [🇮🇩 ID](docs/adr/002-deterministic-grounding.id.md)
- [ADR 003: Canonical Identity Normalization](docs/adr/003-canonical-eval-identity.md) · [🇮🇩 ID](docs/adr/003-canonical-eval-identity.id.md)
- [Indonesian Version / Versi Bahasa Indonesia](README.id.md)

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
