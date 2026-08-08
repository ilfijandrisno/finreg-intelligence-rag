# Model Data & Entitas Domain — FinReg Intelligence

## Gambaran Umum

Dokumen ini menjelaskan entitas domain utama, value object, dan skema basis data relasional untuk **FinReg Intelligence**.

---

## Skema Registri Basis Data Relasional (Terimplementasi Fase 2)

Fase 2 memperkenalkan tabel persistensi basis data untuk melacak rekam jejak ingesti regulasi, metadata, dokumen, dan riwayat versi.

```
                    ┌────────────────────────┐
                    │      regulations       │
                    ├────────────────────────┤
                    │ id (PK)                │
                    │ source                 │
                    │ regulation_type        │
                    │ regulation_number      │
                    │ title                  │
                    │ sector                 │
                    │ subsector              │
                    │ status                 │
                    │ published_date         │
                    │ effective_date         │
                    │ detail_url             │
                    │ summary                │
                    │ abstract               │
                    │ created_at             │
                    │ updated_at             │
                    └───────────┬────────────┘
                                │ 1
                                │
                                │ N
                    ┌───────────┴────────────┐
                    │       documents        │
                    ├────────────────────────┤
                    │ id (PK)                │
                    │ regulation_id (FK)     │
                    │ document_type          │
                    │ document_url           │
                    │ filename               │
                    │ content_type           │
                    │ content_length         │
                    │ sha256                 │
                    │ storage_path           │
                    │ retrieved_at           │
                    │ created_at             │
                    └───────────┬────────────┘
                                │ 1
                                │
                                │ N
                    ┌───────────┴────────────┐
                    │   document_versions    │
                    ├────────────────────────┤
                    │ id (PK)                │
                    │ document_id (FK)       │
                    │ sha256                 │
                    │ storage_path           │
                    │ content_length         │
                    │ first_seen_at          │
                    │ last_seen_at           │
                    │ is_current             │
                    └────────────────────────┘
```

---

## Spesifikasi Tabel Basis Data

### 1. Tabel `regulations`
Menyimpan metadata regulasi resmi yang di-ingest dari portal BI dan OJK.

- **`id`** (`UUID`, PK): Kunci utama unik.
- **`source`** (`VARCHAR(10)`): Otoritas pengatur (`BI`, `OJK`).
- **`regulation_type`** (`VARCHAR(20)`): Tipe regulasi (`PBI`, `POJK`).
- **`regulation_number`** (`VARCHAR(100)`): Nomor regulasi resmi (misalnya `23/13/PBI/2021`, `12/POJK.03/2020`).
- **`title`** (`TEXT`): Judul lengkap regulasi.
- **`sector`** (`VARCHAR(150)`, opsional): Taksonomi sektor keuangan.
- **`subsector`** (`VARCHAR(150)`, opsional): Taksonomi subsektor.
- **`status`** (`VARCHAR(100)`, opsional): Teks status hukum dari sumber.
- **`published_date`** (`DATE`, opsional): Tanggal publikasi.
- **`effective_date`** (`DATE`, opsional): Tanggal keberlakuan efektif.
- **`detail_url`** (`TEXT`): URL halaman detail portal resmi.
- **`summary`** (`TEXT`, opsional): Ringkasan singkat.
- **`abstract`** (`TEXT`, opsional): Teks abstrak lengkap.
- **`created_at`** (`TIMESTAMPTZ`): Stempel waktu pembuatan rekaman.
- **`updated_at`** (`TIMESTAMPTZ`): Stempel waktu pembaruan rekaman.

**Batasan & Indeks**:
- `UNIQUE(source, regulation_type, regulation_number)` (`uq_regulations_source_type_num`)
- `INDEX(source, regulation_type)` (`idx_regulations_source_type`)
- `INDEX(detail_url)` (`idx_regulations_detail_url`)

---

### 2. Tabel `documents`
Melacak referensi dokumen lampiran yang terkait dengan regulasi.

- **`id`** (`UUID`, PK): Kunci utama unik.
- **`regulation_id`** (`UUID`, FK -> `regulations.id`): Identifikasi regulasi induk.
- **`document_type`** (`VARCHAR(50)`): Klasifikasi lampiran (`regulation`, `faq`, `abstract`, `other`).
- **`document_url`** (`TEXT`): URL pengunduhan langsung.
- **`filename`** (`VARCHAR(255)`): Teks nama berkas.
- **`content_type`** (`VARCHAR(100)`): Tipe MIME (misalnya `application/pdf`).
- **`content_length`** (`BIGINT`, opsional): Ukuran berkas dalam bita (*bytes*).
- **`sha256`** (`VARCHAR(64)`, opsional): Checksum SHA-256 terbaru.
- **`storage_path`** (`TEXT`, opsional): Jalur penyimpanan ke berkas PDF mentah aktif.
- **`retrieved_at`** (`TIMESTAMPTZ`, opsional): Stempel waktu pengambilan terakhir.
- **`created_at`** (`TIMESTAMPTZ`): Stempel waktu pembuatan rekaman.

**Batasan & Indeks**:
- `UNIQUE(regulation_id, document_type, document_url)` (`uq_documents_reg_type_url`)

---

### 3. Tabel `document_versions`
Mempertahankan rekam jejak sejarah yang tidak dapat diubah dari konten dokumen mentah.

- **`id`** (`UUID`, PK): Kunci utama versi unik.
- **`document_id`** (`UUID`, FK -> `documents.id`): Identifikasi dokumen induk.
- **`sha256`** (`VARCHAR(64)`): Checksum SHA-256 dari konten mentah.
- **`storage_path`** (`TEXT`): Jalur penyimpanan (`data/raw/{source}/{type}/{doc_id}/{sha256}.pdf`).
- **`content_length`** (`BIGINT`): Ukuran bita konten.
- **`first_seen_at`** (`TIMESTAMPTZ`): Stempel waktu penemuan pertama.
- **`last_seen_at`** (`TIMESTAMPTZ`): Stempel waktu pengamatan terbaru.
- **`is_current`** (`BOOLEAN`): True jika versi ini mewakili versi aktif saat ini.

**Batasan & Indeks**:
- `UNIQUE(document_id, sha256)` (`uq_document_versions_doc_sha256`)
- `INDEX(sha256)` (`idx_document_versions_sha256`)
- **Indeks Unik Parsial**:
  ```sql
  CREATE UNIQUE INDEX uq_document_versions_current ON document_versions (document_id) WHERE is_current = TRUE;
  ```
  *Memastikan invarian bahwa paling banyak satu versi per dokumen yang ditandai sebagai versi aktif (is_current = True).*

---

## Peta Jalan Migrasi Basis Data (Fase 3+)

Fase mendatang akan memperkenalkan pemrosesan dokumen dan tabel pencarian vektor:

```
Fase 3:
├── Tabel: sections (Hierarki struktural Bab / Pasal / Ayat)
├── Tabel: chunks (Konten chunk token berdasarkan posisi)
├── Tabel: chunk_embeddings (Embedding vektor pgvector)
└── Tabel: regulation_relationships (Silsilah hukum: mengubah, mencabut)

Fase 5:
├── Tabel: retrieval_logs
└── Table: evaluation_results
```
