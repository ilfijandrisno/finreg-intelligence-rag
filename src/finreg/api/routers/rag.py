"""Grounded LLM Generation RAG API router."""

import logging
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request, status

from finreg.api.schemas import (
    LegalCitationResponse,
    RAGExecutionReportResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from finreg.rag.service import RAGService

logger = logging.getLogger("finreg.api.routers.rag")

router = APIRouter(prefix="/api/v1/rag", tags=["Grounded RAG Generation"])


def get_rag_service(request: Request) -> RAGService:
    """Retrieve RAGService instance from app state or default."""
    service = getattr(request.app.state, "rag_service", None)
    if service is not None:
        return cast(RAGService, service)
    return RAGService()


@router.post(
    "/generate",
    response_model=RAGQueryResponse,
    summary="Generate Grounded Legal Answer",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation Error"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Processing Error"},
    },
)
def generate_rag_answer(payload: RAGQueryRequest, request: Request) -> RAGQueryResponse:
    """Execute end-to-end grounded RAG generation pipeline.

    Passes user query through Phase 4C Hybrid Retrieval, Phase 5 Neural Cross-Encoder Reranking,
    Context Assembly, XML Boundary Isolation, LLM Generation, and Strict Citation Validation.
    """
    rag_service = get_rag_service(request)
    try:
        gen_result = rag_service.search_and_generate(
            query=payload.query,
            top_n=payload.top_n,
            source_filter=payload.source_filter,
            regulation_type_filter=payload.regulation_type_filter,
            regulation_number_filter=payload.regulation_number_filter,
            document_id_filter=payload.document_id_filter,
        )
    except Exception as exc:
        logger.error("RAG generation processing failed for query '%s': %s", payload.query, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate grounded legal answer",
        ) from exc

    # Map domain LegalCitation list to API LegalCitationResponse list
    citations_api = [
        LegalCitationResponse(
            context_id=cit.context_id,
            chunk_id=cit.chunk_id,
            source=cit.source,
            regulation_type=cit.regulation_type,
            regulation_number=cit.regulation_number,
            structural_path=cit.structural_path,
            page_start=cit.page_start,
            page_end=cit.page_end,
            display_citation=cit.format_display_string(),
        )
        for cit in gen_result.citations
    ]

    report = gen_result.execution_report
    report_api = RAGExecutionReportResponse(
        provider_name=report.provider_name,
        model_name=report.model_name,
        context_blocks_count=report.context_blocks_count,
        estimated_input_tokens=report.estimated_input_tokens,
        output_tokens=report.output_tokens,
        execution_time_ms=report.execution_time_ms,
        abstained=report.abstained,
    )

    return RAGQueryResponse(
        query=gen_result.query,
        answer=gen_result.answer,
        citations=citations_api,
        abstained=gen_result.abstained,
        abstention_reason=gen_result.abstention_reason,
        has_legal_conflict=gen_result.has_legal_conflict,
        execution_report=report_api,
    )
