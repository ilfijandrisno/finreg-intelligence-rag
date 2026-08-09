"""Domain models and validation schemas for semantic legal chunking (Phase 3B)."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


@dataclass
class SemanticChunk:
    """Intermediate domain representation of a retrieval-ready legal text chunk."""

    document_id: UUID
    document_version_id: UUID
    source_node_id: UUID
    chunk_hash: str
    source: str
    regulation_type: str
    regulation_number: str
    title: str
    structural_path: str
    chunk_text: str
    contextual_text: str
    character_count: int
    word_count: int
    page_start: int
    page_end: int
    sequence: int
    chapter_title: str | None = None
    part_title: str | None = None
    section_title: str | None = None
    article_number: str | None = None
    paragraph_number: str | None = None
    letter_code: str | None = None
    numbered_item: str | None = None
    part_index: int = 1
    total_parts: int = 1
    id: UUID = field(default_factory=uuid4)


class ChunkValidationReport(BaseModel):
    """Structured report assessing legal chunking quality, leaf text coverage, and provenance."""

    document_id: UUID = Field(description="Parent regulation document identifier")
    version_id: UUID = Field(description="Target document version identifier")
    total_chunks: int = Field(description="Total semantic chunks generated")
    leaf_source_characters: int = Field(
        description="Total character count across all Phase 3A leaf content nodes"
    )
    chunked_characters: int = Field(
        description="Sum of character counts across all generated chunk_text fields"
    )
    source_text_coverage: float = Field(
        description="Ratio of chunked characters to leaf source characters (target: 1.0)"
    )
    min_chunk_size: int = Field(description="Minimum chunk character count")
    max_chunk_size: int = Field(description="Maximum chunk character count")
    avg_chunk_size: float = Field(description="Average chunk character count")
    is_valid: bool = Field(
        description="True if coverage == 1.0, no empty chunks, and valid hashes/IDs"
    )
    warnings: list[str] = Field(default_factory=list, description="Chunking anomaly warnings")


class ChunkingValidationError(ValueError):
    """Raised when legal chunking fails validation criteria."""

    def __init__(self, message: str, report: ChunkValidationReport):
        super().__init__(message)
        self.report = report
