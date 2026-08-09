# ADR 003: Identitas Kanonikal & Normalisasi Suffix Struktur pada Benchmark

**Bahasa:** 🇮🇩 Bahasa Indonesia · [🇬🇧 English](003-canonical-eval-identity.md)

## Status
**Diterima**

## Konteks
Evaluasi sistem legal retrieval membutuhkan pencocokan chunk hasil retrieval terhadap ground truth yang dianotasi manusia. Pada semantic legal chunking Fase 3B, node hukum yang panjang dapat dipecah menjadi beberapa text chunk. Engine chunking menambahkan suffix part pada `structural_path` yang tersimpan (misalnya `"BAB I/Pasal 1/Ayat (1) [Part 1/2]"`).

Membandingkan path ground truth (`"BAB I/Pasal 1/Ayat (1)"`) dengan structural path database (`"BAB I/Pasal 1/Ayat (1) [Part 1/2]"`) menggunakan exact string equality menghasilkan false-negative, meskipun dokumen, pasal, dan halaman yang benar telah ditemukan.

Sebaliknya, hanya menggunakan UUID chunk (`chunk_id`) membuat ground truth benchmark rapuh dan bergantung pada primary key database yang dapat berubah.

## Keputusan
Kami menetapkan **Canonical Legal Identity Schema** untuk evaluasi benchmark:
1. **Canonical Identity 4-Tuple**: evidence ground truth dan kandidat hasil retrieval diidentifikasi secara unik oleh:
   $$(document\_id, normalized\_structural\_path, page\_start, page\_end)$$
2. **Normalisasi Path pada Evaluation Layer**: evaluation layer menerapkan regex normalization (`PART_SUFFIX_REGEX = re.compile(r"\s*\[Part\s+\d+/\d+\]$")`) hanya di dalam fungsi pembanding benchmark (`canonical_matches()`, `citation_matches_gt()`).
3. **Immutability of Provenance**: structural path pada record database, `RetrievalChunk`, citation response API, dan RAG context block **tidak pernah dimutasi**.

## Konsekuensi
### Positif
- **Ground truth lebih robust**: benchmark bergantung pada atribut hukum yang stabil, bukan UUID database yang dapat berubah.
- **Evaluasi lebih akurat**: artifact suffix dari text splitter tidak mengganggu perhitungan metrik evaluasi.
- **Tanpa side effect**: string provenance yang ditampilkan oleh production API tetap 100% tidak berubah.

### Negatif / Trade-off
- Evaluation engine harus melakukan normalisasi structural path pada setiap langkah perbandingan.
