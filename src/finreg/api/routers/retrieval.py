"""Retrieval operations router (Hybrid RRF Search & Neural Cross-Encoder Reranking)."""

import logging
import time
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request, status

from finreg.api.schemas import (
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResultItem,
    RerankRequest,
    RerankResponse,
    RerankResultItem,
)
from finreg.hybrid.service import HybridRetrievalService
from finreg.reranking.service import RerankingService

logger = logging.getLogger("finreg.api.routers.retrieval")

router = APIRouter(prefix="/api/v1/retrieval", tags=["Legal Retrieval"])


def get_hybrid_service(request: Request) -> HybridRetrievalService:
    """Retrieve HybridRetrievalService instance from app state or default."""
    service = getattr(request.app.state, "hybrid_service", None)
    if service is not None:
        return cast(HybridRetrievalService, service)
    return HybridRetrievalService()


def get_reranking_service(request: Request) -> RerankingService:
    """Retrieve RerankingService instance from app state or default."""
    service = getattr(request.app.state, "reranking_service", None)
    if service is not None:
        return cast(RerankingService, service)
    return RerankingService()


@router.post(
    "/search",
    response_model=HybridSearchResponse,
    summary="Phase 4C RRF Hybrid Legal Retrieval Only",
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Retrieval Error"}},
)
def hybrid_search(payload: HybridSearchRequest, request: Request) -> HybridSearchResponse:
    """Execute Phase 4C RRF Hybrid Retrieval (Dense Vector + BM25 Lexical).

    This endpoint represents Phase 4C Reciprocal Rank Fusion ONLY.
    """
    start_t = time.perf_counter()
    service = get_hybrid_service(request)

    try:
        results, _ = service.search(
            query=payload.query,
            top_k=payload.top_k,
            rrf_k=payload.rrf_k,
            dense_top_k=payload.dense_top_k,
            lexical_top_k=payload.lexical_top_k,
            source_filter=payload.source_filter,
            regulation_type_filter=payload.regulation_type_filter,
            regulation_number_filter=payload.regulation_number_filter,
            document_id_filter=payload.document_id_filter,
        )
    except Exception as exc:
        logger.error("Hybrid search failed for query '%s': %s", payload.query, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hybrid search operation failed",
        ) from exc

    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
    items = [
        HybridSearchResultItem(
            fused_score=res.fused_score,
            dense_rank=res.dense_rank,
            lexical_rank=res.lexical_rank,
            dense_score=res.dense_score,
            lexical_score=res.lexical_score,
            retrieval_method=res.retrieval_method,
            chunk_id=res.chunk_id,
            source_node_id=res.source_node_id,
            document_id=res.document_id,
            document_version_id=res.document_version_id,
            source=res.source,
            regulation_type=res.regulation_type,
            regulation_number=res.regulation_number,
            title=res.title,
            structural_path=res.structural_path,
            chunk_text=res.chunk_text,
            contextual_text=res.contextual_text,
            page_start=res.page_start,
            page_end=res.page_end,
            sequence=res.sequence,
        )
        for res in results
    ]

    return HybridSearchResponse(
        query=payload.query,
        results=items,
        total_results=len(items),
        execution_time_ms=elapsed_ms,
    )


@router.post(
    "/rerank",
    response_model=RerankResponse,
    summary="Phase 4C Hybrid -> Phase 5 Neural Cross-Encoder Reranking",
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Reranking Error"}},
)
def rerank_search(payload: RerankRequest, request: Request) -> RerankResponse:
    """Execute Phase 4C Hybrid RRF -> Phase 5 Neural Cross-Encoder Reranking.

    First retrieves candidates via Phase 4C Hybrid RRF, then scores them via Cross-Encoder.
    """
    start_t = time.perf_counter()
    service = get_reranking_service(request)

    try:
        results, report = service.search(
            query=payload.query,
            top_n=payload.top_n,
            hybrid_top_k=payload.hybrid_top_k,
            source_filter=payload.source_filter,
            regulation_type_filter=payload.regulation_type_filter,
            regulation_number_filter=payload.regulation_number_filter,
            document_id_filter=payload.document_id_filter,
        )
    except Exception as exc:
        logger.error("Neural reranking failed for query '%s': %s", payload.query, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Neural reranking operation failed",
        ) from exc

    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
    model_name = report.model_name if report else "CrossEncoder"

    items = [
        RerankResultItem(
            rerank_score=res.rerank_score,
            rerank_rank=res.rerank_rank,
            fused_score=res.fused_score,
            dense_rank=res.dense_rank,
            lexical_rank=res.lexical_rank,
            dense_score=res.dense_score,
            lexical_score=res.lexical_score,
            retrieval_method=res.retrieval_method,
            chunk_id=res.chunk_id,
            source_node_id=res.source_node_id,
            document_id=res.document_id,
            document_version_id=res.document_version_id,
            source=res.source,
            regulation_type=res.regulation_type,
            regulation_number=res.regulation_number,
            title=res.title,
            structural_path=res.structural_path,
            chunk_text=res.chunk_text,
            contextual_text=res.contextual_text,
            page_start=res.page_start,
            page_end=res.page_end,
            sequence=res.sequence,
        )
        for res in results
    ]

    return RerankResponse(
        query=payload.query,
        results=items,
        total_results=len(items),
        model_name=model_name,
        execution_time_ms=elapsed_ms,
    )
