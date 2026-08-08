"""Data contract schemas for regulatory ingestion pipeline."""

from datetime import UTC, date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    """Classification type of attached document asset."""

    REGULATION = "regulation"
    FAQ = "faq"
    ABSTRACT = "abstract"
    OTHER = "other"


class RegulationReference(BaseModel):
    """Discovery reference contract returned by source adapters."""

    source: str = Field(description="Source issuing authority (e.g. 'BI', 'OJK')")
    regulation_type: str = Field(description="Regulatory type (e.g. 'PBI', 'POJK')")
    regulation_number: str = Field(description="Official regulation number string")
    title: str = Field(description="Regulation title")
    detail_url: str = Field(description="Official detail page URL string")
    published_date: date | None = Field(
        default=None, description="Publication date if available from listing"
    )


class DocumentReference(BaseModel):
    """Attachment reference contract extracted from regulation detail page."""

    document_type: DocumentType = Field(description="Attachment classification type")
    url: str = Field(description="Direct download URL for document file")
    filename: str = Field(description="Original filename or resolved label")
    content_type: str = Field(default="application/pdf", description="Expected HTTP Content-Type")


class RegulationMetadata(BaseModel):
    """Normalized full metadata contract for a regulation entity."""

    source: str = Field(description="Source issuing authority (e.g. 'BI', 'OJK')")
    regulation_type: str = Field(description="Regulatory classification type")
    regulation_number: str = Field(description="Official regulation identifier string")
    title: str = Field(description="Official regulation title")
    sector: str | None = Field(default=None, description="Financial sector classification")
    subsector: str | None = Field(default=None, description="Financial subsector classification")
    status: str | None = Field(default=None, description="Source-provided legal status string")
    published_date: date | None = Field(default=None, description="Official publication date")
    effective_date: date | None = Field(default=None, description="Official effective date")
    detail_url: str = Field(description="Official web detail page URL")
    summary: str | None = Field(default=None, description="Short summary excerpt")
    abstract: str | None = Field(default=None, description="Full abstract text if provided")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attachments: list[DocumentReference] = Field(
        default_factory=list, description="Resolved document attachment references"
    )


class DownloadResult(BaseModel):
    """Payload contract returned by DownloadManager upon HTTP download."""

    url: str = Field(description="Downloaded HTTP resource URL")
    content_bytes: bytes = Field(description="Raw file content byte payload")
    content_type: str = Field(description="HTTP response Content-Type header value")
    content_length: int = Field(description="Byte size length of content")
    sha256: str = Field(description="Deterministic SHA-256 hex digest checksum")
    http_status: int = Field(default=200, description="HTTP response status code")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IngestionSummary(BaseModel):
    """Structured telemetry summary object returned after ingestion run."""

    source: str = Field(description="Source authority identifier")
    discovered: int = Field(default=0, description="Count of regulations discovered")
    metadata_parsed: int = Field(default=0, description="Count of metadata pages parsed")
    documents_found: int = Field(default=0, description="Count of document attachments resolved")
    downloaded: int = Field(default=0, description="Count of raw files successfully downloaded")
    skipped: int = Field(
        default=0, description="Count of unchanged existing files skipped (idempotent)"
    )
    new_versions: int = Field(
        default=0, description="Count of new document versions detected and stored"
    )
    failed: int = Field(default=0, description="Count of failed document processing attempts")
    duration_seconds: float = Field(default=0.0, description="Total execution duration in seconds")
