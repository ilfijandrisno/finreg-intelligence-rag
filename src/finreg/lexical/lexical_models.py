"""Data models, schemas, and result containers for Phase 4B BM25 lexical retrieval."""

from uuid import UUID

from pydantic import BaseModel, Field


class LexicalSearchResult(BaseModel):
    """Retrieved legal chunk with BM25 lexical score and full legal provenance."""

    score: float = Field(description="BM25 keyword similarity score")
    matched_terms_count: int = Field(description="Count of distinct matched query terms")
    chunk_id: UUID = Field(description="Retrieval chunk unique identifier")
    source_node_id: UUID = Field(description="Document node source provenance identifier")
    document_id: UUID = Field(description="Parent regulation document identifier")
    document_version_id: UUID = Field(description="Document version identifier")
    source: str = Field(description="Regulatory authority source (e.g., 'BI', 'OJK')")
    regulation_type: str = Field(description="Regulation type (e.g., 'PBI', 'PADG')")
    regulation_number: str = Field(description="Official regulation number string")
    title: str = Field(description="Regulation title")
    structural_path: str = Field(description="Hierarchical legal path string")
    chunk_text: str = Field(description="Raw legal text body used for BM25 indexing")
    contextual_text: str = Field(description="Contextual header + text payload")
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


class LexicalIndexReport(BaseModel):
    """Summary report for constructed BM25 inverted index."""

    total_chunks: int = Field(description="Total count of retrieval chunks indexed")
    vocabulary_size: int = Field(description="Total count of unique terms in index vocabulary")
    average_doc_length: float = Field(description="Average document length in word tokens")
