"""Validation engine assessing character coverage ratio and structural node integrity."""

import logging
from uuid import UUID

from finreg.config.settings import get_settings
from finreg.documents.models import (
    NodeType,
    NormalizedLine,
    ParsingValidationError,
    StructuredNode,
    ValidationReport,
)

logger = logging.getLogger(__name__)

LEAF_CONTENT_NODE_TYPES = {
    NodeType.PREAMBLE,
    NodeType.CONSIDERATION,
    NodeType.LEGAL_BASIS,
    NodeType.DECISION,
    NodeType.PARAGRAPH,
    NodeType.LETTER,
    NodeType.NUMBERED_ITEM,
    NodeType.CLOSING,
}


class StructureValidator:
    """Validator computing character coverage ratio and enforcing acceptance thresholds."""

    def __init__(self, min_coverage_ratio: float | None = None):
        settings = get_settings()
        self.min_coverage_ratio = (
            min_coverage_ratio
            if min_coverage_ratio is not None
            else settings.parsing_min_coverage_ratio
        )

    def validate(
        self,
        document_id: UUID,
        version_id: UUID,
        lines: list[NormalizedLine],
        nodes: list[StructuredNode],
        total_pages: int,
        raise_on_failure: bool = True,
    ) -> ValidationReport:
        """Validate parsed structure, compute non-overlapping coverage ratio, and produce report.

        Args:
            document_id: Regulation document UUID.
            version_id: Active document version UUID.
            lines: Input normalized lines.
            nodes: Parsed top-level structured nodes tree.
            total_pages: PDF total page count.
            raise_on_failure: If True, raises ParsingValidationError when coverage < threshold.

        Returns:
            ValidationReport with coverage metrics.
        """
        extracted_characters = sum(len(line.text) for line in lines)
        structured_characters = self._calculate_leaf_structured_characters(nodes)

        unparsed_characters = max(0, extracted_characters - structured_characters)
        coverage_ratio = (
            round(structured_characters / extracted_characters, 4)
            if extracted_characters > 0
            else 1.0
        )
        coverage_ratio = min(1.0, coverage_ratio)

        is_valid = coverage_ratio >= self.min_coverage_ratio
        warnings: list[str] = []

        if coverage_ratio < self.min_coverage_ratio:
            msg = (
                f"Coverage ratio {coverage_ratio:.4f} is below minimum "
                f"threshold {self.min_coverage_ratio:.2f}"
            )
            warnings.append(msg)

        report = ValidationReport(
            document_id=document_id,
            version_id=version_id,
            total_pages=total_pages,
            extracted_characters=extracted_characters,
            structured_characters=structured_characters,
            unparsed_characters=unparsed_characters,
            coverage_ratio=coverage_ratio,
            is_valid=is_valid,
            warnings=warnings,
        )

        logger.info(
            "Parsing validation complete for Doc %s (Version: %s) — Coverage: %.2f%% (Valid: %s)",
            document_id,
            version_id,
            coverage_ratio * 100,
            is_valid,
        )

        if not is_valid and raise_on_failure:
            raise ParsingValidationError(
                f"Parsing validation failed for Document {document_id}: "
                f"Coverage ratio {coverage_ratio:.4f} < {self.min_coverage_ratio:.2f}"
            )

        return report

    def _calculate_leaf_structured_characters(self, nodes: list[StructuredNode]) -> int:
        """Sum text lengths from non-overlapping leaf content nodes to prevent double counting."""
        total = 0
        for node in nodes:
            if node.node_type in LEAF_CONTENT_NODE_TYPES and node.text:
                total += len(node.text)
            if node.children:
                total += self._calculate_leaf_structured_characters(node.children)
        return total
