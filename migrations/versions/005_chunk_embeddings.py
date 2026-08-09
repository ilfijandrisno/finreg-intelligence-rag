"""Create chunk_embeddings table with composite FK to retrieval_chunks and HNSW vector index.

Revision ID: 005_chunk_embeddings
Revises: 004_retrieval_chunks
Create Date: 2026-08-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "005_chunk_embeddings"
down_revision: str | None = "004_retrieval_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create chunk_embeddings table, composite FK, HNSW index, and unique constraint."""
    op.create_unique_constraint(
        "uq_retrieval_chunks_doc_ver_id",
        "retrieval_chunks",
        ["document_id", "document_version_id", "id"],
    )

    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id", "document_version_id", "chunk_id"],
            [
                "retrieval_chunks.document_id",
                "retrieval_chunks.document_version_id",
                "retrieval_chunks.id",
            ],
            ondelete="CASCADE",
            name="fk_chunk_embeddings_retrieval_chunk",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "embedding_model", name="uq_chunk_embeddings_chunk_model"),
    )

    op.create_index(
        "idx_chunk_embeddings_doc_ver_model",
        "chunk_embeddings",
        ["document_id", "document_version_id", "embedding_model"],
        unique=False,
    )

    op.create_index(
        "idx_chunk_embeddings_hnsw",
        "chunk_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    """Drop chunk_embeddings table and unique constraint."""
    op.drop_index("idx_chunk_embeddings_hnsw", table_name="chunk_embeddings")
    op.drop_index("idx_chunk_embeddings_doc_ver_model", table_name="chunk_embeddings")
    op.drop_table("chunk_embeddings")
    op.drop_constraint("uq_retrieval_chunks_doc_ver_id", "retrieval_chunks", type_="unique")
