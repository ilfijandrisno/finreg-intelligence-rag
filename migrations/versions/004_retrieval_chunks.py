"""Create retrieval_chunks table with composite foreign key and structural metadata.

Revision ID: 004_retrieval_chunks
Revises: 003_document_nodes
Create Date: 2026-08-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_retrieval_chunks"
down_revision: str | None = "003_document_nodes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create retrieval_chunks table, unique constraints, and indexes."""
    op.create_table(
        "retrieval_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("source_node_id", sa.UUID(), nullable=False),
        sa.Column("chunk_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("regulation_type", sa.String(length=20), nullable=False),
        sa.Column("regulation_number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("chapter_title", sa.Text(), nullable=True),
        sa.Column("part_title", sa.Text(), nullable=True),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("article_number", sa.String(length=50), nullable=True),
        sa.Column("paragraph_number", sa.String(length=50), nullable=True),
        sa.Column("letter_code", sa.String(length=50), nullable=True),
        sa.Column("numbered_item", sa.String(length=50), nullable=True),
        sa.Column("part_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_parts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("structural_path", sa.Text(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("contextual_text", sa.Text(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id", "document_version_id"],
            ["document_versions.document_id", "document_versions.id"],
            ondelete="CASCADE",
            name="fk_retrieval_chunks_doc_version",
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"],
            ["document_nodes.id"],
            ondelete="CASCADE",
            name="fk_retrieval_chunks_source_node",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id", "sequence", name="uq_retrieval_chunks_doc_ver_seq"
        ),
        sa.UniqueConstraint(
            "document_version_id", "chunk_hash", name="uq_retrieval_chunks_doc_ver_hash"
        ),
    )

    op.create_index(
        "idx_retrieval_chunks_doc_ver",
        "retrieval_chunks",
        ["document_id", "document_version_id"],
        unique=False,
    )
    op.create_index(
        "idx_retrieval_chunks_reg_num",
        "retrieval_chunks",
        ["regulation_type", "regulation_number"],
        unique=False,
    )


def downgrade() -> None:
    """Drop retrieval_chunks table."""
    op.drop_index("idx_retrieval_chunks_reg_num", table_name="retrieval_chunks")
    op.drop_index("idx_retrieval_chunks_doc_ver", table_name="retrieval_chunks")
    op.drop_table("retrieval_chunks")
