# FinReg Intelligence RAG: Skema Basis Data & Model Provensi Kanonikal

## 1. Ringkasan Skema Relasional (PostgreSQL + pgvector)

Skema basis data dirancang untuk menyimpan metadata resmi peraturan, versi dokumen, hirarki node dokumen, dan chunk siap pencarian (*retrieval chunks*).

### Tabel Utama:
1. `regulations`: Registry resmi peraturan Bank Indonesia dan OJK.
2. `document_versions`: Versi dokumen dengan hash PDF dan tanggal berlaku.
3. `document_nodes`: Pohon node hirarkis (`BAB`, `Pasal`, `Ayat`, `Huruf`, `Angka`).
4. `retrieval_chunks`: Chunk teks semantik dengan kolom vektor (`vector(1536)`) dan teks lengkap (`tsvector`).

---

## 2. Indeksasi & Optimasi Performa

- **Indeks Vektor HNSW**: Indeks `pgvector` HNSW (`vector_cosine_ops`, $m=16, ef\_construction=64$).
- **Indeks Teks Lengkap GIN**: Indeks GIN pada kolom `fts_document` dengan konfigurasi bahasa Indonesia.
- **Identitas Kanonikal Hukum**: Identitas 4-tuple `(document_id, normalized_path, page_start, page_end)`.
