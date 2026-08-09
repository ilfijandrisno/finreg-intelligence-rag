"""Validation engine assessing chunk coverage, integrity, and non-null provenance."""

import logging
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from finreg.documents.chunk_models import (
    ChunkingValidationError,
    ChunkValidationReport,
    SemanticChunk,
)
from finreg.documents.models import NodeType

logger = logging.getLogger(__name__)

LEAF_NODE_TYPES = {
    NodeType.PREAMBLE,
    NodeType.CONSIDERATION,
    NodeType.LEGAL_BASIS,
    NodeType.DECISION,
    NodeType.PARAGRAPH,
    NodeType.LETTER,
    NodeType.NUMBERED_ITEM,
    NodeType.CLOSING,
}


class ChunkValidator:
    """Validator evaluating chunk set quality metrics against Phase 3A leaf node tree."""

    def validate(
        self,
        document_id: UUID,
        version_id: UUID,
        nodes: Sequence[Any],
        chunks: list[SemanticChunk],
        raise_on_failure: bool = True,
    ) -> ChunkValidationReport:
        """Validate chunks for 100% leaf coverage, canonical hashes, and non-null source_node_id."""
        warnings: list[str] = []

        leaf_source_chars = self._calculate_leaf_source_characters(nodes)
        chunked_chars = sum(c.character_count for c in chunks)

        coverage = (
            round(chunked_chars / leaf_source_chars, 4)
            if leaf_source_chars > 0
            else (1.0 if chunked_chars == 0 else 0.0)
        )

        min_size = min((c.character_count for c in chunks), default=0)
        max_size = max((c.character_count for c in chunks), default=0)
        avg_size = round(chunked_chars / len(chunks), 2) if chunks else 0.0

        is_valid = True

        # Rule 1: 100% Leaf Text Coverage
        if leaf_source_chars > 0 and chunked_chars != leaf_source_chars:
            is_valid = False
            msg = (
                f"Leaf character coverage mismatch: chunked {chunked_chars} chars "
                f"vs leaf source {leaf_source_chars} chars (Ratio: {coverage})"
            )
            warnings.append(msg)
            logger.warning(msg)

        # Rule 2: No empty chunks
        empty_chunks = [c for c in chunks if not c.chunk_text or not c.chunk_text.strip()]
        if empty_chunks:
            is_valid = False
            msg = f"Found {len(empty_chunks)} empty chunks"
            warnings.append(msg)
            logger.warning(msg)

        # Rule 3: No duplicate chunk hashes
        hashes = [c.chunk_hash for c in chunks]
        if len(hashes) != len(set(hashes)):
            is_valid = False
            dup_count = len(hashes) - len(set(hashes))
            msg = f"Found {dup_count} duplicate chunk hashes"
            warnings.append(msg)
            logger.warning(msg)

        # Rule 4: Non-null source_node_id provenance
        null_provenance = [c for c in chunks if c.source_node_id is None]
        if null_provenance:
            is_valid = False
            msg = f"Found {len(null_provenance)} chunks with null source_node_id"
            warnings.append(msg)
            logger.warning(msg)

        # Rule 5: Sequence continuity 1..N
        sequences = [c.sequence for c in chunks]
        expected_sequences = list(range(1, len(chunks) + 1))
        if sequences != expected_sequences:
            is_valid = False
            msg = f"Chunk sequence discontinuity: expected 1..{len(chunks)}, got {sequences[:5]}..."
            warnings.append(msg)
            logger.warning(msg)

        report = ChunkValidationReport(
            document_id=document_id,
            version_id=version_id,
            total_chunks=len(chunks),
            leaf_source_characters=leaf_source_chars,
            chunked_characters=chunked_chars,
            source_text_coverage=coverage,
            min_chunk_size=min_size,
            max_chunk_size=max_size,
            avg_chunk_size=avg_size,
            is_valid=is_valid,
            warnings=warnings,
        )

        if not is_valid and raise_on_failure:
            raise ChunkingValidationError(
                f"Chunk validation failed for Document {document_id}: {'; '.join(warnings)}",
                report=report,
            )

        return report

    def _calculate_leaf_source_characters(self, nodes: Sequence[Any]) -> int:
        """Calculate total character count across all Phase 3A leaf content nodes."""
        total = 0
        root_nodes: list[Any] = (
            [n for n in nodes if getattr(n, "parent_id", None) is None] if nodes else []
        )
        if not root_nodes and nodes:
            root_nodes = list(nodes)

        def _traverse(node_list: Sequence[Any]) -> None:
            nonlocal total
            for node in node_list:
                node_type_val = (
                    node.node_type
                    if isinstance(node.node_type, NodeType)
                    else NodeType(node.node_type)
                )
                if node_type_val in LEAF_NODE_TYPES and node.text and node.text.strip():
                    total += len(node.text.strip())
                if hasattr(node, "children") and node.children:
                    _traverse(node.children)

        _traverse(root_nodes)
        return total
