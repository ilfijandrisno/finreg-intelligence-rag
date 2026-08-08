"""Protocol interfaces for document ingestion and parsing."""

from typing import Any, BinaryIO, Protocol, runtime_checkable

from finreg.domain.models import DocumentVersion, Section


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
