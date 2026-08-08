"""Core domain entities and value objects.

These models are independent from infrastructure, database ORMs, or vendor frameworks.
"""

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class IssuerType(StrEnum):
    """Regulatory issuing body in Indonesian Financial System."""

    BANK_INDONESIA = "BI"
    OTORITAS_JASA_KEUANGAN = "OJK"
    LEMBAGA_PENJAMIN_SIMPANAN = "LPS"
    KEMENTERIAN_KEUANGAN = "KEMENKEU"
    OTHER = "OTHER"


class RelationshipType(StrEnum):
    """Relationship between regulatory documents."""

    AMENDS = "amends"
    REVOKES = "revokes"
    IMPLEMENTS = "implements"
    REFERENCES = "references"
    SUPERSEDES = "supersedes"


class Regulation(BaseModel):
    """Domain model representing an Indonesian financial regulation entity."""

    id: UUID = Field(default_factory=uuid4)
    issuer: IssuerType = Field(description="Issuing regulatory authority")
    regulation_number: str = Field(
        description="Official regulation number string (e.g. 23/13/PBI/2021)"
    )
    title: str = Field(description="Official regulation title")
    category: str = Field(description="Regulatory category (e.g. Peraturan BI, POJK)")
    effective_date: date | None = Field(
        default=None, description="Date when regulation took effect"
    )
    is_active: bool = Field(default=True, description="Active status of regulation")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata attributes"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Document(BaseModel):
    """Domain model representing a raw or processed regulatory document file."""

    id: UUID = Field(default_factory=uuid4)
    regulation_id: UUID = Field(description="Reference to parent Regulation ID")
    file_name: str = Field(description="Original file name")
    file_type: str = Field(default="pdf", description="Document file extension")
    source_url: HttpUrl | None = Field(default=None, description="Official source URL")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DocumentVersion(BaseModel):
    """Domain model representing a specific snapshot version of a document."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID = Field(description="Reference to parent Document ID")
    version_number: int = Field(default=1, description="Sequential version index")
    checksum_sha256: str = Field(description="SHA-256 hash checksum of document content")
    file_size_bytes: int = Field(description="File size in bytes")
    raw_metadata: dict[str, Any] = Field(default_factory=dict, description="Extraction metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Section(BaseModel):
    """Domain model representing a section or article within a regulation document."""

    id: UUID = Field(default_factory=uuid4)
    document_version_id: UUID = Field(description="Reference to DocumentVersion ID")
    parent_section_id: UUID | None = Field(
        default=None, description="ID of parent section if nested"
    )
    level: int = Field(default=1, description="Hierarchical level depth (e.g. 1=Bab, 2=Pasal)")
    title: str = Field(description="Section title or header text")
    content: str = Field(description="Raw section body text")
    order_index: int = Field(description="Sequential ordering index within document")


class Chunk(BaseModel):
    """Domain model representing a discrete chunk of text prepared for indexing."""

    id: UUID = Field(default_factory=uuid4)
    section_id: UUID = Field(description="Reference to parent Section ID")
    content: str = Field(description="Text payload of the chunk")
    token_count: int = Field(description="Estimated token count of chunk content")
    position_index: int = Field(description="Sequential index position within section")
    chunk_hash: str = Field(description="Content hash for deduplication check")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Chunk context & lineage metadata"
    )


class RegulationRelationship(BaseModel):
    """Domain model representing legal lineage/relationship between two regulations."""

    id: UUID = Field(default_factory=uuid4)
    source_regulation_id: UUID = Field(description="Originating regulation ID")
    target_regulation_id: UUID = Field(description="Target regulation ID")
    relationship_type: RelationshipType = Field(description="Legal relation classification")
    notes: str | None = Field(default=None, description="Explanatory notes")


class Citation(BaseModel):
    """Value object representing a verifiable legal citation backing an answer."""

    regulation_number: str = Field(description="Regulation identifier string")
    section_title: str = Field(description="Section or article title")
    text_snippet: str = Field(description="Relevant text excerpt cited")
    source_url: str | None = Field(default=None, description="Direct URL link to regulation source")
    confidence_score: float | None = Field(
        default=None, description="Retrieval score if applicable"
    )
