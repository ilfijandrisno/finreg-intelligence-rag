"""Create document_nodes table with composite foreign key and self-referencing parent hierarchy.

Revision ID: 003_document_nodes
Revises: 002_ingestion_registry
Create Date: 2026-08-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_document_nodes"
down_revision: str | None = "002_ingestion_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create document_nodes table and composite foreign key constraint."""
    op.create_unique_constraint(
        "uq_document_versions_doc_id",
        "document_versions",
        ["document_id", "id"],
    )

    op.create_table(
        "document_nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("node_type", sa.String(length=30), nullable=False),
        sa.Column("node_number", sa.String(length=50), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id", "document_version_id"],
            ["document_versions.document_id", "document_versions.id"],
            ondelete="CASCADE",
            name="fk_document_nodes_doc_version",
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["document_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_document_nodes_doc_ver",
        "document_nodes",
        ["document_id", "document_version_id"],
        unique=False,
    )
    op.create_index(
        "idx_document_nodes_doc_seq",
        "document_nodes",
        ["document_id", "sequence"],
        unique=False,
    )
    op.create_index("idx_document_nodes_parent", "document_nodes", ["parent_id"], unique=False)


def downgrade() -> None:
    """Drop document_nodes table and composite constraint."""
    op.drop_index("idx_document_nodes_parent", table_name="document_nodes")
    op.drop_index("idx_document_nodes_doc_seq", table_name="document_nodes")
    op.drop_index("idx_document_nodes_doc_ver", table_name="document_nodes")
    op.drop_table("document_nodes")
    op.drop_constraint("uq_document_versions_doc_id", "document_versions", type_="unique")
