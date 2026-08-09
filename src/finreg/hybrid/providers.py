"""Pluggable hybrid retriever protocol and RRF-based hybrid retriever implementation."""

import logging
from abc import ABC, abstractmethod
from uuid import UUID

from finreg.hybrid.fusion import reciprocal_rank_fusion
from finreg.hybrid.hybrid_models import HybridSearchResult
from finreg.lexical.service import LexicalRetrievalService
from finreg.vector.search_service import VectorSearchService

logger = logging.getLogger(__name__)


class HybridRetriever(ABC):
    """Abstract protocol for hybrid dense + lexical retrieval implementations."""

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        rrf_k: int = 60,
        dense_top_k: int = 20,
        lexical_top_k: int = 20,
        source_filter: str | None = None,
        regulation_type_filter: str | None = None,
        regulation_number_filter: str | None = None,
        document_id_filter: UUID | None = None,
    ) -> list[HybridSearchResult]:
        """Execute hybrid search combining dense vector search and BM25 lexical retrieval."""
        pass


class RRFHybridRetriever(HybridRetriever):
    """HybridRetriever fusing Phase 4A dense vector search and Phase 4B BM25 search via RRF."""

    def __init__(
        self,
        dense_service: VectorSearchService | None = None,
        lexical_service: LexicalRetrievalService | None = None,
    ):
        self.dense_service = dense_service or VectorSearchService()
        self.lexical_service = lexical_service or LexicalRetrievalService()

    def search(
        self,
        query: str,
        top_k: int = 5,
        rrf_k: int = 60,
        dense_top_k: int = 20,
        lexical_top_k: int = 20,
        source_filter: str | None = None,
        regulation_type_filter: str | None = None,
        regulation_number_filter: str | None = None,
        document_id_filter: UUID | None = None,
    ) -> list[HybridSearchResult]:
        """Execute independent dense and BM25 branch queries and fuse with RRF."""
        if not query or not query.strip() or top_k <= 0:
            return []

        # 1. Query Dense Vector branch up to dense_top_k candidate limit
        dense_candidates = self.dense_service.search(
            query=query.strip(),
            top_k=dense_top_k,
            source_filter=source_filter,
            regulation_type_filter=regulation_type_filter,
            document_id_filter=document_id_filter,
        )

        # 2. Query BM25 Lexical branch up to lexical_top_k candidate limit
        lexical_candidates, _ = self.lexical_service.search(
            query=query.strip(),
            top_k=lexical_top_k,
            source_filter=source_filter,
            regulation_type_filter=regulation_type_filter,
            regulation_number_filter=regulation_number_filter,
            document_id_filter=document_id_filter,
        )

        # 3. Fuse candidates using Reciprocal Rank Fusion and slice to top_k
        fused_results = reciprocal_rank_fusion(
            dense_results=dense_candidates,
            lexical_results=lexical_candidates,
            rrf_k=rrf_k,
            top_k=top_k,
        )

        return fused_results
