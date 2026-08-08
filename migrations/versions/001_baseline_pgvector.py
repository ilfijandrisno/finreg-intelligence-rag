"""Baseline migration: enable pgvector extension.

Revision ID: 001_baseline_pgvector
Revises: None
Create Date: 2026-08-08 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_baseline_pgvector"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable pgvector extension in PostgreSQL."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    """Disable pgvector extension."""
    op.execute("DROP EXTENSION IF EXISTS vector;")
