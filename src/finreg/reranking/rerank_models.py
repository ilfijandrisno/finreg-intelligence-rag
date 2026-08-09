"""Data models, schemas, and result containers for Phase 5 Neural Cross-Encoder Reranking."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RerankedSearchResult(BaseModel):
    """Rescored legal chunk with Cross-Encoder score and legal provenance."""

    rerank_score: float = Field(description="Neural Cross-Encoder relevance score")
    rerank_rank: int = Field(description="1-based rank position after neural reranking")
    fused_score: float = Field(description="Reciprocal Rank Fusion (RRF) score from Phase 4C")
    dense_rank: int | None = Field(
        default=None, description="1-based rank position in dense vector branch"
    )
    lexical_rank: int | None = Field(
        default=None, description="1-based rank position in BM25 lexical branch"
    )
    dense_score: float | None = Field(
        default=None, description="Raw cosine similarity score from dense search"
    )
    lexical_score: float | None = Field(
        default=None, description="Raw BM25 score from lexical keyword search"
    )
    retrieval_method: str = Field(
        description="Source fusion branch contribution ('hybrid', 'dense_only', 'lexical_only')"
    )

    # Full Phase 3B legal provenance fields
    chunk_id: UUID = Field(description="Retrieval chunk unique identifier")
    source_node_id: UUID = Field(description="Document node source provenance identifier")
    document_id: UUID = Field(description="Parent regulation document identifier")
    document_version_id: UUID = Field(description="Document version identifier")
    source: str = Field(description="Regulatory authority source (e.g., 'BI', 'OJK')")
    regulation_type: str = Field(description="Regulation type (e.g., 'PBI', 'PADG')")
    regulation_number: str = Field(description="Official regulation number string")
    title: str = Field(description="Regulation title")
    structural_path: str = Field(description="Hierarchical legal path string")
    chunk_text: str = Field(description="Raw legal text body")
    contextual_text: str = Field(description="Contextual header + text payload paired with query")
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


class RerankExecutionReport(BaseModel):
    """Execution metrics report for neural reranking run."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str = Field(description="Neural Cross-Encoder model identifier string")
    candidates_in_count: int = Field(description="Count of input candidate chunks before reranking")
    reranked_out_count: int = Field(description="Count of top-N reranked results returned")
    execution_time_ms: float = Field(description="Measured reranking execution duration in ms")
