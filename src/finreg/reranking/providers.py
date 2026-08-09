"""Pluggable Cross-Encoder reranker protocol and concrete provider implementations."""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Sequence

from finreg.config.settings import get_settings
from finreg.hybrid.hybrid_models import HybridSearchResult
from finreg.reranking.rerank_models import RerankedSearchResult

logger = logging.getLogger(__name__)


def sort_reranked_candidates(candidates: list[RerankedSearchResult]) -> list[RerankedSearchResult]:
    """Enforce deterministic 7-key tie-breaking sort order across reranked results."""
    candidates.sort(
        key=lambda x: (
            -x.rerank_score,
            -x.fused_score,
            x.dense_rank if x.dense_rank is not None else float("inf"),
            x.lexical_rank if x.lexical_rank is not None else float("inf"),
            x.structural_path,
            x.sequence,
            str(x.chunk_id),
        )
    )
    # Assign 1-based rerank_rank positions post-sorting
    for rank_idx, item in enumerate(candidates, start=1):
        item.rerank_rank = rank_idx
    return candidates


class Reranker(ABC):
    """Abstract protocol for neural and mock reranker providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model identifier string."""
        pass

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: Sequence[HybridSearchResult],
        top_n: int = 5,
    ) -> list[RerankedSearchResult]:
        """Rescore and truncate candidate HybridSearchResults to top_n reranked results."""
        pass


class MockRerankerProvider(Reranker):
    """Deterministic offline mock reranker provider for unit testing."""

    def __init__(self, model_name: str = "mock-reranker-v1"):
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def rerank(
        self,
        query: str,
        candidates: Sequence[HybridSearchResult],
        top_n: int = 5,
    ) -> list[RerankedSearchResult]:
        """Produce deterministic mock rerank scores based on term overlap and candidate ranks."""
        if not query or not query.strip() or top_n <= 0 or not candidates:
            return []

        query_words = set(query.lower().split())
        rescored: list[RerankedSearchResult] = []

        for cand in candidates:
            chunk_words = set(cand.contextual_text.lower().split())
            matched = len(query_words.intersection(chunk_words))
            # Base mock score derived from matched terms count and RRF score
            mock_score = round(matched * 1.5 + cand.fused_score, 4)

            res = RerankedSearchResult(
                rerank_score=mock_score,
                rerank_rank=1,  # will be assigned post-sorting
                fused_score=cand.fused_score,
                dense_rank=cand.dense_rank,
                lexical_rank=cand.lexical_rank,
                dense_score=cand.dense_score,
                lexical_score=cand.lexical_score,
                retrieval_method=cand.retrieval_method,
                chunk_id=cand.chunk_id,
                source_node_id=cand.source_node_id,
                document_id=cand.document_id,
                document_version_id=cand.document_version_id,
                source=cand.source,
                regulation_type=cand.regulation_type,
                regulation_number=cand.regulation_number,
                title=cand.title,
                chapter_title=cand.chapter_title,
                part_title=cand.part_title,
                section_title=cand.section_title,
                article_number=cand.article_number,
                paragraph_number=cand.paragraph_number,
                letter_code=cand.letter_code,
                numbered_item=cand.numbered_item,
                part_index=cand.part_index,
                total_parts=cand.total_parts,
                structural_path=cand.structural_path,
                chunk_text=cand.chunk_text,
                contextual_text=cand.contextual_text,
                page_start=cand.page_start,
                page_end=cand.page_end,
                sequence=cand.sequence,
            )
            rescored.append(res)

        sorted_results = sort_reranked_candidates(rescored)
        return sorted_results[:top_n]


class CrossEncoderRerankerProvider(Reranker):
    """Production neural Cross-Encoder reranker provider with fail-fast error handling."""

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self._model_name = model_name or settings.reranker_model_name
        self._model = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _load_model(self) -> None:
        """Lazy load CrossEncoder model instance or fail fast with clear exception."""
        if self._model is not None:
            return

        logger.info("Initializing neural Cross-Encoder model: '%s'...", self._model_name)
        start_time = time.perf_counter()

        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info("Model '%s' loaded in %.2fms.", self._model_name, elapsed)

        except Exception as exc:
            err_msg = (
                f"Failed to load configured Cross-Encoder model '{self._model_name}'. "
                f"Error: {exc}. Verify sentence-transformers dependency and model identifier."
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg) from exc

    def rerank(
        self,
        query: str,
        candidates: Sequence[HybridSearchResult],
        top_n: int = 5,
    ) -> list[RerankedSearchResult]:
        """Rescore candidates using neural Cross-Encoder pair attention and truncate to top_n."""
        if not query or not query.strip() or top_n <= 0 or not candidates:
            return []

        # Enforce strict model loading (raises RuntimeError if unavailable)
        self._load_model()
        assert self._model is not None

        clean_query = query.strip()
        # Form (query, contextual_text) pairs for Cross-Encoder scoring
        pairs = [(clean_query, cand.contextual_text) for cand in candidates]

        scores = self._model.predict(pairs)

        rescored: list[RerankedSearchResult] = []
        for idx, cand in enumerate(candidates):
            raw_score = float(scores[idx])

            res = RerankedSearchResult(
                rerank_score=round(raw_score, 4),
                rerank_rank=1,  # assigned post-sorting
                fused_score=cand.fused_score,
                dense_rank=cand.dense_rank,
                lexical_rank=cand.lexical_rank,
                dense_score=cand.dense_score,
                lexical_score=cand.lexical_score,
                retrieval_method=cand.retrieval_method,
                chunk_id=cand.chunk_id,
                source_node_id=cand.source_node_id,
                document_id=cand.document_id,
                document_version_id=cand.document_version_id,
                source=cand.source,
                regulation_type=cand.regulation_type,
                regulation_number=cand.regulation_number,
                title=cand.title,
                chapter_title=cand.chapter_title,
                part_title=cand.part_title,
                section_title=cand.section_title,
                article_number=cand.article_number,
                paragraph_number=cand.paragraph_number,
                letter_code=cand.letter_code,
                numbered_item=cand.numbered_item,
                part_index=cand.part_index,
                total_parts=cand.total_parts,
                structural_path=cand.structural_path,
                chunk_text=cand.chunk_text,
                contextual_text=cand.contextual_text,
                page_start=cand.page_start,
                page_end=cand.page_end,
                sequence=cand.sequence,
            )
            rescored.append(res)

        sorted_results = sort_reranked_candidates(rescored)
        return sorted_results[:top_n]
