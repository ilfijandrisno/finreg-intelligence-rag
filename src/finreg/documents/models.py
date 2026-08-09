"""Data models, enums, dataclasses, and custom exceptions for Phase 3A document
parsing.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NoCurrentDocumentVersionError(Exception):
    """Raised when attempting to parse a document that has no active version (is_current=True)."""

    pass


class ParsingValidationError(Exception):
    """Raised when structure validation coverage ratio is below minimum acceptable threshold."""

    pass


class NodeType(StrEnum):
    """Taxonomy of recognized structural nodes in Indonesian financial regulations."""

    PREAMBLE = "preamble"
    CONSIDERATION = "consideration"
    LEGAL_BASIS = "legal_basis"
    DECISION = "decision"
    CHAPTER = "chapter"
    PART = "part"
    SECTION = "section"
    ARTICLE = "article"
    PARAGRAPH = "paragraph"
    LETTER = "letter"
    NUMBERED_ITEM = "numbered_item"
    CLOSING = "closing"


@dataclass
class ExtractedBlock:
    """Raw text block extracted from a single PDF page via PyMuPDF."""

    page_num: int
    block_num: int
    bbox: tuple[float, float, float, float]
    lines: list[str]
    text: str


@dataclass
class NormalizedLine:
    """Line payload after header/footer removal, unwrapping, and hyphenation repair."""

    text: str
    page_num: int
    line_num: int
    is_boundary_marker: bool = False


@dataclass
class StructuredNode:
    """Intermediate tree node representation before database persistence."""

    node_type: NodeType
    node_number: str | None = None
    title: str | None = None
    text: str = ""
    page_start: int = 1
    page_end: int = 1
    sequence: int = 0
    path: str = ""
    children: list["StructuredNode"] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


class ValidationReport(BaseModel):
    """Structured report assessing document parsing quality and character coverage ratio."""

    document_id: UUID = Field(description="Parent regulation document identifier")
    version_id: UUID = Field(description="Target document version identifier")
    total_pages: int = Field(description="Total PDF page count")
    extracted_characters: int = Field(description="Total character count of normalized text")
    structured_characters: int = Field(
        description="Character count captured in non-overlapping leaf content nodes"
    )
    unparsed_characters: int = Field(description="Character count remaining unparsed")
    coverage_ratio: float = Field(
        description="Ratio of structured characters to extracted characters"
    )
    is_valid: bool = Field(description="True if coverage_ratio >= PARSING_MIN_COVERAGE_RATIO")
    warnings: list[str] = Field(default_factory=list, description="Parsing anomaly warnings")
