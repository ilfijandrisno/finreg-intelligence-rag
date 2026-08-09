"""Orchestrator service for Phase 5 Neural Cross-Encoder Reranking and Context Assembly."""

import logging
import time
from uuid import UUID

from finreg.hybrid.service import HybridRetrievalService
from finreg.reranking.providers import CrossEncoderRerankerProvider, Reranker
from finreg.reranking.rerank_models import RerankedSearchResult, RerankExecutionReport

logger = logging.getLogger(__name__)


class RerankingService:
    """Service orchestrating Phase 4C Hybrid Retrieval candidates and Phase 5 Reranking."""

    def __init__(
        self,
        reranker: Reranker | None = None,
        hybrid_service: HybridRetrievalService | None = None,
    ):
        self.reranker = reranker or CrossEncoderRerankerProvider()
        self.hybrid_service = hybrid_service or HybridRetrievalService()

    def search(
        self,
        query: str,
        top_n: int = 5,
        hybrid_top_k: int = 20,
        rrf_k: int = 60,
        dense_top_k: int = 20,
        lexical_top_k: int = 20,
        source_filter: str | None = None,
        regulation_type_filter: str | None = None,
        regulation_number_filter: str | None = None,
        document_id_filter: UUID | None = None,
    ) -> tuple[list[RerankedSearchResult], RerankExecutionReport]:
        """Fetch candidates from Phase 4C Hybrid Retrieval, rescore, and return top_n results."""
        if not query or not query.strip() or top_n <= 0:
            empty_report = RerankExecutionReport(
                model_name=self.reranker.model_name,
                candidates_in_count=0,
                reranked_out_count=0,
                execution_time_ms=0.0,
            )
            return [], empty_report

        start_time = time.perf_counter()

        # 1. Fetch candidate pool from Phase 4C Hybrid Retrieval up to hybrid_top_k limit
        candidates, _ = self.hybrid_service.search(
            query=query.strip(),
            top_k=hybrid_top_k,
            rrf_k=rrf_k,
            dense_top_k=dense_top_k,
            lexical_top_k=lexical_top_k,
            source_filter=source_filter,
            regulation_type_filter=regulation_type_filter,
            regulation_number_filter=regulation_number_filter,
            document_id_filter=document_id_filter,
        )

        if not candidates:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            empty_report = RerankExecutionReport(
                model_name=self.reranker.model_name,
                candidates_in_count=0,
                reranked_out_count=0,
                execution_time_ms=round(elapsed_ms, 2),
            )
            return [], empty_report

        # 2. Execute reranking over candidate pairs
        reranked_results = self.reranker.rerank(
            query=query.strip(),
            candidates=candidates,
            top_n=top_n,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        report = RerankExecutionReport(
            model_name=self.reranker.model_name,
            candidates_in_count=len(candidates),
            reranked_out_count=len(reranked_results),
            execution_time_ms=round(elapsed_ms, 2),
        )

        return reranked_results, report
