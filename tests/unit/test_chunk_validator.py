"""Unit tests for ChunkValidator legal chunk validation metrics."""

from uuid import uuid4

import pytest

from finreg.documents.chunk_models import ChunkingValidationError
from finreg.documents.chunk_validator import ChunkValidator
from finreg.documents.chunker import SemanticLegalChunker
from finreg.documents.models import NodeType, StructuredNode


def test_chunk_validator_valid_set() -> None:
    """Verify ChunkValidator passes on 100% leaf text coverage with clean metadata."""
    doc_id = uuid4()
    ver_id = uuid4()
    node_id = uuid4()

    leaf_node = StructuredNode(
        id=node_id,
        node_type=NodeType.PARAGRAPH,
        node_number="1",
        title=None,
        text="Ketentuan umum berlaku.",
        page_start=1,
        page_end=1,
        sequence=1,
        path="Pasal 1/Ayat (1)",
    )

    chunker = SemanticLegalChunker()
    chunks = chunker.chunk_document_tree(
        document_id=doc_id,
        version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        nodes=[leaf_node],
    )

    validator = ChunkValidator()
    report = validator.validate(
        document_id=doc_id,
        version_id=ver_id,
        nodes=[leaf_node],
        chunks=chunks,
        raise_on_failure=True,
    )

    assert report.is_valid is True
    assert report.source_text_coverage == 1.0
    assert report.leaf_source_characters == len("Ketentuan umum berlaku.")
    assert report.chunked_characters == len("Ketentuan umum berlaku.")


def test_chunk_validator_fails_on_coverage_mismatch() -> None:
    """Verify ChunkValidator raises ChunkingValidationError on leaf coverage mismatch."""
    doc_id = uuid4()
    ver_id = uuid4()
    node_id = uuid4()

    leaf_node = StructuredNode(
        id=node_id,
        node_type=NodeType.PARAGRAPH,
        node_number="1",
        title=None,
        text="Text inside source node.",
        page_start=1,
        page_end=1,
        sequence=1,
        path="Pasal 1/Ayat (1)",
    )

    validator = ChunkValidator()
    with pytest.raises(ChunkingValidationError) as exc_info:
        validator.validate(
            document_id=doc_id,
            version_id=ver_id,
            nodes=[leaf_node],
            chunks=[],  # Zero chunks -> 0% coverage
            raise_on_failure=True,
        )

    assert exc_info.value.report.is_valid is False
    assert exc_info.value.report.source_text_coverage == 0.0
