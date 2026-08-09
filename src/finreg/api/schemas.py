"""Pydantic v2 API request, response, and error schemas for Phase 7 REST endpoints."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Safe, standardized error response model isolating raw exception details."""

    error_code: str = Field(description="Standard error code string (e.g. 'VALIDATION_ERROR')")
    message: str = Field(description="Safe human-readable error description")
    request_id: str = Field(description="Unique request tracing UUID string")


class HealthResponse(BaseModel):
    """Response schema for GET /health liveness probe."""

    status: str = Field(default="ok", description="Service liveness status")
    service: str = Field(default="finreg-intelligence", description="Service name")
    version: str = Field(description="Application version string")


class ReadinessResponse(BaseModel):
    """Response schema for GET /readiness probe."""

    status: str = Field(default="ready", description="Service readiness status")
    database: str = Field(default="connected", description="Database connectivity status")


class RAGQueryRequest(BaseModel):
    """Request schema for POST /api/v1/rag/generate grounded answer generation."""

    query: str = Field(min_length=1, description="User search query string")
    top_n: int = Field(default=5, gt=0, le=20, description="Final top-N reranked context limit")
    source_filter: str | None = Field(default=None, description="Optional regulatory source filter")
    regulation_type_filter: str | None = Field(
        default=None, description="Optional regulation type filter"
    )
    regulation_number_filter: str | None = Field(
        default=None, description="Optional regulation number filter"
    )
    document_id_filter: UUID | None = Field(default=None, description="Optional document filter")


class LegalCitationResponse(BaseModel):
    """Validated legal provenance citation schema."""

    context_id: str = Field(description="Assigned context identifier tag (e.g. 'C1')")
    chunk_id: UUID = Field(description="Unique retrieval chunk identifier")
    source: str = Field(description="Regulatory authority source")
    regulation_type: str = Field(description="Regulation type")
    regulation_number: str = Field(description="Official regulation number string")
    structural_path: str = Field(description="Hierarchical legal path string")
    page_start: int = Field(description="Start page in source PDF")
    page_end: int = Field(description="End page in source PDF")
    display_citation: str = Field(description="Formatted human-readable citation string")


class RAGExecutionReportResponse(BaseModel):
    """Execution diagnostic metrics schema."""

    model_config = ConfigDict(protected_namespaces=())

    provider_name: str = Field(description="LLM provider implementation name")
    model_name: str = Field(description="LLM model identifier string")
    context_blocks_count: int = Field(description="Count of context blocks passed to LLM")
    estimated_input_tokens: int = Field(description="Estimated total input tokens")
    output_tokens: int | None = Field(default=None, description="Output token count")
    execution_time_ms: float = Field(description="Measured execution duration in milliseconds")
    abstained: bool = Field(description="Flag indicating if generation abstained")


class RAGQueryResponse(BaseModel):
    """Response schema for POST /api/v1/rag/generate."""

    query: str = Field(description="User query string")
    answer: str = Field(description="Grounded LLM-generated legal answer")
    citations: list[LegalCitationResponse] = Field(
        default_factory=list, description="Validated legal citations list"
    )
    abstained: bool = Field(description="Flag indicating whether generation abstained")
    abstention_reason: str | None = Field(default=None, description="Reason for abstention")
    has_legal_conflict: bool = Field(description="Flag for context provisions conflict")
    execution_report: RAGExecutionReportResponse = Field(description="Execution diagnostic report")


class HybridSearchRequest(BaseModel):
    """Request schema for POST /api/v1/retrieval/search (Phase 4C Hybrid RRF only)."""

    query: str = Field(min_length=1, description="User search query string")
    top_k: int = Field(default=5, gt=0, le=50, description="Top-K hybrid fused results limit")
    rrf_k: int = Field(default=60, gt=0, description="RRF constant k parameter")
    dense_top_k: int = Field(default=20, gt=0, description="Dense branch candidate pool size")
    lexical_top_k: int = Field(default=20, gt=0, description="Lexical branch candidate pool size")
    source_filter: str | None = Field(default=None, description="Optional regulatory source filter")
    regulation_type_filter: str | None = Field(
        default=None, description="Optional regulation type filter"
    )
    regulation_number_filter: str | None = Field(
        default=None, description="Optional regulation number filter"
    )
    document_id_filter: UUID | None = Field(default=None, description="Optional document filter")


