"""Orchestrator service for Phase 4C hybrid retrieval combining dense and lexical search."""

import logging
from uuid import UUID

from finreg.hybrid.hybrid_models import HybridExecutionReport, HybridSearchResult
from finreg.hybrid.providers import HybridRetriever, RRFHybridRetriever

logger = logging.getLogger(__name__)


class HybridRetrievalService:
    """Service orchestrating dense vector and BM25 lexical search with RRF."""

    def __init__(self, retriever: HybridRetriever | None = None):
        self.retriever = retriever or RRFHybridRetriever()

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
    ) -> tuple[list[HybridSearchResult], HybridExecutionReport]:
        """Execute hybrid search combining dense and BM25 retrieval branches."""
        if not query or not query.strip() or top_k <= 0:
            empty_report = HybridExecutionReport(
                dense_candidates_count=0,
                lexical_candidates_count=0,
                fused_results_count=0,
                rrf_k=rrf_k,
            )
            return [], empty_report

        results = self.retriever.search(
            query=query.strip(),
            top_k=top_k,
            rrf_k=rrf_k,
            dense_top_k=dense_top_k,
            lexical_top_k=lexical_top_k,
            source_filter=source_filter,
            regulation_type_filter=regulation_type_filter,
            regulation_number_filter=regulation_number_filter,
            document_id_filter=document_id_filter,
        )

        # Build diagnostic execution report
        dense_count = sum(1 for r in results if r.dense_rank is not None)
        lexical_count = sum(1 for r in results if r.lexical_rank is not None)

        report = HybridExecutionReport(
            dense_candidates_count=dense_count,
            lexical_candidates_count=lexical_count,
            fused_results_count=len(results),
            rrf_k=rrf_k,
        )

        return results, report
