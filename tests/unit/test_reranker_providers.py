"""Unit tests for MockRerankerProvider and deterministic tie-breaking logic."""

from uuid import UUID, uuid4

from finreg.hybrid.hybrid_models import HybridSearchResult
from finreg.reranking.providers import MockRerankerProvider, sort_reranked_candidates
from finreg.reranking.rerank_models import RerankedSearchResult


def _make_hybrid_res(
    doc_ver_id: tuple[str, str], path: str, rrf_score: float, seq: int
) -> HybridSearchResult:
    doc_id, ver_id = UUID(doc_ver_id[0]), UUID(doc_ver_id[1])
    return HybridSearchResult(
        fused_score=rrf_score,
        dense_rank=1,
        lexical_rank=1,
        dense_score=0.9,
        lexical_score=5.0,
        retrieval_method="hybrid",
        chunk_id=UUID(doc_ver_id[1]),
        source_node_id=uuid4(),
        document_id=doc_id,
        document_version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test Regulation",
        structural_path=path,
        chunk_text="Ketentuan transaksi lindung nilai.",
        contextual_text="Header\n\nKetentuan transaksi lindung nilai.",
        page_start=1,
        page_end=1,
        sequence=seq,
    )


def test_mock_reranker_provider_scoring_and_top_n_truncation() -> None:
    """Verify MockRerankerProvider scores candidates and truncates output to top_n."""
    doc_id = str(uuid4())
    c1 = _make_hybrid_res((doc_id, str(uuid4())), "Pasal 1", 0.03, 1)
    c2 = _make_hybrid_res((doc_id, str(uuid4())), "Pasal 2", 0.02, 2)

    reranker = MockRerankerProvider()
    results = reranker.rerank(query="lindung nilai", candidates=[c1, c2], top_n=1)

    assert len(results) == 1
    assert results[0].rerank_rank == 1
    assert reranker.model_name == "mock-reranker-v1"


def test_reranker_empty_and_zero_top_n_handling() -> None:
    """Verify reranker handles empty candidates and top_n <= 0 cleanly."""
    reranker = MockRerankerProvider()
    assert reranker.rerank("query", candidates=[], top_n=5) == []
    cand = _make_hybrid_res((str(uuid4()), str(uuid4())), "P1", 0.01, 1)
    assert reranker.rerank("query", candidates=[cand], top_n=0) == []


def test_deterministic_7_key_tie_breaking_order() -> None:
    """Verify sort_reranked_candidates applies 7-key tie-breaking hierarchy."""
    doc_id = uuid4()
    ver_id = uuid4()

    r2 = RerankedSearchResult(
        rerank_score=0.95,
        rerank_rank=1,
        fused_score=0.03,
        dense_rank=2,
        lexical_rank=2,
        dense_score=0.8,
        lexical_score=4.0,
        retrieval_method="hybrid",
        chunk_id=uuid4(),
        source_node_id=uuid4(),
        document_id=doc_id,
        document_version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        structural_path="Pasal 2",
        chunk_text="Text 2",
        contextual_text="Header 2",
        page_start=2,
        page_end=2,
        sequence=2,
    )

    r1 = RerankedSearchResult(
        rerank_score=0.95,
        rerank_rank=1,
        fused_score=0.03,
        dense_rank=1,
        lexical_rank=1,
        dense_score=0.9,
        lexical_score=5.0,
        retrieval_method="hybrid",
        chunk_id=uuid4(),
        source_node_id=uuid4(),
        document_id=doc_id,
        document_version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        structural_path="Pasal 1",
        chunk_text="Text 1",
        contextual_text="Header 1",
        page_start=1,
        page_end=1,
        sequence=1,
    )

    # Identical rerank_score and fused_score: tie broken by dense_rank ASC (1 before 2)
    sorted_res = sort_reranked_candidates([r2, r1])
    assert sorted_res[0].structural_path == "Pasal 1"
    assert sorted_res[0].rerank_rank == 1
    assert sorted_res[1].structural_path == "Pasal 2"
    assert sorted_res[1].rerank_rank == 2
