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

Atau menggunakan `uv` (direkomendasikan):

```bash
uv venv .venv
source .venv/bin/activate  # atau .\.venv\Scripts\Activate.ps1 pada Windows
uv pip install -e ".[dev]"
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

Terapkan migrasi basis (mengaktifkan ekstensi `pgvector`):

```bash
alembic upgrade head
```

Verifikasi revisi migrasi saat ini:

```bash
alembic current
```

---

## Menjalankan Layanan Aplikasi

### Jalankan Server Pengembangan FastAPI

```bash
uvicorn finreg.api.main:app --reload --host 0.0.0.0 --port 8000
```

Akses endpoint API di peramban atau HTTP client Anda:
- **Pemeriksaan Kesehatan**: `GET http://localhost:8000/health`
- **Dokumentasi Swagger OpenAPI**: `http://localhost:8000/docs`

---

## Perintah Pengujian & Kontrol Kualitas

### 1. Jalankan Pengujian Unit Otomatis

```bash
pytest
```

Jalankan dengan keluaran rinci:

```bash
pytest -v -s
```

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
