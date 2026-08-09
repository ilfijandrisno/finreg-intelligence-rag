"""Data models and schemas for Phase 6 Grounded LLM Generation and RAG Answer Assembly."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from finreg.reranking.rerank_models import RerankedSearchResult


class LegalCitation(BaseModel):
    """Structured legal provenance citation for downstream UI and auditability."""

    context_id: str = Field(description="Assigned context identifier tag (e.g. 'C1')")
    chunk_id: UUID = Field(description="Unique retrieval chunk identifier")
    source: str = Field(description="Regulatory authority source (e.g. 'BI', 'OJK')")
    regulation_type: str = Field(description="Regulation type (e.g. 'PBI', 'PADG')")
    regulation_number: str = Field(description="Official regulation number string")
    structural_path: str = Field(description="Hierarchical legal path string")
    page_start: int = Field(description="Start page in source PDF")
    page_end: int = Field(description="End page in source PDF")

    def format_display_string(self) -> str:
        """Return formatted human-readable citation string."""
        return (
            f"[{self.source}, {self.regulation_type} No. {self.regulation_number}, "
            f"{self.structural_path}, p. {self.page_start}]"
        )


class ContextBlock(BaseModel):
    """Context block wrapper with assigned context ID and token estimate."""

    context_id: str = Field(description="Assigned context identifier tag (e.g. 'C1')")
    reranked_result: RerankedSearchResult = Field(
        description="Phase 5 reranked chunk carrying full legal provenance"
    )
    estimated_tokens: int = Field(description="Estimated token count for context payload")


class RAGExecutionReport(BaseModel):
    """Execution metrics report for Phase 6 RAG answer generation run."""

    model_config = ConfigDict(protected_namespaces=())

    provider_name: str = Field(description="LLM provider implementation name")
    model_name: str = Field(description="LLM model identifier string")
    context_blocks_count: int = Field(description="Count of context blocks passed to LLM")
    estimated_input_tokens: int = Field(description="Estimated total input tokens in prompt")
    output_tokens: int | None = Field(
        default=None, description="Actual or estimated output tokens in generated answer"
    )
    execution_time_ms: float = Field(description="Measured execution duration in milliseconds")
    abstained: bool = Field(description="Flag indicating if generation abstained")


class GenerationResult(BaseModel):
    """Final RAG generation output containing grounded answer and citations."""

    query: str = Field(description="User query string")
    answer: str = Field(description="Grounded LLM-generated legal answer")
    citations: list[LegalCitation] = Field(
        default_factory=list, description="List of validated legal provenance citations"
    )
    abstained: bool = Field(
        default=False, description="Flag indicating whether generation abstained"
    )
    abstention_reason: str | None = Field(
        default=None, description="Reason for abstention if applicable"
    )
    has_legal_conflict: bool = Field(
        default=False, description="Flag indicating if context contains conflicting provisions"
    )
    execution_report: RAGExecutionReport = Field(description="Execution diagnostics report")
