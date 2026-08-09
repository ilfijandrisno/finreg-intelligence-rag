"""Integration tests for document_nodes database persistence and composite FK integrity."""

import os
import tempfile

import pymupdf as fitz
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from finreg.database.connection import get_engine, get_session_factory
from finreg.database.models import (
    DocumentNodeORM,
    DocumentORM,
    DocumentVersionORM,
    RegulationORM,
)
from finreg.documents.models import NoCurrentDocumentVersionError
from finreg.documents.service import DocumentParsingService


def create_sample_pdf_on_disk(file_path: str) -> None:
    """Create sample PDF document on disk for integration testing."""
    doc = fitz.open()

    page1 = doc.new_page()
    page1.insert_text((50, 50), "PERATURAN BANK INDONESIA NOMOR 23/13/PBI/2021")
    page1.insert_text((50, 100), "BAB I KETENTUAN UMUM")
    page1.insert_text((50, 150), "Pasal 1 Dalam Peraturan ini yang dimaksud dengan:")
    page1.insert_text((50, 180), "(1) Bank Indonesia berwenang mengatur transfer dana.")

    doc.save(file_path)
    doc.close()


def test_document_nodes_persistence_and_idempotency() -> None:
    """Verify document_nodes DB persistence and repeated parsing idempotency."""
    engine = get_engine()
    session_factory = get_session_factory(engine)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = tmp_file.name

    create_sample_pdf_on_disk(pdf_path)

    session: Session = session_factory()
    try:
        # Create parent regulation, document, and current version
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number="99/PARSER/TEST/2026",
            title="Peraturan Uji Coba Parser",
            detail_url="https://example.com/parser-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url="https://example.com/parser-test.pdf",
            filename="parser_test.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        version = DocumentVersionORM(
            document_id=doc.id,
            sha256="dummy_parser_sha256_checksum_hash_value_12345",
            storage_path=pdf_path,
            content_length=1024,
            is_current=True,
        )
        session.add(version)
        session.commit()

        service = DocumentParsingService(session_factory=session_factory)
        service.validator.min_coverage_ratio = 0.50

        # 1. Initial Parsing Run
        report_1, nodes_1 = service.parse_document(document_id=doc.id, dry_run=False)
        assert report_1.is_valid is True
        assert report_1.structured_characters > 0

        # Verify document_nodes created in DB
        nodes_db_1 = list(
            session.scalars(select(DocumentNodeORM).where(DocumentNodeORM.document_id == doc.id))
        )
        assert len(nodes_db_1) >= 3
        first_count = len(nodes_db_1)

        # 2. Repeated Parsing Run (Idempotency Check)
        report_2, nodes_2 = service.parse_document(document_id=doc.id, dry_run=False)
        assert report_2.is_valid is True

        # Verify old nodes were replaced atomically and total node count remains identical
        nodes_db_2 = list(
            session.scalars(select(DocumentNodeORM).where(DocumentNodeORM.document_id == doc.id))
        )
        assert len(nodes_db_2) == first_count

    finally:
        session.delete(reg)
        session.commit()
        session.close()

        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


def test_composite_fk_mismatched_version_rejection() -> None:
    """Verify repository rejects document_node persistence for mismatched version."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number="99/MISMATCH/TEST/2026",
            title="Peraturan Uji Mismatch",
            detail_url="https://example.com/mismatch-test",
        )
        session.add(reg)
        session.flush()

        doc1 = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url="https://example.com/doc1.pdf",
            filename="doc1.pdf",
            content_type="application/pdf",
        )
        doc2 = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url="https://example.com/doc2.pdf",
            filename="doc2.pdf",
            content_type="application/pdf",
        )
        session.add_all([doc1, doc2])
        session.flush()

        ver1 = DocumentVersionORM(
            document_id=doc1.id,
            sha256="sha256_ver1_hash",
            storage_path="path1.pdf",
            content_length=100,
            is_current=True,
        )
        session.add(ver1)
        session.commit()

        from finreg.database.repository import IngestionRepository

        repo = IngestionRepository(session)

        # Attempt to insert nodes for doc2 using ver1 (belonging to doc1)
        with pytest.raises(ValueError) as exc_info:
            repo.replace_document_nodes(
                document_id=doc2.id,
                document_version_id=ver1.id,
                nodes=[],
            )

        assert "does not belong to Document" in str(exc_info.value)

    finally:
        session.delete(reg)
        session.commit()
        session.close()


def test_missing_current_document_version_error() -> None:
    """Verify parsing raises NoCurrentDocumentVersionError when no version is current."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number="99/NOVERSION/TEST/2026",
            title="Peraturan Tanpa Versi Aktif",
            detail_url="https://example.com/no-version-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url="https://example.com/noversion.pdf",
            filename="noversion.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        # Inactive version (is_current=False)
        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256="sha256_inactive_hash",
            storage_path="inactive.pdf",
            content_length=100,
            is_current=False,
        )
        session.add(ver)
        session.commit()

        service = DocumentParsingService(session_factory=session_factory)

        with pytest.raises(NoCurrentDocumentVersionError) as exc_info:
            service.parse_document(document_id=doc.id, dry_run=False)

        assert "No active current document version" in str(exc_info.value)

    finally:
        session.delete(reg)
        session.commit()
        session.close()
