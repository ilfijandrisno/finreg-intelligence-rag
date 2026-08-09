"""Unit tests for Reciprocal Rank Fusion (RRF) algorithm and tie-breaking mechanics."""

from uuid import UUID, uuid4

from finreg.hybrid.fusion import reciprocal_rank_fusion
from finreg.lexical.lexical_models import LexicalSearchResult
from finreg.vector.vector_models import VectorSearchResult


def _make_vector_res(
    doc_ver_id: tuple[str, str], path: str, score: float, seq: int
) -> VectorSearchResult:
    doc_id, ver_id = UUID(doc_ver_id[0]), UUID(doc_ver_id[1])
    return VectorSearchResult(
        score=score,
        distance=round(1.0 - score, 4),
        embedding_model="text-embedding-3-small",
        chunk_id=UUID(doc_ver_id[1]),  # use as chunk_id for simple identity
        source_node_id=uuid4(),
        document_id=doc_id,
        document_version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test Regulation",
        structural_path=path,
        chunk_text="Chunk text sample",
        contextual_text="Header\n\nChunk text sample",
        page_start=1,
        page_end=1,
        sequence=seq,
    )


def _make_lexical_res(
    doc_ver_id: tuple[str, str], path: str, score: float, seq: int
) -> LexicalSearchResult:
    doc_id, ver_id = UUID(doc_ver_id[0]), UUID(doc_ver_id[1])
    return LexicalSearchResult(
        score=score,
        matched_terms_count=2,
        chunk_id=UUID(doc_ver_id[1]),
        source_node_id=uuid4(),
        document_id=doc_id,
        document_version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test Regulation",
        structural_path=path,
        chunk_text="Chunk text sample",
        contextual_text="Header\n\nChunk text sample",
        page_start=1,
        page_end=1,
        sequence=seq,
    )


def test_rrf_mathematical_correctness_and_1_based_ranking() -> None:
    """Verify RRF formula 1/(k + rank) where rank starts at 1."""
    doc_id = str(uuid4())
    chunk1_id = str(uuid4())
    chunk2_id = str(uuid4())

    # Chunk 1 is rank 1 in Dense, rank 2 in Lexical
    # Chunk 2 is rank 2 in Dense, rank 1 in Lexical
    d1 = _make_vector_res((doc_id, chunk1_id), "Pasal 1", 0.95, 1)
    d2 = _make_vector_res((doc_id, chunk2_id), "Pasal 2", 0.85, 2)

    l2 = _make_lexical_res((doc_id, chunk2_id), "Pasal 2", 5.0, 2)
    l1 = _make_lexical_res((doc_id, chunk1_id), "Pasal 1", 3.0, 1)

    k = 60
    results = reciprocal_rank_fusion(
        dense_results=[d1, d2],
        lexical_results=[l2, l1],
        rrf_k=k,
        top_k=5,
    )

    assert len(results) == 2

    # Expected score for Chunk 1: 1/(60+1) + 1/(60+2) = 1/61 + 1/62 = 0.032522
    # Expected score for Chunk 2: 1/(60+2) + 1/(60+1) = 0.032522
    expected_score = round(1.0 / 61.0 + 1.0 / 62.0, 6)

    assert results[0].fused_score == expected_score
    assert results[1].fused_score == expected_score
    assert results[0].retrieval_method == "hybrid"
    assert results[1].retrieval_method == "hybrid"

    # Tie broken by structural_path ASC: "Pasal 1" before "Pasal 2"
    assert results[0].structural_path == "Pasal 1"
    assert results[1].structural_path == "Pasal 2"


def test_single_branch_and_overlapping_chunks() -> None:
    """Verify hybrid fusion handles overlapping chunks and single-branch chunks cleanly."""
    doc_id = str(uuid4())
    chunk1_id = str(uuid4())
    chunk2_id = str(uuid4())
    chunk3_id = str(uuid4())

    d1 = _make_vector_res((doc_id, chunk1_id), "Pasal 1", 0.9, 1)
    d2 = _make_vector_res((doc_id, chunk2_id), "Pasal 2", 0.8, 2)

    l1 = _make_lexical_res((doc_id, chunk1_id), "Pasal 1", 4.0, 1)
    l3 = _make_lexical_res((doc_id, chunk3_id), "Pasal 3", 3.0, 2)

    results = reciprocal_rank_fusion(
        dense_results=[d1, d2],
        lexical_results=[l1, l3],
        rrf_k=60,
        top_k=5,
    )

    assert len(results) == 3

    # Rank 1: Chunk 1 (Hybrid) -> 1/61 + 1/61 = 0.032787
    assert results[0].chunk_id == UUID(chunk1_id)
    assert results[0].retrieval_method == "hybrid"
    assert results[0].dense_rank == 1
    assert results[0].lexical_rank == 1

    # Chunk 2 and Chunk 3 get 1/62 = 0.016129
    methods = {r.chunk_id: r.retrieval_method for r in results}
    assert methods[UUID(chunk2_id)] == "dense_only"
    assert methods[UUID(chunk3_id)] == "lexical_only"


def test_zero_candidate_branch_fallback() -> None:
    """Verify fusion works seamlessly when one retrieval branch returns zero results."""
    doc_id = str(uuid4())
    chunk1_id = str(uuid4())

    d1 = _make_vector_res((doc_id, chunk1_id), "Pasal 1", 0.9, 1)

    # Lexical branch returns []
    results = reciprocal_rank_fusion(
        dense_results=[d1],
        lexical_results=[],
        rrf_k=60,
        top_k=5,
    )

    assert len(results) == 1
    assert results[0].chunk_id == UUID(chunk1_id)
    assert results[0].retrieval_method == "dense_only"
    assert results[0].dense_rank == 1
    assert results[0].lexical_rank is None
    assert results[0].lexical_score is None


def test_configurable_rrf_k_and_top_k_slicing() -> None:
    """Verify configurable rrf_k alters score magnitude and top_k slices output."""
    doc_id = str(uuid4())
    chunks = [str(uuid4()) for _ in range(10)]

    dense_candidates = [
        _make_vector_res((doc_id, c_id), f"Pasal {i + 1}", 0.9 - i * 0.05, i + 1)
        for i, c_id in enumerate(chunks)
    ]

    results_k10 = reciprocal_rank_fusion(
        dense_results=dense_candidates,
        lexical_results=[],
        rrf_k=10,
        top_k=3,
    )

    results_k60 = reciprocal_rank_fusion(
        dense_results=dense_candidates,
        lexical_results=[],
        rrf_k=60,
        top_k=3,
    )

    assert len(results_k10) == 3
    assert len(results_k60) == 3

    # For rank 1: k=10 gives 1/11 = 0.090909; k=60 gives 1/61 = 0.016393
    assert results_k10[0].fused_score == round(1.0 / 11.0, 6)
    assert results_k60[0].fused_score == round(1.0 / 61.0, 6)
