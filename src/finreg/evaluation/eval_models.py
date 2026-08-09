"""Pydantic v2 data models and schemas for Phase 8 RAG Evaluation Framework."""

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Regex stripping chunker-inserted split part suffixes
PART_SUFFIX_REGEX = re.compile(r"\s*\[Part\s+\d+/\d+\]$", re.IGNORECASE)


def normalize_structural_path(path: str) -> str:
    """Normalize structural path by stripping chunker-generated split part suffixes.

    Example:
        'BAB I/Pasal 1/Ayat (1) [Part 1/2]' -> 'BAB I/Pasal 1/Ayat (1)'
    """
    if not path:
        return ""
    return PART_SUFFIX_REGEX.sub("", path.strip())


class CanonicalEvidence(BaseModel):
    """Canonical legal identity model representing ground truth legal provisions."""

    document_id: UUID = Field(description="Parent regulation document UUID")
    structural_path: str = Field(description="Hierarchical legal path string")
    page_start: int = Field(description="Start page in source PDF")
    page_end: int = Field(description="End page in source PDF")
    relevance: int = Field(
        default=3,
        ge=0,
        le=3,
        description="Graded relevance score (0: Irrelevant, 1: Context, 2: Relevant, 3: Direct)",
    )

    def normalized_path(self) -> str:
        """Return normalized structural path without chunking suffixes."""
        return normalize_structural_path(self.structural_path)

    def to_canonical_key(self) -> str:
        """Return deterministic string representation of normalized canonical legal identity."""
        return f"{self.document_id}:{self.normalized_path()}:{self.page_start}:{self.page_end}"


class GoldClaim(BaseModel):
    """Gold-annotated expected claim description and supporting canonical evidence."""

    claim_id: str = Field(description="Unique claim identifier")
    claim_description: str = Field(description="Human-readable claim description")
    supporting_evidence: list[CanonicalEvidence] = Field(
        default_factory=list, description="Structured canonical evidence supporting claim"
    )


class GoldGeneration(BaseModel):
    """Gold generation targets for evaluation sample."""

    expected_abstain: bool = Field(
        default=False, description="Flag indicating if system should abstain"
    )
    expected_claims: list[GoldClaim] = Field(
        default_factory=list, description="Gold-annotated expected claims list"
    )


class EvalSample(BaseModel):
    """Single benchmark evaluation test sample."""

    sample_id: str = Field(description="Unique evaluation sample identifier")
    query: str = Field(description="Test query string")
    query_type: str = Field(
        default="in_domain", description="Query type ('in_domain' or 'out_of_domain')"
    )
    canonical_ground_truth: list[CanonicalEvidence] = Field(
        default_factory=list, description="Ground truth canonical legal provisions list"
    )
    gold_generation: GoldGeneration | None = Field(
        default=None, description="Gold generation targets if applicable"
    )


class EvalDataset(BaseModel):
    """Complete benchmark evaluation dataset container."""

    dataset_version: str = Field(default="1.0.0", description="Dataset schema version string")
    corpus_scope: list[str] = Field(
        default_factory=lambda: ["BI"], description="Regulatory authority scope"
    )
    samples: list[EvalSample] = Field(description="List of evaluation samples")


class RetrievalStageMetrics(BaseModel):
    """Calculated metrics for a specific retrieval pipeline stage."""

    stage_name: str = Field(description="Retrieval stage name (e.g. 'Stage 4: Hybrid + Rerank')")
    mrr_1: float = Field(description="Mean Reciprocal Rank @ 1 (≡ HitRate@1)")
    mrr_5: float = Field(description="Mean Reciprocal Rank @ 5")
    mrr_10: float = Field(description="Mean Reciprocal Rank @ 10")
    hit_rate_1: float = Field(description="Hit Rate @ 1")
    hit_rate_5: float = Field(description="Hit Rate @ 5")
    hit_rate_10: float = Field(description="Hit Rate @ 10")
    ndcg_5: float = Field(description="Normalized Discounted Cumulative Gain @ 5")
    ndcg_10: float = Field(description="Normalized Discounted Cumulative Gain @ 10")
    precision_5: float = Field(description="Precision @ 5")
    recall_5: float = Field(description="Recall @ 5")


class GenerationMetrics(BaseModel):
    """Calculated metrics for Phase 6 Grounded RAG Answer Generation."""

    total_samples: int = Field(description="Total evaluation samples evaluated")
    citation_validity: float = Field(description="Proportion of valid citation tags")
    citation_precision: float = Field(
        description="Proportion of citations matching canonical ground truth"
    )
    citation_recall: float = Field(description="Proportion of ground truth provisions cited")
    grounding_coverage: float = Field(
        description="Proportion of generated claims containing citations"
    )
    gold_claim_coverage: float = Field(
        description="Proportion of gold claims with supporting citations"
    )
    unsupported_claim_rate: float = Field(
        description="Proportion of claims lacking valid citations"
    )
    abstention_accuracy: float = Field(description="Accuracy of abstention decisions")


class BenchmarkReport(BaseModel):
    """Complete benchmark execution report container."""

    model_config = ConfigDict(protected_namespaces=())

    benchmark_timestamp: str = Field(description="ISO timestamp of benchmark execution run")
    dataset_version: str = Field(description="Dataset version evaluated")
    total_samples: int = Field(description="Total query samples in benchmark")
    retrieval_stages: list[RetrievalStageMetrics] = Field(
        description="Metrics across retrieval stages"
    )
    generation_metrics: GenerationMetrics | None = Field(
        default=None, description="Generation & grounding evaluation metrics"
    )
