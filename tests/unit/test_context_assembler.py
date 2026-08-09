"""Unit tests for ContextAssembler token budgeting and context ID assignment."""

from uuid import uuid4

from finreg.rag.context_assembler import ContextAssembler
from finreg.reranking.rerank_models import RerankedSearchResult


def _make_reranked_res(idx: int, text_length: int = 400) -> RerankedSearchResult:
    text = "Ketentuan transaksi lindung nilai. " * (text_length // 30)
    return RerankedSearchResult(
        rerank_score=0.9,
        rerank_rank=idx,
        fused_score=0.03,
        dense_rank=idx,
        lexical_rank=idx,
        dense_score=0.8,
        lexical_score=4.0,
        retrieval_method="hybrid",
        chunk_id=uuid4(),
        source_node_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test Regulation",
        structural_path=f"Pasal {idx}",
        chunk_text=text,
        contextual_text=f"Header {idx}\n\n{text}",
        page_start=idx,
        page_end=idx,
        sequence=idx,
    )


def test_context_assembler_id_assignment_and_budgeting() -> None:
    """Verify ContextAssembler assigns context IDs and truncates when budget is exceeded."""
    res1 = _make_reranked_res(1, 400)
    res2 = _make_reranked_res(2, 400)

    assembler = ContextAssembler()
    # High budget fits both blocks
    blocks = assembler.assemble([res1, res2], max_context_tokens=1000)
    assert len(blocks) == 2
    assert blocks[0].context_id == "C1"
    assert blocks[1].context_id == "C2"

    # Strict low budget only fits first block
    blocks_limited = assembler.assemble([res1, res2], max_context_tokens=120)
    assert len(blocks_limited) == 1
    assert blocks_limited[0].context_id == "C1"


def test_context_assembler_empty_candidates() -> None:
    """Verify ContextAssembler handles empty candidates cleanly."""
    assembler = ContextAssembler()
    assert assembler.assemble([], max_context_tokens=4000) == []
