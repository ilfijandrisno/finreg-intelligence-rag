# FinReg Intelligence RAG: Phase 8 Evaluation Report & Failure Analysis

## 1. Overview & Evaluation Methodology

The Phase 8 evaluation framework measures multi-stage retrieval ranking quality and grounded answer generation fidelity for Bank Indonesia (BI) and OJK financial regulatory queries.

### Test Dataset Composition (`data/evaluation/benchmark_gold_dataset.json`)
- **Total Benchmark Samples**: 3 query evaluation samples.
- **In-Domain Retrieval Benchmark Population**: 2 samples (`eval-bi-valas-001` and `eval-bi-valas-002`) with annotated canonical relevance judgments ($rel \in \{0, 1, 2, 3\}$).
- **Out-of-Domain Safety Population**: 1 sample (`eval-out-of-domain-001`, query: *"peraturan mengenai penerbangan luar angkasa komersial"*, `expected_abstain: true`).
- **Population Separation**: Out-of-domain samples are excluded from retrieval ranking metric denominators to avoid metric dilution, but are 100% included in generation evaluation for measuring **Abstention Accuracy**.

---

## 2. Empirical Benchmark Results

### Retrieval Stage Metrics Summary

| Metric | Stage 1: Dense Vector (Phase 4A) [Non-production / Mock Embedding Benchmark] | Stage 2: BM25 Lexical (Phase 4B) | Stage 3: Hybrid RRF (Phase 4C) | Stage 4: Hybrid + Neural Reranker (Phase 5) |
| :--- | :---: | :---: | :---: | :---: |
| **MRR@1 / HitRate@1** | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| **MRR@5 / HitRate@5** | 0.0000 | **0.5000** | 0.2500 | **0.5000** |
| **MRR@10 / HitRate@10** | 0.0000 | **0.5000** | 0.2500 | **0.5000** |
| **nDCG@5** | 0.0000 | **0.1687** | 0.1064 | **0.1687** |
| **nDCG@10** | 0.0000 | **0.1687** | 0.1064 | **0.1687** |
| **Precision@5** | 0.0000 | **0.1000** | 0.1000 | **0.1000** |
| **Recall@5** | 0.0000 | **0.2500** | 0.2500 | **0.2500** |

### Phase 6 Generation & Grounding Metrics

| Metric Category | Metric Name | Score | Description |
| :--- | :--- | :---: | :--- |
| **Syntax & Validity** | Citation Validity | **100.00%** | Proportion of generated citation tags matching strict `[C1]` syntax |
| **Grounding Fidelity** | Citation Precision | **50.00%** | Proportion of cited context blocks matching target ground truth |
| | Citation Recall | **25.00%** | Proportion of target gold evidence cited in generation |
| | Grounding Coverage | **100.00%** | Proportion of generated answer claims containing citations |
| | Gold Claim Coverage | **0.00%** | Proportion of expected gold claims supported by citations |
| **Safety & Abstention**| Unsupported Claim Rate | **0.00%** | Proportion of ungrounded claims generated (Zero ungrounded claims) |
| | Abstention Accuracy | **100.00%** | Accuracy of system abstention on out-of-domain queries |

---

## 3. Deep Technical Failure Analysis

### Analysis 1: Dense Vector Retrieval 0.0000 Score
- **Root Cause**: In the benchmark test environment, the system operated under `MockEmbeddingProvider` (deterministic hash-seeded pseudo-random vector generation) because live OpenAI API keys are not supplied during offline benchmarking.
- **Interpretation**: The `0.0000` metric reflects pseudo-random vector ranking performance under the test mock provider, **not** production `OpenAIEmbeddingProvider` (`text-embedding-3-small`) retrieval capability.

### Analysis 2: Gold Claim Coverage 0.00% Traceability Analysis
- **Empirical Trace for Sample 1 (`eval-bi-valas-001`)**:
  - `Query`: *"transaksi pasar valuta asing lindung nilai"*
  - `Expected Gold Claim 1`: Expected citation of **`Pasal 1`** (`"BAB I/Pasal 1/Ayat (1)"`, page 2).
  - `RAG Service Generation`: Neural Reranker selected **`Pasal 16`** (`"BAB VI/Bagian Keempat/Pasal 16/Ayat (1)"`, page 7) as Context Block `[C1]`.
  - `Citation Tag Generated`: `[C1]` (referencing `Pasal 16`, page 7).
  - `Canonical Identity Comparison`: `citation_matches_gt(cit_Pasal16, gt_Pasal1)` evaluated `Pasal 16` vs `Pasal 1` $\rightarrow$ **`False`**.
- **Conclusion**: The metric logic evaluated correctly: `Gold Claim Coverage` is `0.00%` because the LLM cited `Pasal 16` instead of `Pasal 1`.

---

## 4. Phase 5 Provider Execution Confirmation

- **Provider**: `CrossEncoderRerankerProvider`
- **Model**: `BAAI/bge-reranker-v2-m3`
- **Execution Mode**: Production HuggingFace Transformer CrossEncoder
- **Candidate Pool**: 20 candidates from Phase 4C Hybrid RRF
- **Final Output Top-K**: 5 reranked chunks
- **Runtime Execution**: Confirmed live inference over candidates (`CrossEncoder.predict()` executed in ~28s).
