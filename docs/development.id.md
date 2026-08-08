# Panduan Pengembangan & Penyiapan Lokal — FinReg Intelligence

## Penyiapan Lingkungan Pengembangan

### Prasyarat
- **Python**: Versi 3.11 atau lebih tinggi
- **Docker & Docker Compose**: Untuk kontainer PostgreSQL 16 + `pgvector` lokal
- **Git**: Untuk kontrol versi

---

## Langkah Cepat Memulai

### 1. Kloning & Konfigurasi Lingkungan

```bash
git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
cd finreg-intelligence-rag

# Salin templat lingkungan
cp .env.example .env
```

### 2. Buat Virtual Environment & Pasang Dependensi

Menggunakan Python `venv`:

```bash
python -m venv .venv

# Pada Linux/macOS
source .venv/bin/activate

# Pada Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Pasang paket dalam mode teredit beserta dependensi pengembang
pip install -e ".[dev]"
```

---

## Infrastruktur Lokal & Basis Data

### 1. Jalankan Kontainer PostgreSQL + pgvector

```bash
docker compose up -d
```

Verifikasi status kontainer:

```bash
docker compose ps
```

### 2. Terapkan Migrasi Basis Data Alembic

Terapkan migrasi basis data (001_baseline_pgvector, 002_ingestion_registry):

```bash
alembic upgrade head
```

Verifikasi revisi migrasi saat ini:

```bash
alembic current
```

---

## Menjalankan Ingesti Data & Smoke Test

### 1. Jalankan CLI Ingesti

Jalankan penemuan dan resolusi metadata dalam mode simulasi (*dry-run* tanpa penulisan basis data atau berkas):

```bash
python -m finreg.ingestion.cli --source bi --limit 5 --dry-run
```

Jalankan ingesti data langsung untuk Bank Indonesia (PBI) atau OJK (POJK):

```bash
# Ingesti regulasi Peraturan Bank Indonesia (PBI)
python -m finreg.ingestion.cli --source bi --limit 10

# Ingesti regulasi Peraturan OJK (POJK)
python -m finreg.ingestion.cli --source ojk --limit 10

# Ingesti seluruh sumber yang didukung
python -m finreg.ingestion.cli --source all --limit 10
```

### 2. Jalankan Smoke Test Ingesti Langsung

Jalankan skrip smoke test mandiri untuk menguji konektivitas jaringan portal resmi, resolusi adapter, dan idempotensi:

```bash
python scripts/smoke_test_ingestion.py --source all --limit 2
```

---

## Perintah Pengujian & Kontrol Kualitas

### 1. Jalankan Pengujian Unit Otomatis

```bash
pytest
```

Catatan: Pengujian jaringan langsung dikecualikan dari eksekusi `pytest` standar dan menggunakan fixture HTML lokal.

### 2. Pemeriksaan Linting & Format Kode

Jalankan linter Ruff:

```bash
ruff check .
```

Jalankan pemeriksaan format kode Ruff:

```bash
ruff format --check .
```

Untuk memformat kode secara otomatis:

```bash
ruff format .
```

### 3. Pemeriksaan Tipe Statis

Jalankan pemeriksa tipe mypy di seluruh kode sumber:

```bash
mypy src
```

---

## Panduan Rekayasa

1. **Tanpa Kredensial di Git**: Jangan pernah memasukkan `.env` atau kredensial ke repositori. Selalu gunakan placeholder di `.env.example`.
2. **Utamakan Antarmuka (Interface First)**: Pertahankan definisi protokol di `protocols.py` saat memperkenalkan komponen ingesti atau pencarian baru.
3. **Tanpa Pengujian atau Data Palsu**: Pastikan pengujian mencerminkan kontrak validasi nyata tanpa bloat *mock*.
4. **Idempotensi & Rekam Jejak Bersih**: Proses ingesti harus bersifat idempotent. Berkas PDF mentah disimpan ke `data/raw/` dan dikecualikan dari Git melalui `.gitignore`.
