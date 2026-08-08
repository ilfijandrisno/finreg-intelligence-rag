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

Or using `uv` (recommended):

```bash
uv venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
uv pip install -e ".[dev]"
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

Apply the baseline migration (enables `pgvector` extension):

```bash
alembic upgrade head
```

Verify current migration revision:

```bash
alembic current
```

---

## Running Application Services

### Start FastAPI Development Server

```bash
uvicorn finreg.api.main:app --reload --host 0.0.0.0 --port 8000
```

Access API endpoints in your browser or HTTP client:
- **Health Check**: `GET http://localhost:8000/health`
- **Swagger OpenAPI Docs**: `http://localhost:8000/docs`

---

## Testing & Quality Control Commands

### 1. Run Automated Unit Tests

```bash
pytest
```

Run with detailed verbose output and coverage:

```bash
pytest -v -s
```

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
