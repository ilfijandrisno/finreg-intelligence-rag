"""Reciprocal Rank Fusion (RRF) algorithm and deterministic tie-breaking logic."""

from collections.abc import Sequence
from uuid import UUID

from finreg.hybrid.hybrid_models import HybridSearchResult
from finreg.lexical.lexical_models import LexicalSearchResult
from finreg.vector.vector_models import VectorSearchResult


class _ChunkFusionAccumulator:
    def __init__(self, key: tuple[UUID, UUID]):
        self.key = key
        self.dense_res: VectorSearchResult | None = None
        self.lexical_res: LexicalSearchResult | None = None
        self.dense_rank: int | None = None
        self.lexical_rank: int | None = None
        self.rrf_score: float = 0.0


def reciprocal_rank_fusion(
    dense_results: Sequence[VectorSearchResult],
    lexical_results: Sequence[LexicalSearchResult],
    rrf_k: int = 60,
    top_k: int = 5,
) -> list[HybridSearchResult]:
    """Execute Reciprocal Rank Fusion over candidate retrieval branches and return top_k results.

    RRF formula: RRF_score(d) = sum(1 / (k + r_m(d))) for each branch m where rank r_m starts at 1.
    """
    if top_k <= 0 or rrf_k < 0:
        return []

    accumulators: dict[tuple[UUID, UUID], _ChunkFusionAccumulator] = {}

    # 1. Process 1-based ranks from Dense Vector Search branch
    for idx, d_res in enumerate(dense_results):
        rank = idx + 1
        key = (d_res.document_version_id, d_res.chunk_id)
        if key not in accumulators:
            accumulators[key] = _ChunkFusionAccumulator(key)

        acc = accumulators[key]
        acc.dense_res = d_res
        acc.dense_rank = rank
        acc.rrf_score += 1.0 / (rrf_k + rank)

    # 2. Process 1-based ranks from BM25 Lexical Search branch
    for idx, l_res in enumerate(lexical_results):
        rank = idx + 1
        key = (l_res.document_version_id, l_res.chunk_id)
        if key not in accumulators:
            accumulators[key] = _ChunkFusionAccumulator(key)

        acc = accumulators[key]
        acc.lexical_res = l_res
        acc.lexical_rank = rank
        acc.rrf_score += 1.0 / (rrf_k + rank)

    if not accumulators:
        return []

    # 3. Build candidate list with provenance payload
    candidate_list: list[tuple[_ChunkFusionAccumulator, HybridSearchResult]] = []
    for acc in accumulators.values():
        ref: VectorSearchResult | LexicalSearchResult
        if acc.dense_res is not None and acc.lexical_res is not None:
            method = "hybrid"
            ref = acc.dense_res
        elif acc.dense_res is not None:
            method = "dense_only"
            ref = acc.dense_res
        else:
            assert acc.lexical_res is not None
            method = "lexical_only"
            ref = acc.lexical_res

        h_res = HybridSearchResult(
            fused_score=round(acc.rrf_score, 6),
            dense_rank=acc.dense_rank,
            lexical_rank=acc.lexical_rank,
            dense_score=round(acc.dense_res.score, 4) if acc.dense_res is not None else None,
            lexical_score=round(acc.lexical_res.score, 4) if acc.lexical_res is not None else None,
            retrieval_method=method,
            chunk_id=ref.chunk_id,
            source_node_id=ref.source_node_id,
            document_id=ref.document_id,
            document_version_id=ref.document_version_id,
            source=ref.source,
            regulation_type=ref.regulation_type,
            regulation_number=ref.regulation_number,
            title=ref.title,
            chapter_title=ref.chapter_title,
            part_title=ref.part_title,
            section_title=ref.section_title,
            article_number=ref.article_number,
            paragraph_number=ref.paragraph_number,
            letter_code=ref.letter_code,
            numbered_item=ref.numbered_item,
            part_index=ref.part_index,
            total_parts=ref.total_parts,
            structural_path=ref.structural_path,
            chunk_text=ref.chunk_text,
            contextual_text=ref.contextual_text,
            page_start=ref.page_start,
            page_end=ref.page_end,
            sequence=ref.sequence,
        )
        candidate_list.append((acc, h_res))

    # 4. Enforce deterministic multi-key tie-breaking sort order:
    #    1. fused_score DESC
    #    2. dense_rank ASC (if None, float('inf'))
    #    3. lexical_rank ASC (if None, float('inf'))
    #    4. structural_path ASC
    #    5. sequence ASC
    #    6. str(chunk_id) ASC
    candidate_list.sort(
        key=lambda x: (
            -x[1].fused_score,
            x[0].dense_rank if x[0].dense_rank is not None else float("inf"),
            x[0].lexical_rank if x[0].lexical_rank is not None else float("inf"),
            x[1].structural_path,
            x[1].sequence,
            str(x[1].chunk_id),
        )
    )

    top_candidates = [item[1] for item in candidate_list[:top_k]]
    return top_candidates
