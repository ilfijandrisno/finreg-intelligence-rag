# FinReg Intelligence RAG: Laporan Evaluasi Fase 8 & Analisis Kegagalan

**Bahasa:** 🇮🇩 Bahasa Indonesia · [🇬🇧 English](eval-report.md)

## 1. Ringkasan & Metodologi Evaluasi

Framework evaluasi Fase 8 mengukur kualitas ranking retrieval multi-tahap dan fidelity generasi jawaban yang ter-grounding untuk kueri regulasi keuangan Bank Indonesia (BI) dan OJK.

### Komposisi Dataset Pengujian (`data/evaluation/benchmark_gold_dataset.json`)
- **Total Sampel Benchmark**: 3 sampel evaluasi kueri.
- **Populasi Benchmark Retrieval In-Domain**: 2 sampel (`eval-bi-valas-001` dan `eval-bi-valas-002`) dengan annotated canonical relevance judgments ($rel \in \{0, 1, 2, 3\}$).
- **Populasi Safety Out-of-Domain**: 1 sampel (`eval-out-of-domain-001`, kueri: *"peraturan mengenai penerbangan luar angkasa komersial"*, `expected_abstain: true`).
- **Pemisahan Populasi**: sampel out-of-domain dikeluarkan dari denominator metrik ranking retrieval untuk mencegah dilusi metrik, tetapi tetap 100% dimasukkan dalam evaluasi generation untuk mengukur **Abstention Accuracy**.

---

## 2. Hasil Benchmark Empiris

### Ringkasan Metrik Tahap Retrieval

| Metrik | Stage 1: Dense Vector (Phase 4A) [Non-production / Mock Embedding Benchmark] | Stage 2: BM25 Lexical (Phase 4B) | Stage 3: Hybrid RRF (Phase 4C) | Stage 4: Hybrid + Neural Reranker (Phase 5) |
| :--- | :---: | :---: | :---: | :---: |
| **MRR@1 / HitRate@1** | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| **MRR@5 / HitRate@5** | 0.0000 | **0.5000** | 0.2500 | **0.5000** |
| **MRR@10 / HitRate@10** | 0.0000 | **0.5000** | 0.2500 | **0.5000** |
| **nDCG@5** | 0.0000 | **0.1687** | 0.1064 | **0.1687** |
| **nDCG@10** | 0.0000 | **0.1687** | 0.1064 | **0.1687** |
| **Precision@5** | 0.0000 | **0.1000** | 0.1000 | **0.1000** |
| **Recall@5** | 0.0000 | **0.2500** | 0.2500 | **0.2500** |

### Metrik Generation & Grounding Fase 6

| Kategori Metrik | Nama Metrik | Skor | Deskripsi |
| :--- | :--- | :---: | :--- |
| **Syntax & Validity** | Citation Validity | **100.00%** | Proporsi tag sitasi yang dihasilkan dan sesuai syntax `[C1]` yang ketat |
| **Grounding Fidelity** | Citation Precision | **50.00%** | Proporsi context block yang dikutip dan sesuai dengan ground truth |
| | Citation Recall | **25.00%** | Proporsi evidence gold target yang dikutip dalam generation |
| | Grounding Coverage | **100.00%** | Proporsi claim jawaban yang dihasilkan dan memiliki sitasi |
| | Gold Claim Coverage | **0.00%** | Proporsi gold claim yang diharapkan dan didukung oleh sitasi |
| **Safety & Abstention** | Unsupported Claim Rate | **0.00%** | Proporsi claim tanpa grounding yang dihasilkan (nol claim ungrounded) |
| | Abstention Accuracy | **100.00%** | Akurasi sistem melakukan abstain pada kueri out-of-domain |

---

## 3. Analisis Kegagalan Teknis Mendalam

### Analisis 1: Dense Vector Retrieval dengan Skor 0.0000
- **Root Cause**: Pada lingkungan benchmark, sistem menggunakan `MockEmbeddingProvider` (pembuatan vektor pseudo-random berbasis hash yang deterministik) karena API key OpenAI live tidak disediakan selama benchmark offline.
- **Interpretasi**: Metrik `0.0000` mencerminkan performa ranking pseudo-random dari mock provider, **bukan** kemampuan retrieval production `OpenAIEmbeddingProvider` (`text-embedding-3-small`).

### Analisis 2: Gold Claim Coverage 0.00% — Analisis Traceability
- **Trace empiris untuk Sample 1 (`eval-bi-valas-001`)**:
  - `Query`: *"transaksi pasar valuta asing lindung nilai"*
  - `Expected Gold Claim 1`: sitasi yang diharapkan adalah **`Pasal 1`** (`"BAB I/Pasal 1/Ayat (1)"`, halaman 2).
  - `RAG Service Generation`: Neural Reranker memilih **`Pasal 16`** (`"BAB VI/Bagian Keempat/Pasal 16/Ayat (1)"`, halaman 7) sebagai Context Block `[C1]`.
  - `Citation Tag Generated`: `[C1]` (merujuk ke `Pasal 16`, halaman 7).
  - `Canonical Identity Comparison`: `citation_matches_gt(cit_Pasal16, gt_Pasal1)` mengevaluasi Pasal 16 vs Pasal 1 $ightarrow$ **`False`**.
- **Kesimpulan**: Logika metrik telah mengevaluasi dengan benar: `Gold Claim Coverage` adalah `0.00%` karena LLM mengutip `Pasal 16`, bukan `Pasal 1`.

---

## 4. Konfirmasi Eksekusi Provider Fase 5

- **Provider**: `CrossEncoderRerankerProvider`
- **Model**: `BAAI/bge-reranker-v2-m3`
- **Mode Eksekusi**: Production HuggingFace Transformer CrossEncoder
- **Candidate Pool**: 20 kandidat dari Phase 4C Hybrid RRF
- **Final Output Top-K**: 5 chunk hasil reranking
- **Runtime Execution**: Inferensi live terhadap kandidat terkonfirmasi (`CrossEncoder.predict()` dieksekusi sekitar 28 detik).
