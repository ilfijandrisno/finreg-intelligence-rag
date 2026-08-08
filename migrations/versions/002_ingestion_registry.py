"""Ingestion registry tables (regulations, documents, document_versions) and partial unique index.

Revision ID: 002_ingestion_registry
Revises: 001_baseline_pgvector
Create Date: 2026-08-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_ingestion_registry"
down_revision: str | None = "001_baseline_pgvector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ingestion registry tables and constraints."""
    op.create_table(
        "regulations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("regulation_type", sa.String(length=20), nullable=False),
        sa.Column("regulation_number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("sector", sa.String(length=150), nullable=True),
        sa.Column("subsector", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("detail_url", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "regulation_type",
            "regulation_number",
            name="uq_regulations_source_type_num",
        ),
    )
    op.create_index(
        "idx_regulations_source_type",
        "regulations",
        ["source", "regulation_type"],
        unique=False,
    )
    op.create_index("idx_regulations_detail_url", "regulations", ["detail_url"], unique=False)

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("regulation_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("document_url", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("content_length", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["regulation_id"], ["regulations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "regulation_id",
            "document_type",
            "document_url",
            name="uq_documents_reg_type_url",
        ),
    )

    op.create_table(
        "document_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("content_length", sa.BigInteger(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "sha256", name="uq_document_versions_doc_sha256"),
    )
    op.create_index(
        "idx_document_versions_sha256",
        "document_versions",
        ["sha256"],
        unique=False,
    )

    # PostgreSQL partial unique index ensuring at most one current version per document_id
    op.execute(
        "CREATE UNIQUE INDEX uq_document_versions_current "
        "ON document_versions (document_id) WHERE is_current = TRUE;"
    )


def downgrade() -> None:
    """Drop ingestion registry tables and partial index."""
    op.execute("DROP INDEX IF EXISTS uq_document_versions_current;")
    op.drop_index("idx_document_versions_sha256", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_index("idx_regulations_detail_url", table_name="regulations")
    op.drop_index("idx_regulations_source_type", table_name="regulations")
    op.drop_table("regulations")