class HybridSearchResultItem(BaseModel):
    """Item schema for Phase 4C Hybrid RRF search result."""

    fused_score: float = Field(description="Reciprocal Rank Fusion (RRF) score")
    dense_rank: int | None = Field(default=None, description="Rank position in dense branch")
    lexical_rank: int | None = Field(default=None, description="Rank position in lexical branch")
    dense_score: float | None = Field(default=None, description="Raw cosine similarity score")
    lexical_score: float | None = Field(default=None, description="Raw BM25 score")
    retrieval_method: str = Field(description="Source fusion branch contribution")
    chunk_id: UUID = Field(description="Retrieval chunk unique identifier")
    source_node_id: UUID = Field(description="Document node source provenance identifier")
    document_id: UUID = Field(description="Parent regulation document identifier")
    document_version_id: UUID = Field(description="Document version identifier")
    source: str = Field(description="Regulatory authority source")
    regulation_type: str = Field(description="Regulation type")
    regulation_number: str = Field(description="Official regulation number string")
    title: str = Field(description="Regulation title")
    structural_path: str = Field(description="Hierarchical legal path string")
    chunk_text: str = Field(description="Raw legal text body")
    contextual_text: str = Field(description="Contextual header + text payload")
    page_start: int = Field(description="Start page in source PDF")
    page_end: int = Field(description="End page in source PDF")
    sequence: int = Field(description="Chunk sequence ordinal")


class HybridSearchResponse(BaseModel):
    """Response schema for POST /api/v1/retrieval/search."""

    query: str = Field(description="User query string")
    results: list[HybridSearchResultItem] = Field(description="List of hybrid fused search results")
    total_results: int = Field(description="Total count of returned results")
    execution_time_ms: float = Field(description="Execution duration in milliseconds")


class RerankRequest(BaseModel):
    """Request schema for POST /api/v1/retrieval/rerank (Phase 4C Hybrid -> Phase 5 Rerank)."""

    query: str = Field(min_length=1, description="User search query string")
    top_n: int = Field(default=5, gt=0, le=20, description="Final top-N reranked results limit")
    hybrid_top_k: int = Field(default=20, gt=0, description="Candidate pool size before reranking")
    source_filter: str | None = Field(default=None, description="Optional regulatory source filter")
    regulation_type_filter: str | None = Field(
        default=None, description="Optional regulation type filter"
    )
    regulation_number_filter: str | None = Field(
        default=None, description="Optional regulation number filter"
    )
    document_id_filter: UUID | None = Field(default=None, description="Optional document filter")


class RerankResultItem(BaseModel):
    """Item schema for Phase 5 Neural Cross-Encoder reranked result."""

    rerank_score: float = Field(description="Neural Cross-Encoder relevance score")
    rerank_rank: int = Field(description="1-based rank position after reranking")
    fused_score: float = Field(description="RRF score from Phase 4C")
    dense_rank: int | None = Field(default=None, description="Rank position in dense branch")
    lexical_rank: int | None = Field(default=None, description="Rank position in lexical branch")
    dense_score: float | None = Field(default=None, description="Raw cosine similarity score")
    lexical_score: float | None = Field(default=None, description="Raw BM25 score")
    retrieval_method: str = Field(description="Source fusion branch contribution")
    chunk_id: UUID = Field(description="Retrieval chunk unique identifier")
    source_node_id: UUID = Field(description="Document node source provenance identifier")
    document_id: UUID = Field(description="Parent regulation document identifier")
    document_version_id: UUID = Field(description="Document version identifier")
    source: str = Field(description="Regulatory authority source")
    regulation_type: str = Field(description="Regulation type")
    regulation_number: str = Field(description="Official regulation number string")
    title: str = Field(description="Regulation title")
    structural_path: str = Field(description="Hierarchical legal path string")
    chunk_text: str = Field(description="Raw legal text body")
    contextual_text: str = Field(description="Contextual header + text payload")
    page_start: int = Field(description="Start page in source PDF")
    page_end: int = Field(description="End page in source PDF")
    sequence: int = Field(description="Chunk sequence ordinal")


class RerankResponse(BaseModel):
    """Response schema for POST /api/v1/retrieval/rerank."""

    query: str = Field(description="User query string")
    results: list[RerankResultItem] = Field(description="List of neural reranked search results")
    total_results: int = Field(description="Total count of returned results")
    model_name: str = Field(description="Neural Cross-Encoder model identifier string")
    execution_time_ms: float = Field(description="Execution duration in milliseconds")
