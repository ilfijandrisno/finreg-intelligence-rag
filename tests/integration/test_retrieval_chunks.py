"""Integration tests for retrieval_chunks database persistence, FK integrity, and idempotency."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from finreg.database.connection import get_engine, get_session_factory
from finreg.database.models import (
    DocumentNodeORM,
    DocumentORM,
    DocumentVersionORM,
    RegulationORM,
    RetrievalChunkORM,
)
from finreg.documents.chunk_service import DocumentChunkingService


def test_retrieval_chunks_persistence_and_idempotency() -> None:
    """Verify retrieval_chunks DB persistence, non-null source_node_id, and repeated idempotency."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        # 1. Setup test Regulation, Document, Version, and DocumentNode
        unique_num = f"CHUNK-TEST-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Peraturan Uji Coba Chunking",
            detail_url="https://example.com/chunk-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/chunk-test-{unique_num}.pdf",
            filename=f"chunk_test_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_storage.pdf",
            content_length=12345,
            is_current=True,
        )
        session.add(ver)
        session.flush()

        # Insert a root article and leaf paragraph node into document_nodes
        art_node = DocumentNodeORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            parent_id=None,
            node_type="article",
            node_number="1",
            title=None,
            text="",
            page_start=1,
            page_end=1,
            sequence=1,
            path="Pasal 1",
        )
        session.add(art_node)
        session.flush()

        para_node = DocumentNodeORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            parent_id=art_node.id,
            node_type="paragraph",
            node_number="1",
            title=None,
            text="Tujuan pengawasan adalah menjamin kelancaran sistem pembayaran.",
            page_start=1,
            page_end=1,
            sequence=2,
            path="Pasal 1/Ayat (1)",
        )
        session.add(para_node)
        session.commit()

        # 2. First Chunking Execution (Persistence)
        service = DocumentChunkingService()
        report1, chunks1 = service.chunk_document(
            document_id=doc.id, dry_run=False, session=session
        )

        assert report1.is_valid is True
        assert report1.source_text_coverage == 1.0

        # Query database for persisted chunks
        db_chunks1 = list(
            session.scalars(
                select(RetrievalChunkORM).where(RetrievalChunkORM.document_id == doc.id)
            )
        )
        assert len(db_chunks1) == 1
        assert db_chunks1[0].source_node_id == para_node.id
        expected_text = "Tujuan pengawasan adalah menjamin kelancaran sistem pembayaran."
        assert db_chunks1[0].chunk_text == expected_text
        assert db_chunks1[0].sequence == 1
        hash1 = db_chunks1[0].chunk_hash

        # 3. Second Chunking Execution (Idempotency Check)
        report2, chunks2 = service.chunk_document(
            document_id=doc.id, dry_run=False, session=session
        )

        assert report2.is_valid is True
        db_chunks2 = list(
            session.scalars(
                select(RetrievalChunkORM).where(RetrievalChunkORM.document_id == doc.id)
            )
        )
        assert len(db_chunks2) == 1
        assert db_chunks2[0].chunk_hash == hash1  # Identical hash

    finally:
        session.close()


def test_dry_run_causes_zero_db_mutations() -> None:
    """Verify that --dry-run execution performs zero database mutations."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        unique_num = f"DRY-TEST-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Peraturan Dry Run Test",
            detail_url="https://example.com/dry-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/dry-{unique_num}.pdf",
            filename=f"dry_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_dry.pdf",
            content_length=54321,
            is_current=True,
        )
        session.add(ver)
        session.flush()

        para_node = DocumentNodeORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            parent_id=None,
            node_type="paragraph",
            node_number="1",
            title=None,
            text="Ketentuan dry run.",
            page_start=1,
            page_end=1,
            sequence=1,
            path="Pasal 1/Ayat (1)",
        )
        session.add(para_node)
        session.commit()

        service = DocumentChunkingService()
        report, chunks = service.chunk_document(document_id=doc.id, dry_run=True, session=session)

        assert report.is_valid is True
        assert len(chunks) == 1

        # Query database to confirm 0 rows in retrieval_chunks
        db_chunks = list(
            session.scalars(
                select(RetrievalChunkORM).where(RetrievalChunkORM.document_id == doc.id)
            )
        )
        assert len(db_chunks) == 0

    finally:
        session.close()
