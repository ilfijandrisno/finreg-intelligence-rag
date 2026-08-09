"""SQLAlchemy ORM models for ingestion database registry (Phase 2)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy ORM models."""

    pass


class RegulationORM(Base):
    """PostgreSQL ORM model for official regulation registry."""

    __tablename__ = "regulations"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "regulation_type",
            "regulation_number",
            name="uq_regulations_source_type_num",
        ),
        Index("idx_regulations_source_type", "source", "regulation_type"),
        Index("idx_regulations_detail_url", "detail_url"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    regulation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    regulation_number: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    sector: Mapped[str | None] = mapped_column(String(150), nullable=True)
    subsector: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    detail_url: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    documents: Mapped[list["DocumentORM"]] = relationship(
        "DocumentORM", back_populates="regulation", cascade="all, delete-orphan"
    )


class DocumentORM(Base):
    """PostgreSQL ORM model for document attachment references."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "regulation_id",
            "document_type",
            "document_url",
            name="uq_documents_reg_type_url",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    regulation_id: Mapped[UUID] = mapped_column(
        ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_url: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="application/pdf"
    )
    content_length: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    regulation: Mapped["RegulationORM"] = relationship("RegulationORM", back_populates="documents")
    versions: Mapped[list["DocumentVersionORM"]] = relationship(
        "DocumentVersionORM", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersionORM(Base):
    """PostgreSQL ORM model for immutable version snapshots of documents."""

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "sha256", name="uq_document_versions_doc_sha256"),
        UniqueConstraint("document_id", "id", name="uq_document_versions_doc_id"),
        Index("idx_document_versions_sha256", "sha256"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    document: Mapped["DocumentORM"] = relationship("DocumentORM", back_populates="versions")
    nodes: Mapped[list["DocumentNodeORM"]] = relationship(
        "DocumentNodeORM", back_populates="document_version", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["RetrievalChunkORM"]] = relationship(
        "RetrievalChunkORM", back_populates="document_version", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["ChunkEmbeddingORM"]] = relationship(
        "ChunkEmbeddingORM",
        primaryjoin=(
            "and_("
            "DocumentVersionORM.document_id == foreign(ChunkEmbeddingORM.document_id), "
            "DocumentVersionORM.id == foreign(ChunkEmbeddingORM.document_version_id)"
            ")"
        ),
        back_populates="document_version",
        cascade="all, delete-orphan",
    )


class DocumentNodeORM(Base):
    """PostgreSQL ORM model for hierarchical document node trees."""

    __tablename__ = "document_nodes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "document_version_id"],
            ["document_versions.document_id", "document_versions.id"],
            ondelete="CASCADE",
            name="fk_document_nodes_doc_version",
        ),
        Index("idx_document_nodes_doc_ver", "document_id", "document_version_id"),
        Index("idx_document_nodes_doc_seq", "document_id", "sequence"),
        Index("idx_document_nodes_parent", "parent_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(nullable=False)
    document_version_id: Mapped[UUID] = mapped_column(nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_nodes.id", ondelete="CASCADE"), nullable=True
    )
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    node_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    page_start: Mapped[int] = mapped_column(nullable=False)
    page_end: Mapped[int] = mapped_column(nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    document_version: Mapped["DocumentVersionORM"] = relationship(
        "DocumentVersionORM", back_populates="nodes"
    )
    parent: Mapped["DocumentNodeORM | None"] = relationship(
        "DocumentNodeORM", remote_side=lambda: [DocumentNodeORM.id], back_populates="children"
    )
    children: Mapped[list["DocumentNodeORM"]] = relationship(
        "DocumentNodeORM", back_populates="parent", cascade="all, delete-orphan"
    )


class RetrievalChunkORM(Base):
    """PostgreSQL ORM model for retrieval-ready legal text chunks."""

    __tablename__ = "retrieval_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "document_version_id"],
            ["document_versions.document_id", "document_versions.id"],
            ondelete="CASCADE",
            name="fk_retrieval_chunks_doc_version",
        ),
        ForeignKeyConstraint(
            ["source_node_id"],
            ["document_nodes.id"],
            ondelete="CASCADE",
            name="fk_retrieval_chunks_source_node",
        ),
        UniqueConstraint("document_version_id", "sequence", name="uq_retrieval_chunks_doc_ver_seq"),
        UniqueConstraint(
            "document_version_id", "chunk_hash", name="uq_retrieval_chunks_doc_ver_hash"
        ),
        Index("idx_retrieval_chunks_doc_ver", "document_id", "document_version_id"),
        Index("idx_retrieval_chunks_reg_num", "regulation_type", "regulation_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(nullable=False)
    document_version_id: Mapped[UUID] = mapped_column(nullable=False)
    source_node_id: Mapped[UUID] = mapped_column(nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    regulation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    regulation_number: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    chapter_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    article_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    paragraph_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    letter_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    numbered_item: Mapped[str | None] = mapped_column(String(50), nullable=True)
    part_index: Mapped[int] = mapped_column(nullable=False, default=1)
    total_parts: Mapped[int] = mapped_column(nullable=False, default=1)
    structural_path: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    contextual_text: Mapped[str] = mapped_column(Text, nullable=False)
    character_count: Mapped[int] = mapped_column(nullable=False)
    word_count: Mapped[int] = mapped_column(nullable=False)
    page_start: Mapped[int] = mapped_column(nullable=False)
    page_end: Mapped[int] = mapped_column(nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    document_version: Mapped["DocumentVersionORM"] = relationship(
        "DocumentVersionORM", back_populates="chunks"
    )
    source_node: Mapped["DocumentNodeORM"] = relationship("DocumentNodeORM")
    embeddings: Mapped[list["ChunkEmbeddingORM"]] = relationship(
        "ChunkEmbeddingORM",
        primaryjoin=(
            "and_("
            "RetrievalChunkORM.document_id == foreign(ChunkEmbeddingORM.document_id), "
            "RetrievalChunkORM.document_version_id == "
            "foreign(ChunkEmbeddingORM.document_version_id), "
            "RetrievalChunkORM.id == foreign(ChunkEmbeddingORM.chunk_id)"
            ")"
        ),
        back_populates="chunk",
        cascade="all, delete-orphan",
        overlaps="document_version,embeddings",
    )


class ChunkEmbeddingORM(Base):
    """PostgreSQL ORM model for dense vector embeddings with pgvector Vector(1536)."""

    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "document_version_id", "chunk_id"],
            [
                "retrieval_chunks.document_id",
                "retrieval_chunks.document_version_id",
                "retrieval_chunks.id",
            ],
            ondelete="CASCADE",
            name="fk_chunk_embeddings_retrieval_chunk",
        ),
        UniqueConstraint("chunk_id", "embedding_model", name="uq_chunk_embeddings_chunk_model"),
        Index(
            "idx_chunk_embeddings_doc_ver_model",
            "document_id",
            "document_version_id",
            "embedding_model",
        ),
        Index(
            "idx_chunk_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(nullable=False)
    document_version_id: Mapped[UUID] = mapped_column(nullable=False)
    chunk_id: Mapped[UUID] = mapped_column(nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    document_version: Mapped["DocumentVersionORM"] = relationship(
        "DocumentVersionORM",
        primaryjoin=(
            "and_(DocumentVersionORM.document_id == foreign(ChunkEmbeddingORM.document_id), "
            "DocumentVersionORM.id == foreign(ChunkEmbeddingORM.document_version_id))"
        ),
        back_populates="embeddings",
    )
    chunk: Mapped["RetrievalChunkORM"] = relationship(
        "RetrievalChunkORM",
        primaryjoin=(
            "and_("
            "RetrievalChunkORM.document_id == foreign(ChunkEmbeddingORM.document_id), "
            "RetrievalChunkORM.document_version_id == "
            "foreign(ChunkEmbeddingORM.document_version_id), "
            "RetrievalChunkORM.id == foreign(ChunkEmbeddingORM.chunk_id)"
            ")"
        ),
        back_populates="embeddings",
        overlaps="document_version,embeddings",
    )
