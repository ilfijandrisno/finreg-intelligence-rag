"""Unit tests for LexicalSearchResult and LexicalIndexReport schemas."""

from uuid import uuid4

from finreg.lexical.lexical_models import LexicalIndexReport, LexicalSearchResult


def test_lexical_search_result_formatting() -> None:
    """Verify LexicalSearchResult formats score, matched terms, and provenance fields."""
    chunk_id = uuid4()
    node_id = uuid4()
    doc_id = uuid4()
    ver_id = uuid4()

    res = LexicalSearchResult(
        score=2.4512,
        matched_terms_count=2,
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
        contextual_text="[BI - PBI No. 20/2026] Header\n\nPengawasan kehati-hatian.",
        page_start=1,
        page_end=1,
        sequence=1,
    )

    assert res.score == 2.4512
    assert res.matched_terms_count == 2
    assert res.chunk_id == chunk_id
    assert res.source == "BI"
    assert res.regulation_type == "PBI"
    assert res.regulation_number == "20/2026"


def test_lexical_index_report() -> None:
    """Verify LexicalIndexReport holds valid diagnostic index metrics."""
    report = LexicalIndexReport(
        total_chunks=105,
        vocabulary_size=1250,
        average_doc_length=45.2,
    )
    assert report.total_chunks == 105
    assert report.vocabulary_size == 1250
    assert report.average_doc_length == 45.2
