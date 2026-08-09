"""Orchestrator service for Phase 6 Grounded LLM Generation and RAG Answer Assembly."""

import logging
import time
from uuid import UUID

from finreg.config.settings import get_settings
from finreg.rag.citation_validator import CitationValidator
from finreg.rag.context_assembler import ContextAssembler, estimate_token_count
from finreg.rag.prompt_builder import PromptBuilder
from finreg.rag.providers import LLMProvider, OpenAILLMProvider
from finreg.rag.rag_models import GenerationResult, RAGExecutionReport
from finreg.reranking.service import RerankingService

logger = logging.getLogger(__name__)

ABSTENTION_MESSAGE = (
    "The supplied financial regulation context does not contain sufficient legal evidence "
    "to answer the query."
)


class RAGService:
    """Service orchestrating Phase 5 Neural Reranking and Phase 6 Grounded LLM Generation."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        reranking_service: RerankingService | None = None,
        context_assembler: ContextAssembler | None = None,
        prompt_builder: PromptBuilder | None = None,
        citation_validator: CitationValidator | None = None,
    ):
        self.llm_provider = llm_provider or OpenAILLMProvider()
        self.reranking_service = reranking_service or RerankingService()
        self.context_assembler = context_assembler or ContextAssembler()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.citation_validator = citation_validator or CitationValidator()

    def search_and_generate(
        self,
        query: str,
        top_n: int = 5,
        hybrid_top_k: int = 20,
        source_filter: str | None = None,
        regulation_type_filter: str | None = None,
        regulation_number_filter: str | None = None,
        document_id_filter: UUID | None = None,
    ) -> GenerationResult:
        """Execute full RAG generation pipeline from retrieval to citation validation."""
        clean_query = query.strip() if query else ""
        settings = get_settings()

        if not clean_query:
            report = RAGExecutionReport(
                provider_name=self.llm_provider.provider_name,
                model_name=self.llm_provider.model_name,
                context_blocks_count=0,
                estimated_input_tokens=0,
                output_tokens=0,
                execution_time_ms=0.0,
                abstained=True,
            )
            return GenerationResult(
                query=query,
                answer="",
                citations=[],
                abstained=True,
                abstention_reason="Empty user query",
                execution_report=report,
            )

        start_time = time.perf_counter()

        # 1. Retrieve candidates from Phase 5 Neural Reranking Service
        reranked_results, _ = self.reranking_service.search(
            query=clean_query,
            top_n=top_n,
            hybrid_top_k=hybrid_top_k,
            source_filter=source_filter,
            regulation_type_filter=regulation_type_filter,
            regulation_number_filter=regulation_number_filter,
            document_id_filter=document_id_filter,
        )

        # 2. Early-Gate Quality Check (rag_min_rerank_threshold)
        # Note: Threshold pass is ONLY an early gate; it does NOT prove evidence is sufficient.
        if (
            not reranked_results
            or reranked_results[0].rerank_score < settings.rag_min_rerank_threshold
        ):
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            report = RAGExecutionReport(
                provider_name=self.llm_provider.provider_name,
                model_name=self.llm_provider.model_name,
                context_blocks_count=0,
                estimated_input_tokens=estimate_token_count(clean_query),
                output_tokens=0,
                execution_time_ms=round(elapsed_ms, 2),
                abstained=True,
            )
            return GenerationResult(
                query=clean_query,
                answer=ABSTENTION_MESSAGE,
                citations=[],
                abstained=True,
                abstention_reason="No retrieved context meets the early quality gate threshold",
                execution_report=report,
            )

        # 3. Assemble context blocks within token budget
        context_blocks = self.context_assembler.assemble(
            reranked_results=reranked_results,
            max_context_tokens=settings.rag_max_context_tokens,
        )

        # 4. Build system instructions and structured user prompt
        system_inst = self.prompt_builder.build_system_instructions()
        user_prompt = self.prompt_builder.build_user_prompt(clean_query, context_blocks)
        input_tokens = estimate_token_count(system_inst + user_prompt)

        # 5. Call LLM provider
        raw_response = self.llm_provider.generate(
            query=user_prompt,
            context_blocks=context_blocks,
            system_instructions=system_inst,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_output_tokens,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        response_text = raw_response.text.strip()

        # 6. Check for LLM abstention statement
        if ABSTENTION_MESSAGE.lower() in response_text.lower():
            report = RAGExecutionReport(
                provider_name=self.llm_provider.provider_name,
                model_name=self.llm_provider.model_name,
                context_blocks_count=len(context_blocks),
                estimated_input_tokens=input_tokens,
                output_tokens=raw_response.output_tokens,
                execution_time_ms=round(elapsed_ms, 2),
                abstained=True,
            )
            return GenerationResult(
                query=clean_query,
                answer=ABSTENTION_MESSAGE,
                citations=[],
                abstained=True,
                abstention_reason="LLM determined retrieved legal context was insufficient",
                execution_report=report,
            )

        # 7. Check for legal conflict indication
        has_conflict = "conflicting" in response_text.lower() or "conflict" in response_text.lower()

        # 8. Strict Citation Validation Safety Check
        is_valid_grounding, valid_citations, invalid_tags = self.citation_validator.validate(
            text=response_text,
            context_blocks=context_blocks,
        )

        if not is_valid_grounding:
            logger.error(
                "RAG Citation Validation Failed: LLM generated unassigned context tags %s. "
                "Suppressing answer and marking abstained=True.",
                invalid_tags,
            )
            report = RAGExecutionReport(
                provider_name=self.llm_provider.provider_name,
                model_name=self.llm_provider.model_name,
                context_blocks_count=len(context_blocks),
                estimated_input_tokens=input_tokens,
                output_tokens=raw_response.output_tokens,
                execution_time_ms=round(elapsed_ms, 2),
                abstained=True,
            )
            return GenerationResult(
                query=clean_query,
                answer=ABSTENTION_MESSAGE,
                citations=[],
                abstained=True,
                abstention_reason=f"Citation validation failure for tags {invalid_tags}",
                has_legal_conflict=has_conflict,
                execution_report=report,
            )

        # 9. Return grounded generation result
        report = RAGExecutionReport(
            provider_name=self.llm_provider.provider_name,
            model_name=self.llm_provider.model_name,
            context_blocks_count=len(context_blocks),
            estimated_input_tokens=input_tokens,
            output_tokens=raw_response.output_tokens,
            execution_time_ms=round(elapsed_ms, 2),
            abstained=False,
        )

        return GenerationResult(
            query=clean_query,
            answer=response_text,
            citations=valid_citations,
            abstained=False,
            abstention_reason=None,
            has_legal_conflict=has_conflict,
            execution_report=report,
        )
