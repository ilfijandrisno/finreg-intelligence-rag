# ADR 001: Hybrid Reciprocal Rank Fusion (RRF) Retrieval

## Status
**Accepted**

## Context
Indonesian financial regulations issued by Bank Indonesia (BI) and the Financial Services Authority (OJK) present dual challenges for retrieval systems:
1. **Specific Technical Nomenclature**: Legal texts contain precise codes, article identifiers (`Pasal 1 ayat (1) huruf b`), regulation numbers (`PBI No. 20/2026`), and acronyms (`DPB`, `OPB`, `RGI`, `SBN`) that dense vector models frequently miss or misrank.
2. **Semantic Conceptual Queries**: User queries often inquire about broader legal concepts (e.g., "persyaratan transaksi lindung nilai valas") where exact lexical matching alone fails to capture paraphrased legal provisions.

Relying exclusively on dense vector search or lexical BM25 search creates distinct failure modes:
- **Dense Vector Search Only**: Struggles with exact article numbers and legal acronyms; subject to embedding model vocabulary limits.
- **Lexical BM25 Search Only**: Fails on conceptual paraphrase queries and synonym variations.

## Decision
We implement a **Multi-Stage Hybrid Retrieval Engine** combining:
1. **Dense Vector Search**: PostgreSQL `pgvector` with HNSW cosine similarity indexes (`vector_cosine_ops`), executing embedding similarity over 1536-dimensional vectors.
2. **Lexical Full-Text Search**: PostgreSQL `tsvector` with GIN indexes using Indonesian text search configurations (`indonesian` dictionary).
3. **Reciprocal Rank Fusion (RRF)**: Merging dense and lexical ranked candidate lists using RRF with a standard smoothing constant $k=60$:

$$RRF\_Score(d) = \sum_{m \in \{dense, lexical\}} \frac{1}{k + rank_m(d)}$$

## Consequences
### Positive
- **Improved Recall**: Captures both exact legal markers (via BM25) and semantic legal concepts (via Dense Vector).
- **Scale Invariance**: RRF operates on ranks rather than raw uncalibrated similarity scores, avoiding distance normalization distortion across vector vs. BM25 score distributions.
- **Modularity**: Allows independent tuning of vector top-$K$ and BM25 top-$K$ candidates before fusion.

### Negative / Trade-offs
- Requires maintaining dual indexes in PostgreSQL (`HNSW` on vector column, `GIN` on `tsvector` column).
- Two parallel database queries per retrieval request before in-memory RRF fusion.
