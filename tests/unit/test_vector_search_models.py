"""Unit tests for VectorSearchResult formatting and distance score calculation."""

from uuid import uuid4

from finreg.vector.vector_models import VectorSearchResult


def test_vector_search_result_formatting() -> None:
    """Verify VectorSearchResult correctly formats score, distance, and provenance fields."""
    chunk_id = uuid4()
    node_id = uuid4()
    doc_id = uuid4()
    ver_id = uuid4()

    res = VectorSearchResult(
        score=0.85,
        distance=0.15,
        chunk_id=chunk_id,
        source_node_id=node_id,
        document_id=doc_id,
        document_version_id=ver_id,
        embedding_model="text-embedding-3-small",
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Lindung Nilai Valuta Asing",
        structural_path="Pasal 1/Ayat (1)",
        chunk_text="Pengawasan kehati-hatian.",
        contextual_text=(
            "[BI - PBI No. 20/2026] Lindung Nilai\n"
            "Hierarki: Pasal 1/Ayat (1)\n\n"
            "Pengawasan kehati-hatian."
        ),
        page_start=1,
        page_end=1,
        sequence=1,
    )

    assert res.score == 0.85
    assert res.distance == 0.15
    assert res.chunk_id == chunk_id
    assert res.source == "BI"
    assert res.regulation_type == "PBI"
    assert res.regulation_number == "20/2026"
