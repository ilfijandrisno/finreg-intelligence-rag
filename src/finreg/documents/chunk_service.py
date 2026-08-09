"""Orchestrator service for semantic legal chunking and persistence (Phase 3B)."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from finreg.database.connection import get_engine, get_session_factory
from finreg.database.repository import IngestionRepository
from finreg.documents.chunk_models import (
    ChunkValidationReport,
    SemanticChunk,
)
from finreg.documents.chunk_validator import ChunkValidator
from finreg.documents.chunker import SemanticLegalChunker
from finreg.documents.models import NoCurrentDocumentVersionError
from finreg.documents.service import DocumentParsingService

logger = logging.getLogger(__name__)


class DocumentChunkingService:
    """Service managing legal document chunking, validation, and database replacement."""

    def __init__(
        self,
        chunker: SemanticLegalChunker | None = None,
        validator: ChunkValidator | None = None,
    ):
        self.chunker = chunker or SemanticLegalChunker()
        self.validator = validator or ChunkValidator()

    def chunk_document(
        self,
        document_id: UUID,
        dry_run: bool = False,
        session: Session | None = None,
    ) -> tuple[ChunkValidationReport, list[SemanticChunk]]:
        """Chunk a document version, validate quality, and optionally persist retrieval_chunks."""
        own_session = False
        if session is None:
            engine = get_engine()
            session_factory = get_session_factory(engine)
            session = session_factory()
            own_session = True

        try:
            repo = IngestionRepository(session)
            version = repo.get_current_document_version(document_id)
            if not version:
                raise NoCurrentDocumentVersionError(
                    f"No active document_version with is_current=True for Document {document_id}"
                )

            db_nodes = repo.get_document_nodes(document_id)
            nodes: list[Any] = list(db_nodes)
            if not nodes:
                # Parse on the fly via DocumentParsingService if nodes not in DB
                parsing_service = DocumentParsingService()
                _, parsed_nodes = parsing_service.parse_document(
                    document_id=document_id, dry_run=True
                )
                nodes = list(parsed_nodes)

            regulation = version.document.regulation
            source = regulation.source
            reg_type = regulation.regulation_type
            reg_num = regulation.regulation_number
            reg_title = regulation.title

            chunks = self.chunker.chunk_document_tree(
                document_id=document_id,
                version_id=version.id,
                source=source,
                regulation_type=reg_type,
                regulation_number=reg_num,
                title=reg_title,
                nodes=nodes,
            )

            report = self.validator.validate(
                document_id=document_id,
                version_id=version.id,
                nodes=nodes,
                chunks=chunks,
                raise_on_failure=not dry_run,
            )

            if not dry_run and report.is_valid:
                created_chunks = repo.replace_retrieval_chunks(
                    document_id=document_id,
                    document_version_id=version.id,
                    chunks=chunks,
                )
                session.commit()
                logger.info(
                    "Successfully committed %d retrieval chunks for Document %s",
                    len(created_chunks),
                    document_id,
                )

            return report, chunks

        except Exception as exc:
            session.rollback()
            logger.error("Failed to chunk document %s: %s", document_id, exc)
            raise

        finally:
            if own_session:
                session.close()
