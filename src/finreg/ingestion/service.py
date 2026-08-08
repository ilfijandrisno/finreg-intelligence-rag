"""Ingestion orchestrator service coordinating adapters, downloader, storage, and DB persistence."""

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from finreg.database.connection import get_session_factory
from finreg.database.repository import IngestionRepository
from finreg.ingestion.downloader import DownloadManager
from finreg.ingestion.models import (
    DocumentType,
    IngestionSummary,
)
from finreg.ingestion.protocols import RegulatorySourceAdapter
from finreg.ingestion.storage import LocalStorageManager

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrator for discovering, downloading, validating, and persisting regulatory data."""

    def __init__(
        self,
        downloader: DownloadManager | None = None,
        storage_manager: LocalStorageManager | None = None,
        session_factory: Any | None = None,
    ):
        self.downloader = downloader or DownloadManager()
        self.storage_manager = storage_manager or LocalStorageManager()
        self.session_factory = session_factory or get_session_factory()

    def run_ingestion(
        self,
        adapter: RegulatorySourceAdapter,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> IngestionSummary:
        """Run complete ingestion pipeline for a given regulatory source adapter.

        Args:
            adapter: RegulatorySourceAdapter instance (BI or OJK).
            limit: Maximum regulations limit to discover.
            dry_run: If True, executes discovery and URL resolution without file/DB mutations.

        Returns:
            IngestionSummary containing execution metrics.
        """
        start_time = time.time()
        source = adapter.source_name
        logger.info(
            "Starting ingestion for source '%s' (Limit: %s, Dry-Run: %s)",
            source,
            limit,
            dry_run,
        )

        summary = IngestionSummary(source=source)

        # 1. Discovery
        references = adapter.discover_regulations(limit=limit)
        summary.discovered = len(references)
        logger.info("Discovered %d regulations from %s", len(references), source)

        if dry_run:
            logger.info("[DRY-RUN] Simulating metadata and document resolution...")
            for ref in references:
                try:
                    metadata = adapter.fetch_metadata(ref)
                    summary.metadata_parsed += 1
                    doc_refs = adapter.resolve_documents(metadata)
                    summary.documents_found += len(doc_refs)
                    logger.info(
                        "[DRY-RUN] Discovered: %s %s - %d attachments resolved (%s)",
                        metadata.regulation_type,
                        metadata.regulation_number,
                        len(doc_refs),
                        ref.detail_url,
                    )
                except Exception as exc:
                    logger.error("[DRY-RUN] Error processing %s: %s", ref.detail_url, exc)
                    summary.failed += 1

            summary.duration_seconds = round(time.time() - start_time, 2)
            return summary

        # 2. Ingestion Execution with Database Transactions
        session: Session = self.session_factory()
        repo = IngestionRepository(session)

        try:
            for ref in references:
                try:
                    # Fetch & parse metadata
                    metadata = adapter.fetch_metadata(ref)
                    summary.metadata_parsed += 1

                    # Resolve attachment document references
                    doc_refs = adapter.resolve_documents(metadata)
                    summary.documents_found += len(doc_refs)

                    # Upsert regulation record in DB
                    reg_orm = repo.upsert_regulation(metadata)

                    # Save metadata JSON artifact
                    self.storage_manager.save_metadata_artifact(
                        metadata=metadata, regulation_id=reg_orm.id
                    )

                    # Process PDF attachments
                    for doc_ref in doc_refs:
                        # Process regulation PDFs for dataset core
                        if doc_ref.document_type != DocumentType.REGULATION and len(doc_refs) > 1:
                            # Register non-regulation attachments in doc_refs
                            pass

                        # Get or create DB Document record
                        doc_orm = repo.get_or_create_document(reg_orm.id, doc_ref)

                        # Download content bytes
                        download_res = self.downloader.download_file(doc_ref.url)

                        # Idempotency check: see if version with identical SHA-256 exists
                        existing_ver = repo.get_document_version(doc_orm.id, download_res.sha256)

                        if existing_ver:
                            # Unchanged file payload -> idempotent skip
                            repo.register_version(
                                document=doc_orm,
                                sha256=download_res.sha256,
                                storage_path=existing_ver.storage_path,
                                content_length=download_res.content_length,
                            )
                            summary.skipped += 1
                            logger.info(
                                "Idempotent skip: Document %s (SHA-256: %s) unchanged",
                                doc_orm.filename,
                                download_res.sha256[:12],
                            )
                        else:
                            # New file payload -> write to raw storage and register version
                            saved_path = self.storage_manager.save_raw_file(
                                content_bytes=download_res.content_bytes,
                                source=metadata.source,
                                regulation_type=metadata.regulation_type,
                                document_id=doc_orm.id,
                                sha256=download_res.sha256,
                                extension="pdf",
                            )

                            try:
                                repo.register_version(
                                    document=doc_orm,
                                    sha256=download_res.sha256,
                                    storage_path=saved_path,
                                    content_length=download_res.content_length,
                                )
                                summary.downloaded += 1
                                summary.new_versions += 1
                            except Exception as db_exc:
                                # Clean up transient raw file on DB transaction failure
                                self.storage_manager.delete_file_if_exists(saved_path)
                                raise db_exc

                    # Commit regulation transaction
                    session.commit()

                except Exception as exc:
                    session.rollback()
                    summary.failed += 1
                    logger.error(
                        "Error processing regulation reference %s (%s): %s",
                        ref.regulation_number,
                        ref.detail_url,
                        exc,
                        exc_info=True,
                    )

        finally:
            session.close()

        summary.duration_seconds = round(time.time() - start_time, 2)
        logger.info(
            "Ingestion completed for %s in %.2fs "
            "(Downloaded: %d, Skipped: %d, New Versions: %d, Failed: %d)",
            source,
            summary.duration_seconds,
            summary.downloaded,
            summary.skipped,
            summary.new_versions,
            summary.failed,
        )

        return summary
