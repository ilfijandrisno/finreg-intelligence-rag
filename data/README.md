# Data Governance & Regulatory Source Directory

## English

This directory serves as the root location for local regulatory dataset storage and metadata manifests.

### Data Governance Principles
1. **Official Sources Only**: All regulatory texts are sourced exclusively from official public regulatory portals:
   - **Bank Indonesia (BI)**: [https://www.bi.go.id](https://www.bi.go.id)
   - **Otoritas Jasa Keuangan (OJK)**: [https://www.ojk.go.id](https://www.ojk.go.id)
2. **Zero PDF Commit Policy**: Binary PDF files of financial regulations are **never** committed to Git repositories. They are maintained in local storage or object storage (S3/GCS).
3. **Traceability**: Raw and parsed regulatory documents retain full lineage, including original source URL, SHA-256 checksum, HTTP fetch timestamp, and issuing authority.
4. **Public Domain Compliance**: Content ingested consists solely of public regulatory acts, regulations, circular letters, and official guidance published for public compliance.

---

## Bahasa Indonesia

Direktori ini berfungsi sebagai lokasi utama penyimpanan dataset regulasi lokal dan manifes metadata.

### Prinsip Tata Kelola Data
1. **Hanya Sumber Resmi**: Seluruh teks regulasi diperoleh secara eksklusif dari portal resmi regulator publik:
   - **Bank Indonesia (BI)**: [https://www.bi.go.id](https://www.bi.go.id)
   - **Otoritas Jasa Keuangan (OJK)**: [https://www.ojk.go.id](https://www.ojk.go.id)
2. **Kebijakan Tanpa Berkas PDF di Git**: Berkas biner PDF regulasi keuangan **tidak pernah** dimasukkan ke dalam repositori Git. Berkas disimpan di media penyimpanan lokal atau penyimpanan objek (S3/GCS).
3. **Keterlacakan (Traceability)**: Dokumen regulasi mentah dan hasil olahan mempertahankan rekam jejak lengkap, mencakup URL sumber asli, *checksum* SHA-256, stempel waktu pengambilan HTTP, serta otoritas penerbit.
4. **Kepatuhan Domain Publik**: Konten yang di-ingest hanya terdiri dari undang-undang, peraturan, surat edaran, dan panduan resmi yang dipublikasikan untuk kepatuhan publik.
