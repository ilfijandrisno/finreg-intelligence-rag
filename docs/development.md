# Developer Setup & Contribution Guide — FinReg Intelligence

## Development Environment Setup

### Prerequisites
- **Python**: Version 3.11 or higher
- **Docker & Docker Compose**: For local PostgreSQL 16 + `pgvector` container infrastructure
- **Git**: For version control

---

## Quickstart Step-by-Step

### 1. Clone & Environment Configuration

```bash
git clone https://github.com/ilfijandrisno/finreg-intelligence-rag.git
cd finreg-intelligence-rag

# Copy environment template
cp .env.example .env
```

### 2. Create Virtual Environment & Install Dependencies

Using Python `venv`:

```bash
python -m venv .venv

# On Linux/macOS
source .venv/bin/activate

# On Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"
```

---

## Local Infrastructure & Database

### 1. Start PostgreSQL + pgvector Container

```bash
docker compose up -d
```

Verify container status:

```bash
docker compose ps
```

### 2. Apply Alembic Database Migrations

Apply migrations (001_baseline_pgvector, 002_ingestion_registry):

```bash
alembic upgrade head
```

Verify current migration revision:

```bash
alembic current
```

---

## Running Data Ingestion & Live Smoke Tests

### 1. Execute Ingestion CLI

Run discovery and metadata resolution in dry-run mode (no database or disk writes):

```bash
python -m finreg.ingestion.cli --source bi --limit 5 --dry-run
```

Run live data ingestion for Bank Indonesia (PBI) or OJK (POJK):

```bash
# Ingest Bank Indonesia PBI regulations
python -m finreg.ingestion.cli --source bi --limit 10

# Ingest OJK POJK regulations
python -m finreg.ingestion.cli --source ojk --limit 10

# Ingest all supported sources
python -m finreg.ingestion.cli --source all --limit 10
```

### 2. Run Live Ingestion Smoke Test

Execute the standalone live smoke test script against official portals to verify network connectivity, adapter resolution, and idempotency:

```bash
python scripts/smoke_test_ingestion.py --source all --limit 2
```

---

## Testing & Quality Control Commands

### 1. Run Automated Test Suite

```bash
pytest
```

Note: Live network tests are excluded from normal `pytest` execution and use local HTML fixtures.

### 2. Code Linting & Formatting Check

Run Ruff linter:

```bash
ruff check .
```

Run Ruff code formatter check:

```bash
ruff format --check .
```

To automatically format code:

```bash
ruff format .
```

### 3. Static Type Checking

Run mypy type checker across source code:

```bash
mypy src
```

---

## Engineering Guidelines

1. **No Secrets in Git**: Never commit `.env` or credentials. Always use `.env.example` placeholders.
2. **Interface First**: Maintain protocol definitions in `protocols.py` when introducing new ingestion or retrieval components.
3. **No Fake Tests or Data**: Ensure tests reflect real validation contracts without mock bloat.
4. **Idempotency & Clean Lineage**: Ingestion runs must be idempotent. Raw PDFs are saved to `data/raw/` and excluded from Git via `.gitignore`.
