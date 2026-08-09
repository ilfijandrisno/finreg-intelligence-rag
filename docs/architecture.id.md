# FinReg Intelligence RAG: Arsitektur Sistem & Aliran Data

**Bahasa:** 🇮🇩 Bahasa Indonesia · [🇬🇧 English](architecture.md)

## 1. Ringkasan Sistem

FinReg Intelligence RAG adalah platform legal technology berorientasi produksi yang dirancang untuk ingestion otomatis, hybrid indexing, reranking, dan question answering berbasis grounding atas peraturan keuangan Indonesia yang diterbitkan oleh Bank Indonesia (BI) dan Otoritas Jasa Keuangan (OJK).

Platform ini menerapkan provenance hukum yang ketat, sitasi inline yang dapat diverifikasi, isolasi batas konteks, serta safeguards abstention eksplisit berbasis ambang skor.

---

## 2. Arsitektur Sistem End-to-End

```mermaid
flowchart TD
    subgraph Ingestion["Fase 2 & 3: Pipeline Ingestion & Dokumen"]
        PDF["PDF Regulasi Mentah"] --> Extractor["PyMuPDF Reader"]
        Extractor --> Normalizer["Text Normalizer & Cleaner"]
        Normalizer --> Parser["Context-Aware State-Machine Parser"]
        Parser --> Tree["Pohon Dokumen Hirarkis (Nodes)"]
        Tree --> Chunker["Semantic Legal Chunker (Maks. 1500 karakter)"]
        Chunker --> DB_Chunks[("PostgreSQL: retrieval_chunks")]
    end

    subgraph Indexing["Fase 4: Multi-Vector Indexing"]
        DB_Chunks --> HNSW["HNSW Vector Index (cosine)"]
        DB_Chunks --> GIN["Full-Text Search GIN Index (tsvector)"]
    end

    subgraph Retrieval["Fase 4 & 5: Multi-Stage Hybrid Search"]
        UserQuery["Kueri Pengguna"] --> VectorSearch["VectorSearchService (HNSW)"]
        UserQuery --> LexicalSearch["LexicalSearchService (tsvector)"]
        VectorSearch --> RRF["Hybrid RRF Fusion (k=60)"]
        LexicalSearch --> RRF
        RRF --> Reranker["RerankingService (BAAI/bge-reranker-v2-m3)"]
    end

    subgraph Generation["Fase 6 & 7: Grounded RAG & FastAPI"]
        Reranker --> Gate{"Top Score >= Threshold (0.30)?"}
        Gate -- Tidak --> Abstain["Abstain Response (Jawaban Kosong)"]
        Gate -- Ya --> PromptBuilder["Prompt Assembler & Context Isolation"]
        PromptBuilder --> LLM["LLM Provider (gpt-4o-mini / Mock)"]
        LLM --> CitVal["Citation Validator (Regex [C1])"]
        CitVal --> FastApi["FastAPI REST Endpoint (/api/v1/rag/query)"]
    end
```

---

## 3. Sequence Hybrid Retrieval Multi-Tahap & Reranking

```mermaid
sequenceDiagram
    autonumber
    actor Client as API Client
    participant API as FastAPI Router
    participant RAG as RAGService
    participant Rerank as RerankingService
    participant Hybrid as HybridRetrievalService
    participant Vector as VectorSearchService
    participant Lexical as LexicalSearchService
    participant DB as PostgreSQL Database

    Client->>API: POST /api/v1/rag/query { query }
    API->>RAG: search_and_generate(query)
    RAG->>Rerank: search(query, top_n=5, hybrid_top_k=20)
    Rerank->>Hybrid: search(query, top_k=20)

    par Dense Vector Search
        Hybrid->>Vector: search(query, top_k=20)
        Vector->>DB: Cosine Similarity Query (HNSW)
        DB-->>Vector: Dense Vector Results
    and Lexical Full-Text Search
        Hybrid->>Lexical: search(query, top_k=20)
        Lexical->>DB: tsvector Websearch Query (GIN)
        DB-->>Lexical: BM25 Lexical Results
    end

    Vector-->>Hybrid: Dense Ranked List
    Lexical-->>Hybrid: Lexical Ranked List
    Hybrid->>Hybrid: Apply Reciprocal Rank Fusion (RRF k=60)
    Hybrid-->>Rerank: Top-20 Hybrid Candidates

    Rerank->>Rerank: BAAI/bge-reranker-v2-m3 Batch Scoring
    Rerank-->>RAG: Top-5 Reranked Results

    alt Top Score < Minimum Threshold (0.30)
        RAG-->>API: Abstained GenerationResult
        API-->>Client: HTTP 200 { abstained: true, answer: "" }
    else Top Score >= Threshold
        RAG->>RAG: Assemble Context Blocks & Call LLM
        RAG->>RAG: Deterministic Regex Citation Validation ([C1])
        RAG-->>API: Validated GenerationResult
        API-->>Client: HTTP 200 { answer, citations, report }
    end
```

---

## 4. State Machine Enforcement Grounded RAG Fase 6

```mermaid
stateDiagram-v2
    [*] --> QueryReceived: User Query Input
    QueryReceived --> HybridRetrieval: Execute Phase 4C Hybrid RRF Search
    HybridRetrieval --> NeuralReranking: Execute Phase 5 Cross-Encoder Rerank
    NeuralReranking --> ThresholdCheck: Check Top Candidate Score

    state ThresholdCheck {
        [*] --> ScoreEvaluated
        ScoreEvaluated --> InsufficientScore: Score < 0.30
        ScoreEvaluated --> SufficientScore: Score >= 0.30
    }

    InsufficientScore --> AbstainOutput: Return Abstained Response (Safety Safeguard)
    SufficientScore --> LLMGeneration: Prompt LLM with Sealed Context Blocks

    LLMGeneration --> CitationValidation: Parse Inline Citations [C1]

    state CitationValidation {
        [*] --> RegexParsing
        RegexParsing --> ProvenanceCheck: Validate Citation Context IDs
        ProvenanceCheck --> ValidationPassed: All Tags Valid & Context Bound
        ProvenanceCheck --> ValidationFailed: Invalid Tag or Citation Hallucination
    }

    ValidationFailed --> AbstainOutput: Suppress Answer & Abstain
    ValidationPassed --> FinalOutput: Deliver Grounded Answer & Citations
    AbstainOutput --> [*]
    FinalOutput --> [*]
```

---

## 5. Ringkasan Technology Stack

- **Bahasa Utama**: Python 3.11+
- **Ekstraksi PDF**: PyMuPDF (`fitz`)
- **Parser Engine**: Custom Regex Context-Aware State-Machine Parser
- **Database Layer**: PostgreSQL 16 + `pgvector`
- **Vector Search Index**: HNSW (`vector_cosine_ops`, $m=16, ef\_construction=64$)
- **Full-Text Index**: PostgreSQL `tsvector` GIN index (konfigurasi bahasa `indonesian`)
- **Neural Reranker**: `BAAI/bge-reranker-v2-m3` melalui HuggingFace `sentence-transformers` CrossEncoder
- **REST Framework**: FastAPI + Pydantic v2
- **Testing & Quality**: Pytest, Ruff, Mypy
