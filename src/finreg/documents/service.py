"""Document parsing service orchestrator for Phase 3A PDF structure parsing."""

import logging
from typing import Any
from uuid import UUID

from finreg.database.connection import get_session_factory
from finreg.database.repository import IngestionRepository
from finreg.documents.extractor import PdfExtractor
from finreg.documents.models import (
    NoCurrentDocumentVersionError,
    StructuredNode,
    ValidationReport,
)
from finreg.documents.normalizer import TextNormalizer
from finreg.documents.parser import RegulatoryStructureParser
from finreg.documents.validator import StructureValidator

logger = logging.getLogger(__name__)


class DocumentParsingService:
    """Orchestrator for extracting, normalizing, parsing, validating, and persisting node trees."""

    def __init__(
        self,
        extractor: PdfExtractor | None = None,
        normalizer: TextNormalizer | None = None,
        parser: RegulatoryStructureParser | None = None,
        validator: StructureValidator | None = None,
        session_factory: Any | None = None,
    ):
        self.extractor = extractor or PdfExtractor()
        self.normalizer = normalizer or TextNormalizer()
        self.parser = parser or RegulatoryStructureParser()
        self.validator = validator or StructureValidator()
        self.session_factory = session_factory or get_session_factory()

    def parse_document(
        self, document_id: UUID, dry_run: bool = False
    ) -> tuple[ValidationReport, list[StructuredNode]]:
        """Parse raw PDF document into structured node hierarchy and persist to database.

        Args:
            document_id: Regulation document UUID.
            dry_run: If True, executes parsing and validation without writing to DB.

        Returns:
            (ValidationReport, top_level_nodes)

        Raises:
            NoCurrentDocumentVersionError: If document has no active current version.
            ParsingValidationError: If coverage ratio is below threshold and dry_run=False.
        """
        logger.info(
            "Starting structure parsing for Document %s (Dry-Run: %s)",
            document_id,
            dry_run,
        )

        session = self.session_factory()
        repo = IngestionRepository(session)

        try:
            version = repo.get_current_document_version(document_id)
            if not version or not version.is_current:
                raise NoCurrentDocumentVersionError(
                    f"No active current document version found for Document {document_id}"
                )

            # 1. Extraction
            blocks, total_pages = self.extractor.extract_blocks_from_file(version.storage_path)

            # 2. Normalization
            lines = self.normalizer.normalize_blocks(blocks, total_pages)

            # 3. Structure Parsing
            nodes = self.parser.parse(lines)

            # 4. Validation
            report = self.validator.validate(
                document_id=document_id,
                version_id=version.id,
                lines=lines,
                nodes=nodes,
                total_pages=total_pages,
                raise_on_failure=not dry_run,
            )

            # 5. Persistence (if valid and not dry_run)
            if not dry_run and report.is_valid:
                created_nodes = repo.replace_document_nodes(
                    document_id=document_id,
                    document_version_id=version.id,
                    nodes=nodes,
                )
                session.commit()
                logger.info(
                    "Successfully committed %d document nodes for Document %s",
                    len(created_nodes),
                    document_id,
                )

            return report, nodes

        except Exception as exc:
            session.rollback()
            logger.error("Failed to parse document %s: %s", document_id, exc)
            raise

        finally:
            session.close()
