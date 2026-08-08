"""Unit tests for core domain entity models and value objects."""

from datetime import date
from uuid import uuid4

from finreg.domain.models import (
    Chunk,
    Citation,
    Document,
    DocumentVersion,
    IssuerType,
    Regulation,
    RegulationRelationship,
    RelationshipType,
    Section,
)


def test_regulation_model_creation() -> None:
    """Verify Regulation domain model instantiation and default attributes."""
    reg = Regulation(
        issuer=IssuerType.BANK_INDONESIA,
        regulation_number="23/13/PBI/2021",
        title="Peraturan Bank Indonesia tentang Kehati-hatian dalam Kegiatan Transfer Dana",
        category="Peraturan Bank Indonesia",
        effective_date=date(2021, 12, 1),
    )
    assert reg.issuer == IssuerType.BANK_INDONESIA
    assert reg.regulation_number == "23/13/PBI/2021"
    assert reg.is_active is True
    assert reg.id is not None


def test_document_and_version_creation() -> None:
    """Verify Document and DocumentVersion model instantiation."""
    reg_id = uuid4()
    doc = Document(
        regulation_id=reg_id,
        file_name="PBI_23132021.pdf",
        source_url="https://www.bi.go.id/id/peraturan/PBI_23132021.pdf",  # type: ignore[arg-type]
    )
    assert doc.regulation_id == reg_id
    assert doc.file_type == "pdf"

    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=1024500,
    )
    assert version.document_id == doc.id
    assert version.version_number == 1


def test_section_and_chunk_creation() -> None:
    """Verify Section and Chunk domain model creation."""
    doc_ver_id = uuid4()
    section = Section(
        document_version_id=doc_ver_id,
        level=1,
        title="Pasal 1",
        content="Dalam Peraturan Bank Indonesia ini yang dimaksud dengan...",
        order_index=1,
    )
    assert section.title == "Pasal 1"
    assert section.level == 1

    chunk = Chunk(
        section_id=section.id,
        content=section.content,
        token_count=12,
        position_index=0,
        chunk_hash="abc123hash",
    )
    assert chunk.section_id == section.id
    assert chunk.token_count == 12


def test_regulation_relationship_and_citation() -> None:
    """Verify RegulationRelationship and Citation value objects."""
    reg_1 = uuid4()
    reg_2 = uuid4()

    rel = RegulationRelationship(
        source_regulation_id=reg_1,
        target_regulation_id=reg_2,
        relationship_type=RelationshipType.AMENDS,
    )
    assert rel.relationship_type == RelationshipType.AMENDS

    citation = Citation(
        regulation_number="23/13/PBI/2021",
        section_title="Pasal 1 Ayat (2)",
        text_snippet="Transfer dana dilaksanakan melalui sistem pembayaran...",
        source_url="https://www.bi.go.id/id/peraturan/PBI_23132021.pdf",
    )
    assert citation.regulation_number == "23/13/PBI/2021"
    assert citation.section_title == "Pasal 1 Ayat (2)"
