# Model Data & Entitas Domain — FinReg Intelligence

## Gambaran Umum

Dokumen ini menjelaskan entitas domain utama, value object, dan konseptual skema relasional untuk **FinReg Intelligence**.

> [!IMPORTANT]
> Sesuai dengan prinsip rekayasa Fase 1, model domain diimplementasikan sebagai **dataclass/skema Pydantic Python murni** di `src/finreg/domain/models.py` yang independen dari pemrosesan basis data. Tabel basis data untuk entitas bisnis secara sengaja ditunda hingga Fase 2+.

---

## Entitas Domain Utama (Terimplementasi Fase 1)

### 1. `Regulation`
Mewakili entitas regulasi keuangan resmi Indonesia.

- **`id`** (`UUID`): Kunci utama unik.
- **`issuer`** (`IssuerType`): Otoritas pengatur (`BI`, `OJK`, `LPS`, `KEMENKEU`).
- **`regulation_number`** (`str`): Nomor regulasi resmi (misalnya `23/13/PBI/2021`, `12/POJK.03/2020`).
- **`title`** (`str`): Judul lengkap regulasi.
- **`category`** (`str`): Klasifikasi regulasi (misalnya Peraturan BI, POJK, SE OJK).
- **`effective_date`** (`date`, opsional): Tanggal pengundangan atau keberlakuan efektif.
- **`is_active`** (`bool`): Indikator status aktif/berlaku.
- **`metadata`** (`Dict[str, Any]`): Metadata JSON fleksibel.

### 2. `Document` & `DocumentVersion`
Lacak metadata berkas mentah, URL sumber, dan rekam jejak versi.

- **`Document`**: Penghubung antara `Regulation` dan berkas fisik.
  - `id` (`UUID`), `regulation_id` (`UUID`), `file_name` (`str`), `file_type` (`str`), `source_url` (`HttpUrl`).
- **`DocumentVersion`**: Versi rekam jejak (*snapshot*) dokumen yang tidak dapat diubah (*immutable*).
  - `id` (`UUID`), `document_id` (`UUID`), `version_number` (`int`), `checksum_sha256` (`str`), `file_size_bytes` (`int`), `raw_metadata` (`Dict[str, Any]`).

### 3. `Section`
Mewakili hierarki struktural regulasi (Bab, Pasal, Ayat).

- **`id`** (`UUID`): Identifikasi seksi unik.
- **`document_version_id`** (`UUID`): Referensi ke *snapshot* dokumen induk.
- **`parent_section_id`** (`UUID`, opsional): ID referensi diri untuk sub-seksi bersarang.
- **`level`** (`int`): Indeks kedalaman hierarki (1=Bab, 2=Pasal, 3=Ayat).
- **`title`** (`str`): Judul struktural (misalnya `Pasal 5 Ayat (1)`).
- **`content`** (`str`): Teks isi seksi.
- **`order_index`** (`int`): Indeks urutan dalam dokumen.

### 4. `Chunk`
Unit dasar indeksasi teks dan embedding vektor.

- **`id`** (`UUID`): Identifikasi chunk unik.
- **`section_id`** (`UUID`): Referensi ke `Section` induk.
- **`content`** (`str`): Isi teks chunk.
- **`token_count`** (`int`): Jumlah panjang token.
- **`position_index`** (`int`): Posisi urutan dalam seksi.
- **`chunk_hash`** (`str`): Hash konten untuk pemeriksaan deduplikasi.

### 5. `RegulationRelationship`
Meringkas hubungan hukum antar regulasi.

- **`id`** (`UUID`): Identifikasi hubungan unik.
- **`source_regulation_id`** (`UUID`): Regulasi asal.
- **`target_regulation_id`** (`UUID`): Regulasi sasaran.
- **`relationship_type`** (`RelationshipType`): `AMENDS`, `REVOKES`, `IMPLEMENTS`, `REFERENCES`, `SUPERSEDES`.

### 6. `Citation`
Value object yang mewakili sitasi hukum terverifikasi yang dikembalikan bersama jawaban RAG.

- **`regulation_number`** (`str`): Teks nomor regulasi.
- **`section_title`** (`str`): Referensi seksi / pasal.
- **`text_snippet`** (`str`): Kutipan teks terverifikasi.
- **`source_url`** (`str`, opsional): Tautan web sumber resmi publik.

---

## Peta Jalan Migrasi Basis Data (Fase 2+)

Fase mendatang akan memperkenalkan pemetaan SQLAlchemy ORM dan migrasi skema Alembic untuk persistensi basis data:

```
Fase 2:
├── Tabel: documents
├── Tabel: document_versions
├── Tabel: sections
└── Tabel: chunks

Fase 3:
├── Tabel: chunk_embeddings (PostgreSQL + ekstensi pgvector)
└── Tabel: regulation_relationships

Fase 5:
├── Tabel: retrieval_logs
└── Tabel: evaluation_results
```
