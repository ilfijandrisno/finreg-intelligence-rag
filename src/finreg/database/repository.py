"""Ingestion repository managing relational persistence and idempotency logic."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from finreg.database.models import DocumentORM, DocumentVersionORM, RegulationORM
from finreg.ingestion.models import DocumentReference, RegulationMetadata

logger = logging.getLogger(__name__)


class IngestionRepository:
    """Repository handling database operations for regulations, documents, and versions."""

    def __init__(self, session: Session):
        self.session = session

    def upsert_regulation(self, metadata: RegulationMetadata) -> RegulationORM:
        """Upsert a regulation record based on (source, regulation_type, regulation_number)."""
        stmt = select(RegulationORM).where(
            RegulationORM.source == metadata.source,
            RegulationORM.regulation_type == metadata.regulation_type,
            RegulationORM.regulation_number == metadata.regulation_number,
        )
        existing = self.session.scalar(stmt)

        if existing:
            existing.title = metadata.title
            existing.sector = metadata.sector or existing.sector
            existing.subsector = metadata.subsector or existing.subsector
            existing.status = metadata.status or existing.status
            existing.published_date = metadata.published_date or existing.published_date
            existing.effective_date = metadata.effective_date or existing.effective_date
            existing.detail_url = metadata.detail_url
            existing.summary = metadata.summary or existing.summary
            existing.abstract = metadata.abstract or existing.abstract
            existing.updated_at = datetime.now(UTC)
            logger.debug(
                "Updated regulation record: %s %s %s",
                existing.source,
                existing.regulation_type,
                existing.regulation_number,
            )
            return existing

        reg = RegulationORM(
            source=metadata.source,
            regulation_type=metadata.regulation_type,
            regulation_number=metadata.regulation_number,
            title=metadata.title,
            sector=metadata.sector,
            subsector=metadata.subsector,
            status=metadata.status,
            published_date=metadata.published_date,
            effective_date=metadata.effective_date,
            detail_url=metadata.detail_url,
            summary=metadata.summary,
            abstract=metadata.abstract,
        )
        self.session.add(reg)
        self.session.flush()
        logger.info(
            "Created regulation record: %s %s %s (ID: %s)",
            reg.source,
            reg.regulation_type,
            reg.regulation_number,
            reg.id,
        )
        return reg

    def get_or_create_document(
        self, regulation_id: UUID, doc_ref: DocumentReference
    ) -> DocumentORM:
        """Get or create a document record based on (regulation_id, document_type, document_url)."""
        stmt = select(DocumentORM).where(
            DocumentORM.regulation_id == regulation_id,
            DocumentORM.document_type == doc_ref.document_type.value,
            DocumentORM.document_url == doc_ref.url,
        )
        existing = self.session.scalar(stmt)

        if existing:
            return existing

        doc = DocumentORM(
            regulation_id=regulation_id,
            document_type=doc_ref.document_type.value,
            document_url=doc_ref.url,
            filename=doc_ref.filename,
            content_type=doc_ref.content_type,
        )
        self.session.add(doc)
        self.session.flush()
        logger.info(
            "Created document record: %s (%s) (ID: %s)",
            doc.filename,
            doc.document_type,
            doc.id,
        )
        return doc

    def get_document_version(self, document_id: UUID, sha256: str) -> DocumentVersionORM | None:
        """Fetch a specific version of a document by (document_id, sha256)."""
        stmt = select(DocumentVersionORM).where(
            DocumentVersionORM.document_id == document_id,
            DocumentVersionORM.sha256 == sha256,
        )
        return self.session.scalar(stmt)

    def register_version(
        self,
        document: DocumentORM,
        sha256: str,
        storage_path: str,
        content_length: int,
    ) -> tuple[DocumentVersionORM, bool]:
        """Register a document version.

        Returns:
            (version_orm, is_new_version)
            If existing version with same SHA-256 is found, updates last_seen_at
            and returns (existing, False). If new SHA-256, demotes prior version
            and returns (new_ver, True).
        """
        existing = self.get_document_version(document.id, sha256)
        now = datetime.now(UTC)

        if existing:
            existing.last_seen_at = now
            document.sha256 = sha256
            document.storage_path = storage_path
            document.content_length = content_length
            document.retrieved_at = now
            logger.debug(
                "Document %s (SHA-256: %s) unchanged. Updated last_seen_at.",
                document.id,
                sha256[:12],
            )
            return existing, False

        # Demote previous current versions
        self.session.execute(
            update(DocumentVersionORM)
            .where(
                DocumentVersionORM.document_id == document.id,
                DocumentVersionORM.is_current.is_(True),
            )
            .values(is_current=False)
        )

        new_version = DocumentVersionORM(
            document_id=document.id,
            sha256=sha256,
            storage_path=storage_path,
            content_length=content_length,
            first_seen_at=now,
            last_seen_at=now,
            is_current=True,
        )
        self.session.add(new_version)

        # Update parent document pointers
        document.sha256 = sha256
        document.storage_path = storage_path
        document.content_length = content_length
        document.retrieved_at = now

        self.session.flush()
        logger.info(
            "Registered new version for Document %s (SHA-256: %s)",
            document.id,
            sha256[:12],
        )
        return new_version, True
