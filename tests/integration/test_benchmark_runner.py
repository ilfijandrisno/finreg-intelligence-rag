"""Offline integration tests for Phase 8 BenchmarkRunner."""

from pathlib import Path
from uuid import uuid4

from finreg.evaluation.benchmark_runner import BenchmarkRunner
from finreg.evaluation.eval_models import (
    CanonicalEvidence,
    EvalDataset,
    EvalSample,
    GoldClaim,
    GoldGeneration,
)
from finreg.hybrid.hybrid_models import HybridSearchResult
from finreg.rag.providers import MockLLMProvider
from finreg.rag.service import RAGService
from finreg.reranking.rerank_models import RerankedSearchResult


def _make_hybrid_result(doc_id: uuid4, path: str) -> HybridSearchResult:
    return HybridSearchResult(
        fused_score=0.032,
        dense_rank=1,
        lexical_rank=1,
        dense_score=0.9,
        lexical_score=4.0,
        retrieval_method="hybrid",
        chunk_id=uuid4(),
        source_node_id=uuid4(),
        document_id=doc_id,
        document_version_id=uuid4(),
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Title",
        structural_path=path,
        chunk_text="text",
        contextual_text="header\n\ntext",
        page_start=1,
        page_end=1,
        sequence=1,
    )


def _make_reranked_result(doc_id: uuid4, path: str) -> RerankedSearchResult:
    return RerankedSearchResult(
        rerank_score=0.95,
        rerank_rank=1,
        fused_score=0.032,
        dense_rank=1,
        lexical_rank=1,
        dense_score=0.9,
        lexical_score=4.0,
        retrieval_method="hybrid",
        chunk_id=uuid4(),
        source_node_id=uuid4(),
        document_id=doc_id,
        document_version_id=uuid4(),
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Title",
        structural_path=path,
        chunk_text="text",
        contextual_text="header\n\ntext",
        page_start=1,
        page_end=1,
        sequence=1,
    )


class MockVectorService:
    def __init__(self, doc_id: uuid4):
        self.doc_id = doc_id

    def search(self, **kwargs):
        return [_make_hybrid_result(self.doc_id, "Pasal 1")]


class MockLexicalService:
    def __init__(self, doc_id: uuid4):
        self.doc_id = doc_id

    def search(self, **kwargs):
        return [_make_hybrid_result(self.doc_id, "Pasal 1")], None


class MockHybridService:
    def __init__(self, doc_id: uuid4):
        self.doc_id = doc_id

    def search(self, **kwargs):
        return [_make_hybrid_result(self.doc_id, "Pasal 1")], None


class MockRerankingService:
    def __init__(self, doc_id: uuid4):
        self.doc_id = doc_id

    def search(self, **kwargs):
        return [_make_reranked_result(self.doc_id, "Pasal 1")], None


def test_benchmark_runner_offline_execution(tmp_path: Path) -> None:
    """Verify BenchmarkRunner executes 100% offline using mock services."""
    doc_id = uuid4()
    ev = CanonicalEvidence(
        document_id=doc_id, structural_path="Pasal 1", page_start=1, page_end=1, relevance=3
    )

    sample = EvalSample(
        sample_id="eval-1",
        query="test query",
        canonical_ground_truth=[ev],
        gold_generation=GoldGeneration(
            expected_abstain=False,
            expected_claims=[
                GoldClaim(claim_id="c1", claim_description="test claim", supporting_evidence=[ev])
            ],
        ),
    )
    dataset = EvalDataset(dataset_version="1.0.0", samples=[sample])

    v_svc = MockVectorService(doc_id)
    l_svc = MockLexicalService(doc_id)
    h_svc = MockHybridService(doc_id)
    r_svc = MockRerankingService(doc_id)
    rag_svc = RAGService(llm_provider=MockLLMProvider(), reranking_service=r_svc)

    runner = BenchmarkRunner(
        vector_service=v_svc,
        lexical_service=l_svc,
        hybrid_service=h_svc,
        reranking_service=r_svc,
        rag_service=rag_svc,
    )

    report = runner.run_benchmark(dataset)

    assert report.total_samples == 1
    assert len(report.retrieval_stages) == 4
    assert report.retrieval_stages[0].hit_rate_5 == 1.0
    assert report.retrieval_stages[3].hit_rate_5 == 1.0
    assert report.generation_metrics is not None
    assert report.generation_metrics.citation_validity == 1.0

    json_art, md_art = runner.export_reports(report, tmp_path)
    assert json_art.exists()
    assert md_art.exists()

    md_text = md_art.read_text(encoding="utf-8")
    assert "FinReg Intelligence RAG Evaluation Benchmark Report" in md_text
    assert "Stage 4: Hybrid + Rerank" in md_text
