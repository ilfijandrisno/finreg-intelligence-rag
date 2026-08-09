"""Semantic legal chunker generating retrieval-ready chunks with full provenance and context."""

import hashlib
import re
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from finreg.documents.chunk_models import SemanticChunk
from finreg.documents.models import NodeType

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


class SemanticLegalChunker:
    """Legal hierarchy-aware semantic chunker."""

    def __init__(self, chunk_max_size: int = 1500, chunk_target_size: int = 500):
        self.chunk_max_size = chunk_max_size
        self.chunk_target_size = chunk_target_size

    def chunk_document_tree(
        self,
        document_id: UUID,
        version_id: UUID,
        source: str,
        regulation_type: str,
        regulation_number: str,
        title: str,
        nodes: Sequence[Any],
    ) -> list[SemanticChunk]:
        """Traverse legal node tree and generate deterministic SemanticChunk instances."""
        chunks: list[SemanticChunk] = []
        sequence_counter = 0

        # Filter top-level root nodes if passed a flat list of ORM objects
        root_nodes: list[Any] = (
            [n for n in nodes if getattr(n, "parent_id", None) is None] if nodes else []
        )
        if not root_nodes and nodes:
            root_nodes = list(nodes)

        def _traverse(
            node_list: Sequence[Any],
            chapter_title: str | None = None,
            part_title: str | None = None,
            section_title: str | None = None,
            article_number: str | None = None,
            paragraph_number: str | None = None,
            letter_code: str | None = None,
            numbered_item: str | None = None,
        ) -> None:
            nonlocal sequence_counter

            for node in node_list:
                node_type_val = (
                    node.node_type
                    if isinstance(node.node_type, NodeType)
                    else NodeType(node.node_type)
                )

                # Update context variables for container nodes
                cur_chap = node.title if node_type_val == NodeType.CHAPTER else chapter_title
                cur_part = node.title if node_type_val == NodeType.PART else part_title
                cur_sec = node.title if node_type_val == NodeType.SECTION else section_title
                cur_art = node.node_number if node_type_val == NodeType.ARTICLE else article_number
                cur_para = (
                    node.node_number if node_type_val == NodeType.PARAGRAPH else paragraph_number
                )
                cur_letter = node.node_number if node_type_val == NodeType.LETTER else letter_code
                cur_num = (
                    node.node_number if node_type_val == NodeType.NUMBERED_ITEM else numbered_item
                )

                # Process leaf content node text
                if node_type_val in LEAF_NODE_TYPES and node.text and node.text.strip():
                    text = node.text.strip()
                    parts = self._split_text_hierarchically(text)
                    total_parts = len(parts)

                    for part_idx, part_text in enumerate(parts, start=1):
                        sequence_counter += 1
                        path = node.path
                        if total_parts > 1:
                            path = f"{node.path} [Part {part_idx}/{total_parts}]"

                        contextual_text = self._build_contextual_text(
                            source=source,
                            regulation_type=regulation_type,
                            regulation_number=regulation_number,
                            title=title,
                            path=path,
                            page_start=node.page_start,
                            page_end=node.page_end,
                            chunk_text=part_text,
                        )

                        chunk_hash = self._compute_canonical_hash(
                            version_id=version_id,
                            source_node_id=node.id,
                            structural_path=path,
                            part_index=part_idx,
                            chunk_text=part_text,
                        )

                        words = len(part_text.split())

                        chunk = SemanticChunk(
                            document_id=document_id,
                            document_version_id=version_id,
                            source_node_id=node.id,
                            chunk_hash=chunk_hash,
                            source=source,
                            regulation_type=regulation_type,
                            regulation_number=regulation_number,
                            title=title,
                            chapter_title=cur_chap,
                            part_title=cur_part,
                            section_title=cur_sec,
                            article_number=cur_art,
                            paragraph_number=cur_para,
                            letter_code=cur_letter,
                            numbered_item=cur_num,
                            part_index=part_idx,
                            total_parts=total_parts,
                            structural_path=path,
                            chunk_text=part_text,
                            contextual_text=contextual_text,
                            character_count=len(part_text),
                            word_count=words,
                            page_start=node.page_start,
                            page_end=node.page_end,
                            sequence=sequence_counter,
                        )
                        chunks.append(chunk)

                # Recurse children
                if hasattr(node, "children") and node.children:
                    _traverse(
                        node.children,
                        chapter_title=cur_chap,
                        part_title=cur_part,
                        section_title=cur_sec,
                        article_number=cur_art,
                        paragraph_number=cur_para,
                        letter_code=cur_letter,
                        numbered_item=cur_num,
                    )

        _traverse(root_nodes)
        return chunks

    def _split_text_hierarchically(self, text: str) -> list[str]:
        """Split oversized text deterministically via sentence boundary or clause fallback."""
        if len(text) <= self.chunk_max_size:
            return [text]

        parts: list[str] = []
        remaining = text

        while len(remaining) > self.chunk_max_size:
            target_slice = remaining[: self.chunk_max_size]
            split_pos = -1
            # Find candidate boundary pos in target_slice
            for pattern in [r"\.\s+", r";\s+", r"\.\n", r"\n\n", r"\n", r",\s+", r"\s+"]:
                matches = [m.end() for m in re.finditer(pattern, target_slice)]
                if matches:
                    split_pos = matches[-1]
                    break

            if split_pos <= 0:
                split_pos = self.chunk_max_size

            parts.append(remaining[:split_pos])
            remaining = remaining[split_pos:]

        if remaining:
            parts.append(remaining)

        return [p for p in parts if p]

    def _build_contextual_text(
        self,
        source: str,
        regulation_type: str,
        regulation_number: str,
        title: str,
        path: str,
        page_start: int,
        page_end: int,
        chunk_text: str,
    ) -> str:
        header = (
            f"[{source} - {regulation_type} No. {regulation_number}] {title}\n"
            f"Hierarki: {path}\nHalaman: {page_start} - {page_end}\n\n{chunk_text}"
        )
        return header

    def _compute_canonical_hash(
        self,
        version_id: UUID,
        source_node_id: UUID,
        structural_path: str,
        part_index: int,
        chunk_text: str,
    ) -> str:
        """Calculate canonical SHA-256 identity hash for chunk idempotency."""
        payload = f"{version_id}:{source_node_id}:{structural_path}:{part_index}:{chunk_text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
