"""Context assembly component for Phase 6 RAG pipeline."""

import logging
from collections.abc import Sequence

from finreg.rag.rag_models import ContextBlock
from finreg.reranking.rerank_models import RerankedSearchResult

logger = logging.getLogger(__name__)


def estimate_token_count(text: str) -> int:
    """Estimate token count for text using standard ~4 characters per token heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class ContextAssembler:
    """Consumes reranked search results, assigns context IDs, and enforces token budget."""

    def assemble(
        self,
        reranked_results: Sequence[RerankedSearchResult],
        max_context_tokens: int = 4000,
    ) -> list[ContextBlock]:
        """Assemble ContextBlock list with stable context IDs while enforcing token budget."""
        if not reranked_results or max_context_tokens <= 0:
            return []

        context_blocks: list[ContextBlock] = []
        accumulated_tokens = 0

        for idx, res in enumerate(reranked_results, start=1):
            context_id = f"C{idx}"
            tokens = estimate_token_count(res.contextual_text)

            if accumulated_tokens + tokens > max_context_tokens:
                logger.info(
                    "Context token budget (%d) reached at chunk %d (estimated %d tokens). "
                    "Truncating remaining low-ranked chunks.",
                    max_context_tokens,
                    idx,
                    accumulated_tokens + tokens,
                )
                break

            block = ContextBlock(
                context_id=context_id,
                reranked_result=res,
                estimated_tokens=tokens,
            )
            context_blocks.append(block)
            accumulated_tokens += tokens

        return context_blocks
