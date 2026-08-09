"""Pluggable lexical retriever protocol and pure-Python BM25 implementation."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from finreg.database.models import RetrievalChunkORM
from finreg.lexical.bm25 import BM25Engine, tokenize
from finreg.lexical.lexical_models import LexicalIndexReport, LexicalSearchResult

logger = logging.getLogger(__name__)


class LexicalRetriever(ABC):
    """Abstract protocol for lexical keyword search retrievers."""

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
        regulation_type_filter: str | None = None,
        regulation_number_filter: str | None = None,
        document_id_filter: UUID | None = None,
    ) -> list[LexicalSearchResult]:
        """Execute lexical keyword search with metadata filtering and deterministic ranking."""
        pass

    @abstractmethod
    def get_index_report(self) -> LexicalIndexReport:
        """Return diagnostic index statistics report."""
        pass


class BM25LexicalRetriever(LexicalRetriever):
    """BM25 retriever indexing retrieval_chunks.chunk_text and applying post-scoring filters."""

    def __init__(self, chunks: Sequence[RetrievalChunkORM]):
        self.chunks = list(chunks)
        # BM25 engine is constructed over chunk_text of the full loaded corpus
        corpus_texts = [c.chunk_text for c in self.chunks]
        self.engine = BM25Engine(corpus_texts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
        regulation_type_filter: str | None = None,
        regulation_number_filter: str | None = None,
        document_id_filter: UUID | None = None,
    ) -> list[LexicalSearchResult]:
        """Search query against BM25 index, apply metadata filters, and return top_k results."""
        if not query or not query.strip() or top_k <= 0 or not self.chunks:
            return []

        clean_query = query.strip()
        query_tokens = set(tokenize(clean_query))

        # 1. Calculate scores against the full BM25 corpus index
        raw_scores = self.engine.get_scores(clean_query)

        # 2. Package candidate results with metadata
        candidates: list[tuple[float, RetrievalChunkORM, int]] = []
        for idx, chunk in enumerate(self.chunks):
            score = raw_scores[idx]
            if score <= 0.0:
                continue

            # Calculate count of distinct query terms matched in chunk_text
            chunk_tokens = set(self.engine.doc_tokens[idx])
            matched_count = len(query_tokens.intersection(chunk_tokens))
            if matched_count == 0:
                continue

            # 3. Apply metadata filters after scoring and before top-k selection
            if source_filter and chunk.source.lower() != source_filter.lower():
                continue
            if (
                regulation_type_filter
                and chunk.regulation_type.lower() != regulation_type_filter.lower()
            ):
                continue
            if (
                regulation_number_filter
                and chunk.regulation_number.lower() != regulation_number_filter.lower()
            ):
                continue
            if document_id_filter and chunk.document_id != document_id_filter:
                continue

            candidates.append((score, chunk, matched_count))

        if not candidates:
            return []

        # 4. Enforce deterministic multi-key tie-breaking sort:
        #    Primary: score DESC
        #    Secondary: structural_path ASC
        #    Tertiary: sequence ASC
        #    Quaternary: str(chunk_id) ASC
        candidates.sort(
            key=lambda x: (
                -x[0],
                x[1].structural_path,
                x[1].sequence,
                str(x[1].id),
            )
        )

        top_candidates = candidates[:top_k]

        results: list[LexicalSearchResult] = []
        for score, chunk, matched_count in top_candidates:
            res = LexicalSearchResult(
                score=round(score, 4),
                matched_terms_count=matched_count,
                chunk_id=chunk.id,
                source_node_id=chunk.source_node_id,
                document_id=chunk.document_id,
                document_version_id=chunk.document_version_id,
                source=chunk.source,
                regulation_type=chunk.regulation_type,
                regulation_number=chunk.regulation_number,
                title=chunk.title,
                chapter_title=chunk.chapter_title,
                part_title=chunk.part_title,
                section_title=chunk.section_title,
                article_number=chunk.article_number,
                paragraph_number=chunk.paragraph_number,
                letter_code=chunk.letter_code,
                numbered_item=chunk.numbered_item,
                part_index=chunk.part_index if chunk.part_index is not None else 1,
                total_parts=chunk.total_parts if chunk.total_parts is not None else 1,
                structural_path=chunk.structural_path,
                chunk_text=chunk.chunk_text,
                contextual_text=chunk.contextual_text,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                sequence=chunk.sequence,
            )
            results.append(res)

        return results

    def get_index_report(self) -> LexicalIndexReport:
        """Return diagnostic index summary stats."""
        return LexicalIndexReport(
            total_chunks=len(self.chunks),
            vocabulary_size=self.engine.vocabulary_size,
            average_doc_length=round(self.engine.avg_doc_length, 2),
        )
