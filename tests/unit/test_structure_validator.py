"""Unit tests for StructureValidator character coverage ratio calculation."""

from uuid import uuid4

import pytest

from finreg.documents.models import (
    NodeType,
    NormalizedLine,
    ParsingValidationError,
    StructuredNode,
)
from finreg.documents.validator import StructureValidator


def test_non_overlapping_character_coverage_calculation() -> None:
    """Verify character coverage ratio sums text without double counting container parents."""
    validator = StructureValidator(min_coverage_ratio=0.90)

    doc_id = uuid4()
    version_id = uuid4()

    leaf_text_1 = "Bank Indonesia berwenang mengatur transfer dana."
    leaf_text_2 = "Penyelenggara wajib memenuhi modal minimum."

    lines = [
        NormalizedLine(text=leaf_text_1, page_num=1, line_num=1),
        NormalizedLine(text=leaf_text_2, page_num=1, line_num=2),
    ]

    # Chapter container node with empty text, containing Paragraph leaf node
    nodes = [
        StructuredNode(
            node_type=NodeType.CHAPTER,
            node_number="I",
            title="KETENTUAN UMUM",
            text="",  # Empty container text
            children=[
                StructuredNode(
                    node_type=NodeType.PARAGRAPH,
                    node_number="1",
                    text=leaf_text_1,
                ),
                StructuredNode(
                    node_type=NodeType.PARAGRAPH,
                    node_number="2",
                    text=leaf_text_2,
                ),
            ],
        )
    ]

    report = validator.validate(
        document_id=doc_id,
        version_id=version_id,
        lines=lines,
        nodes=nodes,
        total_pages=1,
        raise_on_failure=True,
    )

    assert report.extracted_characters == len(leaf_text_1) + len(leaf_text_2)
    assert report.structured_characters == len(leaf_text_1) + len(leaf_text_2)
    assert report.coverage_ratio == 1.0
    assert report.is_valid is True


def test_acceptance_threshold_enforcement() -> None:
    """Verify validation raises error when coverage_ratio < threshold."""
    validator = StructureValidator(min_coverage_ratio=0.90)

    doc_id = uuid4()
    version_id = uuid4()

    full_text = (
        "Teks regulasi sangat panjang yang sebagian besar tidak berhasil diparse oleh parser..."
    )
    lines = [NormalizedLine(text=full_text, page_num=1, line_num=1)]

    # Only a small fraction is captured in structured node
    nodes = [
        StructuredNode(
            node_type=NodeType.PARAGRAPH,
            node_number="1",
            text="Teks regulasi",  # Very short text compared to full_text
        )
    ]

    with pytest.raises(ParsingValidationError) as exc_info:
        validator.validate(
            document_id=doc_id,
            version_id=version_id,
            lines=lines,
            nodes=nodes,
            total_pages=1,
            raise_on_failure=True,
        )

    assert "Coverage ratio" in str(exc_info.value)
