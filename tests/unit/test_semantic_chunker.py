"""Unit tests for SemanticLegalChunker legal document chunking logic."""

from uuid import uuid4

from finreg.documents.chunker import SemanticLegalChunker
from finreg.documents.models import NodeType, StructuredNode


def test_chunker_single_clause_article() -> None:
    """Verify chunker generates a single chunk for single-clause Article."""
    doc_id = uuid4()
    ver_id = uuid4()
    node_id = uuid4()

    para_node = StructuredNode(
        id=node_id,
        node_type=NodeType.PARAGRAPH,
        node_number=None,
        title=None,
        text="Objek pengaturan meliputi transaksi pasar valuta asing.",
        page_start=1,
        page_end=1,
        sequence=2,
        path="Pasal 3/Ayat (1)",
    )

    art_node = StructuredNode(
        node_type=NodeType.ARTICLE,
        node_number="3",
        title=None,
        text="",
        page_start=1,
        page_end=1,
        sequence=1,
        path="Pasal 3",
        children=[para_node],
    )

    chunker = SemanticLegalChunker()
    chunks = chunker.chunk_document_tree(
        document_id=doc_id,
        version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Transaksi Pasar Valuta Asing",
        nodes=[art_node],
    )

    assert len(chunks) == 1
    c = chunks[0]
    assert c.document_id == doc_id
    assert c.document_version_id == ver_id
    assert c.source_node_id == node_id
    assert c.article_number == "3"
    assert c.chunk_text == "Objek pengaturan meliputi transaksi pasar valuta asing."
    assert "BI - PBI No. 20/2026" in c.contextual_text
    assert c.part_index == 1
    assert c.total_parts == 1
    assert c.sequence == 1


def test_chunker_article_with_huruf_and_numbered_items() -> None:
    """Verify chunker extracts discrete chunks for Huruf and Numbered Item nodes."""
    doc_id = uuid4()
    ver_id = uuid4()
    huruf_id = uuid4()
    num_id = uuid4()

    num_node = StructuredNode(
        id=num_id,
        node_type=NodeType.NUMBERED_ITEM,
        node_number="1",
        title=None,
        text="Pengawasan kehati-hatian.",
        page_start=1,
        page_end=1,
        sequence=3,
        path="Pasal 1/Ayat (1)/Huruf a/1.",
    )

    huruf_node = StructuredNode(
        id=huruf_id,
        node_type=NodeType.LETTER,
        node_number="a",
        title=None,
        text="Kewenangan pengawasan meliputi:",
        page_start=1,
        page_end=1,
        sequence=2,
        path="Pasal 1/Ayat (1)/Huruf a",
        children=[num_node],
    )

    para_node = StructuredNode(
        node_type=NodeType.PARAGRAPH,
        node_number="1",
        title=None,
        text="",
        page_start=1,
        page_end=1,
        sequence=1,
        path="Pasal 1/Ayat (1)",
        children=[huruf_node],
    )

    chunker = SemanticLegalChunker()
    chunks = chunker.chunk_document_tree(
        document_id=doc_id,
        version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test Regulation",
        nodes=[para_node],
    )

    assert len(chunks) == 2
    assert chunks[0].source_node_id == huruf_id
    assert chunks[0].letter_code == "a"
    assert chunks[1].source_node_id == num_id
    assert chunks[1].numbered_item == "1"


def test_chunker_oversized_legal_unit_splitting() -> None:
    """Verify oversized legal unit (>1500 chars) uses sentence-boundary splitting."""
    doc_id = uuid4()
    ver_id = uuid4()
    node_id = uuid4()

    sentence1 = "A " * 500  # 1000 chars
    sentence2 = "B " * 500  # 1000 chars
    long_text = f"{sentence1.strip()}. {sentence2.strip()}."

    leaf_node = StructuredNode(
        id=node_id,
        node_type=NodeType.PARAGRAPH,
        node_number="1",
        title=None,
        text=long_text,
        page_start=1,
        page_end=1,
        sequence=1,
        path="Pasal 5/Ayat (1)",
    )

    chunker = SemanticLegalChunker(chunk_max_size=1200)
    chunks = chunker.chunk_document_tree(
        document_id=doc_id,
        version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        nodes=[leaf_node],
    )

    assert len(chunks) == 2
    assert chunks[0].source_node_id == node_id
    assert chunks[0].part_index == 1
    assert chunks[0].total_parts == 2
    assert "[Part 1/2]" in chunks[0].structural_path

    assert chunks[1].source_node_id == node_id
    assert chunks[1].part_index == 2
    assert chunks[1].total_parts == 2
    assert "[Part 2/2]" in chunks[1].structural_path


def test_chunk_hash_canonical_identity() -> None:
    """Verify chunk_hash is deterministic based on canonical parameters."""
    doc_id = uuid4()
    ver_id = uuid4()
    node_id = uuid4()

    leaf_node = StructuredNode(
        id=node_id,
        node_type=NodeType.PARAGRAPH,
        node_number="1",
        title=None,
        text="Sample legal text.",
        page_start=1,
        page_end=1,
        sequence=1,
        path="Pasal 1/Ayat (1)",
    )

    chunker = SemanticLegalChunker()
    chunks1 = chunker.chunk_document_tree(
        document_id=doc_id,
        version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        nodes=[leaf_node],
    )

    chunks2 = chunker.chunk_document_tree(
        document_id=doc_id,
        version_id=ver_id,
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        nodes=[leaf_node],
    )

    assert chunks1[0].chunk_hash == chunks2[0].chunk_hash
