"""Unit tests for CitationValidator strict verification and invalid citation safety failure."""

from uuid import uuid4

from finreg.rag.citation_validator import CitationValidator
from finreg.rag.context_assembler import ContextBlock
from finreg.reranking.rerank_models import RerankedSearchResult


def _make_block(context_id: str) -> ContextBlock:
    res = RerankedSearchResult(
        rerank_score=0.9,
        rerank_rank=1,
        fused_score=0.03,
        dense_rank=1,
        lexical_rank=1,
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
        title="Test",
        structural_path="Pasal 1",
        chunk_text="Tekstual",
        contextual_text="Header\n\nTekstual",
        page_start=1,
        page_end=1,
        sequence=1,
    )
    return ContextBlock(context_id=context_id, reranked_result=res, estimated_tokens=10)


def test_citation_validator_valid_extraction() -> None:
    """Verify CitationValidator extracts valid citations."""
    b1 = _make_block("C1")
    b2 = _make_block("C2")

    validator = CitationValidator()
    text = "Berdasarkan ketentuan [C1] dan [C2], lindung nilai wajib dilaksanakan."
    is_valid, valid_cits, invalid_tags = validator.validate(text, [b1, b2])

    assert is_valid is True
    assert len(valid_cits) == 2
    assert len(invalid_tags) == 0
    assert valid_cits[0].context_id == "C1"
    assert valid_cits[1].context_id == "C2"


def test_citation_validator_invalid_citation_causes_failure() -> None:
    """Verify invalid context ID [C99] causes is_valid = False under strict safety failure rule."""
    b1 = _make_block("C1")

    validator = CitationValidator()
    text = "Berdasarkan ketentuan [C1] dan [C99], transaksi valas diatur."
    is_valid, valid_cits, invalid_tags = validator.validate(text, [b1])

    assert is_valid is False
    assert invalid_tags == ["C99"]
