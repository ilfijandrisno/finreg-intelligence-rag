"""Unit tests for RerankedSearchResult and RerankExecutionReport schemas."""

from uuid import uuid4

from finreg.reranking.rerank_models import RerankedSearchResult, RerankExecutionReport


def test_reranked_search_result_formatting() -> None:
    """Verify RerankedSearchResult formats score, ranks, and provenance fields."""
    chunk_id = uuid4()
    node_id = uuid4()
    doc_id = uuid4()
    ver_id = uuid4()

    res = RerankedSearchResult(
        rerank_score=0.9812,
        rerank_rank=1,
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

    assert res.rerank_score == 0.9812
    assert res.rerank_rank == 1
    assert res.fused_score == 0.032522
    assert res.retrieval_method == "hybrid"
    assert res.chunk_id == chunk_id


def test_rerank_execution_report() -> None:
    """Verify RerankExecutionReport holds diagnostic execution metrics."""
    report = RerankExecutionReport(
        model_name="BAAI/bge-reranker-v2-m3",
        candidates_in_count=20,
        reranked_out_count=5,
        execution_time_ms=45.2,
    )
    assert report.model_name == "BAAI/bge-reranker-v2-m3"
    assert report.candidates_in_count == 20
    assert report.reranked_out_count == 5
    assert report.execution_time_ms == 45.2
