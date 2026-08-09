"""Unit tests for HybridSearchResult and HybridExecutionReport schemas."""

from uuid import uuid4

from finreg.hybrid.hybrid_models import HybridExecutionReport, HybridSearchResult


def test_hybrid_search_result_formatting() -> None:
    """Verify HybridSearchResult formats fused score, branch ranks, and legal provenance."""
    chunk_id = uuid4()
    node_id = uuid4()
    doc_id = uuid4()
    ver_id = uuid4()

    res = HybridSearchResult(
        fused_score=0.032522,
        dense_rank=1,
        lexical_rank=2,
        dense_score=0.8845,
        lexical_score=4.5123,
        retrieval_method="hybrid",
        chunk_id=chunk_id,
        source_node_id=node_id,
        document_id=doc_id,
        document_version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Lindung Nilai Valuta Asing",
        structural_path="Pasal 1/Ayat (1)",
        chunk_text="Pengawasan kehati-hatian.",
        contextual_text="Header\n\nPengawasan kehati-hatian.",
        page_start=1,
        page_end=1,
        sequence=1,
    )

    assert res.fused_score == 0.032522
    assert res.dense_rank == 1
    assert res.lexical_rank == 2
    assert res.dense_score == 0.8845
    assert res.lexical_score == 4.5123
    assert res.retrieval_method == "hybrid"
    assert res.chunk_id == chunk_id


def test_hybrid_execution_report() -> None:
    """Verify HybridExecutionReport holds diagnostic metrics."""
    report = HybridExecutionReport(
        dense_candidates_count=20,
        lexical_candidates_count=20,
        fused_results_count=5,
        rrf_k=60,
    )
    assert report.dense_candidates_count == 20
    assert report.lexical_candidates_count == 20
    assert report.fused_results_count == 5
    assert report.rrf_k == 60
