"""Data models, schemas, and result containers for Phase 4A vector retrieval."""

from uuid import UUID

from pydantic import BaseModel, Field


class VectorSearchResult(BaseModel):
    """Retrieved legal chunk with vector similarity score and full provenance."""

    score: float = Field(description="Cosine similarity score (1.0 - cosine_distance)")
    distance: float = Field(description="Cosine distance from pgvector (<=> operator)")
    chunk_id: UUID = Field(description="Retrieval chunk unique identifier")
    source_node_id: UUID = Field(description="Document node source provenance identifier")
    document_id: UUID = Field(description="Parent regulation document identifier")
    document_version_id: UUID = Field(description="Document version identifier")
    embedding_model: str = Field(description="Embedding model identifier used for vector search")
    source: str = Field(description="Regulatory authority source (e.g., 'BI', 'OJK')")
    regulation_type: str = Field(description="Regulation type (e.g., 'PBI', 'PADG')")
    regulation_number: str = Field(description="Official regulation number string")
    title: str = Field(description="Regulation title")
    structural_path: str = Field(description="Hierarchical legal path string")
    chunk_text: str = Field(description="Raw legal text body")
    contextual_text: str = Field(description="Contextual header + text used for embedding")
    part_index: int = Field(default=1, description="Part index for split chunks")
    total_parts: int = Field(default=1, description="Total split parts count")
    page_start: int = Field(description="Start page in source PDF")
    page_end: int = Field(description="End page in source PDF")
    sequence: int = Field(description="Chunk sequence ordinal")
    chapter_title: str | None = Field(default=None, description="Chapter title if applicable")
    part_title: str | None = Field(default=None, description="Part title if applicable")
    section_title: str | None = Field(default=None, description="Section title if applicable")
    article_number: str | None = Field(default=None, description="Article number if applicable")
    paragraph_number: str | None = Field(default=None, description="Paragraph number if applicable")
    letter_code: str | None = Field(default=None, description="Letter code if applicable")
    numbered_item: str | None = Field(default=None, description="Numbered item if applicable")


class EmbeddingExecutionReport(BaseModel):
    """Structured execution summary report for document chunk embedding generation."""

    document_id: UUID = Field(description="Parent regulation document identifier")
    version_id: UUID = Field(description="Document version identifier")
    embedding_model: str = Field(description="Embedding model identifier used")
    dimension: int = Field(description="Target embedding vector dimension")
    chunks_embedded: int = Field(description="Count of chunks processed for embedding")
    total_vectors_persisted: int = Field(description="Count of vectors persisted in DB")
    is_valid: bool = Field(description="True if all chunks embedded validly")
    warnings: list[str] = Field(default_factory=list, description="Execution anomaly warnings")
