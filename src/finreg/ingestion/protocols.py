"""Protocol interfaces for document ingestion and source adapters."""

from typing import Any, BinaryIO, Protocol, runtime_checkable

from finreg.domain.models import DocumentVersion, Section
from finreg.ingestion.models import (
    DocumentReference,
    RegulationMetadata,
    RegulationReference,
)


@runtime_checkable
class DocumentLoader(Protocol):
    """Protocol for fetching raw regulatory documents from official sources."""

    def load_from_url(self, url: str) -> bytes:
        """Fetch raw document bytes from public HTTP URL."""
        ...

    def load_from_stream(self, stream: BinaryIO) -> bytes:
        """Read document bytes from a binary stream or local file."""
        ...


@runtime_checkable
class DocumentParser(Protocol):
    """Protocol for extracting structured sections and metadata from raw document bytes."""

    def parse(
        self, content: bytes, file_type: str, metadata: dict[str, Any] | None = None
    ) -> tuple[DocumentVersion, list[Section]]:
        """Parse raw content into a DocumentVersion and associated ordered Sections."""
        ...


@runtime_checkable
class RegulatorySourceAdapter(Protocol):
    """Protocol contract for official regulatory source adapters (BI, OJK)."""

    @property
    def source_name(self) -> str:
        """Return the adapter source identifier (e.g. 'BI', 'OJK')."""
        ...

    @property
    def target_regulation_type(self) -> str:
        """Return the target regulatory type (e.g. 'PBI', 'POJK')."""
        ...

    def discover_regulations(self, limit: int | None = None) -> list[RegulationReference]:
        """Discover regulation references from official portal listing pages."""
        ...

    def fetch_metadata(self, reference: RegulationReference) -> RegulationMetadata:
        """Fetch and parse detailed metadata from the official regulation detail page."""
        ...

    def resolve_documents(self, metadata: RegulationMetadata) -> list[DocumentReference]:
        """Resolve attachment document references for a given regulation."""
        ...
