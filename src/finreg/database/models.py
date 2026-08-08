"""SQLAlchemy ORM models for ingestion database registry (Phase 2)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
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
