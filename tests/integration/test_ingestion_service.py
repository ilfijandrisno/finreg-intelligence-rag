"""Integration tests for IngestionService database persistence, idempotency, and versioning."""

import tempfile
from datetime import date
from unittest.mock import MagicMock

from sqlalchemy import select
from sqlalchemy.orm import Session

from finreg.database.connection import get_engine, get_session_factory
from finreg.database.models import DocumentORM, DocumentVersionORM, RegulationORM
from finreg.ingestion.downloader import DownloadManager
from finreg.ingestion.models import (
    DocumentReference,
    DocumentType,
    DownloadResult,
    RegulationMetadata,
    RegulationReference,
)
from finreg.ingestion.service import IngestionService
from finreg.ingestion.storage import LocalStorageManager


class DummyAdapter:
    """Mock RegulatorySourceAdapter for testing ingestion service without live network calls."""

    def __init__(self, doc_url: str):
        self.doc_url = doc_url

    @property
    def source_name(self) -> str:
        return "TEST_BI"

    @property
    def target_regulation_type(self) -> str:
        return "TEST_PBI"

    def discover_regulations(self, limit: int | None = None) -> list[RegulationReference]:
        return [
            RegulationReference(
                source="TEST_BI",
                regulation_type="TEST_PBI",
                regulation_number="99/1/TEST/2026",
                title="Peraturan Uji Coba Ingesti",
                detail_url="https://example.com/test-reg",
                published_date=date(2026, 1, 1),
            )
        ]

    def fetch_metadata(self, reference: RegulationReference) -> RegulationMetadata:
        meta = RegulationMetadata(
            source="TEST_BI",
            regulation_type="TEST_PBI",
            regulation_number="99/1/TEST/2026",
            title="Peraturan Uji Coba Ingesti",
            sector="Uji Coba",
            status="Berlaku",
            detail_url=reference.detail_url,
        )
        meta.attachments = self.resolve_documents(meta)
        return meta

    def resolve_documents(self, metadata: RegulationMetadata) -> list[DocumentReference]:
        return [
            DocumentReference(
                document_type=DocumentType.REGULATION,
                url=self.doc_url,
                filename="test_reg.pdf",
                content_type="application/pdf",
            )
        ]


def test_ingestion_service_persistence_and_idempotency() -> None:
    """Verify IngestionService DB persistence, idempotency, and versioning contracts."""
    engine = get_engine()
    session_factory = get_session_factory(engine)

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageManager(raw_dir=tmp_dir, metadata_dir=tmp_dir)

        # Mock downloader returning initial file content
        initial_bytes = b"%PDF-1.5 Initial Regulation Document Content Payload"
        downloader = MagicMock(spec=DownloadManager)

        def mock_download(url: str) -> DownloadResult:
            sha256 = downloader.calculate_sha256(initial_bytes)
            return DownloadResult(
                url=url,
                content_bytes=initial_bytes,
                content_type="application/pdf",
                content_length=len(initial_bytes),
                sha256=sha256,
                http_status=200,
            )

        downloader.download_file.side_effect = mock_download
        downloader.calculate_sha256.side_effect = lambda b: DownloadManager().calculate_sha256(b)

        doc_url = "https://example.com/downloads/test_reg.pdf"
        adapter = DummyAdapter(doc_url=doc_url)
        service = IngestionService(
            downloader=downloader,
            storage_manager=storage,
            session_factory=session_factory,
        )

        # 1. First Ingestion Run
        summary_1 = service.run_ingestion(adapter, limit=1, dry_run=False)
        assert summary_1.discovered == 1
        assert summary_1.downloaded == 1
        assert summary_1.skipped == 0
        assert summary_1.new_versions == 1

        # Verify DB records created
        session: Session = session_factory()
        try:
            reg = session.scalar(
                select(RegulationORM).where(RegulationORM.regulation_number == "99/1/TEST/2026")
            )
            assert reg is not None
            assert reg.source == "TEST_BI"

            doc = session.scalar(select(DocumentORM).where(DocumentORM.regulation_id == reg.id))
            assert doc is not None
            assert doc.document_url == doc_url

            versions = list(
                session.scalars(
                    select(DocumentVersionORM).where(DocumentVersionORM.document_id == doc.id)
                )
            )
            assert len(versions) == 1
            assert versions[0].is_current is True
        finally:
            session.close()

        # 2. Second Ingestion Run (Idempotency Check - Unchanged Content)
        summary_2 = service.run_ingestion(adapter, limit=1, dry_run=False)
        assert summary_2.discovered == 1
        assert summary_2.downloaded == 0
        assert summary_2.skipped == 1
        assert summary_2.new_versions == 0

        # Verify zero new version rows created
        session = session_factory()
        try:
            versions_2 = list(
                session.scalars(
                    select(DocumentVersionORM).where(DocumentVersionORM.document_id == doc.id)
                )
            )
            assert len(versions_2) == 1
            assert versions_2[0].is_current is True
        finally:
            session.close()

        # 3. Third Ingestion Run (Updated Content -> New Version Detection)
        updated_bytes = b"%PDF-1.5 UPDATED Regulation Document Content Payload v2"

        def mock_download_updated(url: str) -> DownloadResult:
            sha256 = downloader.calculate_sha256(updated_bytes)
            return DownloadResult(
                url=url,
                content_bytes=updated_bytes,
                content_type="application/pdf",
                content_length=len(updated_bytes),
                sha256=sha256,
                http_status=200,
            )

        downloader.download_file.side_effect = mock_download_updated

        summary_3 = service.run_ingestion(adapter, limit=1, dry_run=False)
        assert summary_3.discovered == 1
        assert summary_3.downloaded == 1
        assert summary_3.skipped == 0
        assert summary_3.new_versions == 1

        # Verify version tracking and partial index current invariant
        session = session_factory()
        try:
            versions_3 = list(
                session.scalars(
                    select(DocumentVersionORM)
                    .where(DocumentVersionORM.document_id == doc.id)
                    .order_by(DocumentVersionORM.first_seen_at)
                )
            )
            assert len(versions_3) == 2

            current_versions = [v for v in versions_3 if v.is_current]
            assert len(current_versions) == 1
            assert current_versions[0].sha256 == downloader.calculate_sha256(updated_bytes)
        finally:
            # Cleanup test data from DB
            session.delete(reg)
            session.commit()
            session.close()
