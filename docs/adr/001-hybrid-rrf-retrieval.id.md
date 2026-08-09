# ADR 001: Retrieval Hybrid Reciprocal Rank Fusion (RRF)

**Bahasa:** 🇮🇩 Bahasa Indonesia · [🇬🇧 English](001-hybrid-rrf-retrieval.md)

## Status
**Diterima**

## Konteks
Regulasi keuangan Indonesia yang diterbitkan oleh Bank Indonesia (BI) dan Otoritas Jasa Keuangan (OJK) menghadirkan dua tantangan utama bagi sistem retrieval:
1. **Terminologi Teknis Spesifik**: Teks hukum berisi kode presisi, identitas pasal (`Pasal 1 ayat (1) huruf b`), nomor regulasi (`PBI No. 20/2026`), dan akronim (`DPB`, `OPB`, `RGI`, `SBN`) yang sering terlewat atau salah peringkat oleh model dense vector.
2. **Kueri Konseptual Semantik**: User sering menanyakan konsep hukum yang lebih luas (misalnya, "persyaratan transaksi lindung nilai valas") ketika pencocokan lexical saja gagal menangkap ketentuan hukum yang diparafrasekan.

Mengandalkan hanya dense vector search atau lexical BM25 menimbulkan failure mode yang berbeda:
- **Dense Vector Search Saja**: kesulitan menemukan nomor pasal dan akronim hukum secara tepat; bergantung pada vocabulary embedding model.
- **Lexical BM25 Saja**: gagal pada kueri parafrase konseptual dan variasi sinonim.

## Keputusan
Kami menerapkan **Multi-Stage Hybrid Retrieval Engine** yang menggabungkan:
1. **Dense Vector Search**: PostgreSQL `pgvector` dengan indeks HNSW cosine similarity (`vector_cosine_ops`) untuk similarity embedding pada vektor berdimensi 1536.
2. **Lexical Full-Text Search**: PostgreSQL `tsvector` dengan indeks GIN menggunakan konfigurasi text search bahasa Indonesia (`indonesian` dictionary).
3. **Reciprocal Rank Fusion (RRF)**: menggabungkan daftar kandidat dense dan lexical menggunakan RRF dengan konstanta smoothing standar $k=60$:

$$RRF\_Score(d) = \sum_{m \in \{dense, lexical\}} \frac{1}{k + rank_m(d)}$$

## Konsekuensi
### Positif
- **Recall lebih baik**: menangkap marker hukum exact melalui BM25 dan konsep hukum semantik melalui Dense Vector.
- **Scale invariance**: RRF beroperasi pada ranking, bukan raw similarity score yang tidak terkalibrasi, sehingga menghindari distorsi normalisasi antara distribusi score vector dan BM25.
- **Modularitas**: top-$K$ vector dan BM25 dapat dituning secara independen sebelum fusion.

### Negatif / Trade-off
- Memerlukan pemeliharaan dua indeks PostgreSQL (`HNSW` pada kolom vector dan `GIN` pada kolom `tsvector`).
- Membutuhkan dua query database paralel untuk setiap request retrieval sebelum in-memory RRF fusion.
