"""Pure mathematical retrieval evaluation metrics (MRR, HitRate, nDCG, Precision, Recall)."""

import math
from typing import Any

from finreg.evaluation.eval_models import (
    CanonicalEvidence,
    EvalSample,
    RetrievalStageMetrics,
    normalize_structural_path,
)


def canonical_matches(retrieved_item: Any, gt_item: CanonicalEvidence) -> bool:
    """Check if a retrieved chunk matches a canonical ground truth evidence item.

    Matching uses normalized structural_path without mutating the original item.
    Equality comparison: (document_id, normalized_path, page_start, page_end).
    """
    doc_id = getattr(retrieved_item, "document_id", None)
    raw_struct_path = getattr(retrieved_item, "structural_path", None)
    p_start = getattr(retrieved_item, "page_start", None)
    p_end = getattr(retrieved_item, "page_end", None)

    if doc_id != gt_item.document_id:
        return False
    if p_start != gt_item.page_start or p_end != gt_item.page_end:
        return False

    norm_retrieved = normalize_structural_path(str(raw_struct_path or ""))
    norm_gt = gt_item.normalized_path()

    return norm_retrieved == norm_gt


def get_item_relevance(retrieved_item: Any, ground_truth: list[CanonicalEvidence]) -> int:
    """Return maximum graded relevance score (0-3) for a retrieved item."""
    max_rel = 0
    for gt in ground_truth:
        if canonical_matches(retrieved_item, gt) and gt.relevance > max_rel:
            max_rel = gt.relevance
    return max_rel


def calculate_dcg_at_k(relevances: list[int], k: int) -> float:
    """Calculate Discounted Cumulative Gain at cutoff K."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        if rel > 0:
            dcg += (2**rel - 1) / math.log2(i + 2)
    return dcg


def calculate_idcg_at_k(ground_truth: list[CanonicalEvidence], k: int) -> float:
    """Calculate Ideal Discounted Cumulative Gain at cutoff K from gold relevance annotations."""
    sorted_rels = sorted([gt.relevance for gt in ground_truth], reverse=True)
    return calculate_dcg_at_k(sorted_rels, k)


def calculate_ndcg_at_k(
    retrieved_items: list[Any], ground_truth: list[CanonicalEvidence], k: int
) -> float:
    """Calculate Normalized Discounted Cumulative Gain at cutoff K."""
    if not ground_truth:
        return 0.0
    idcg = calculate_idcg_at_k(ground_truth, k)
    if idcg <= 0.0:
        return 0.0
    rels = [get_item_relevance(item, ground_truth) for item in retrieved_items]
    dcg = calculate_dcg_at_k(rels, k)
    return min(dcg / idcg, 1.0)


def calculate_reciprocal_rank_at_k(
    retrieved_items: list[Any], ground_truth: list[CanonicalEvidence], k: int
) -> float:
    """Calculate Reciprocal Rank (1/rank of first matching item) at cutoff K."""
    if not ground_truth or not retrieved_items:
        return 0.0
    for rank_idx, item in enumerate(retrieved_items[:k], start=1):
        if get_item_relevance(item, ground_truth) > 0:
            return 1.0 / rank_idx
    return 0.0


def calculate_hit_rate_at_k(
    retrieved_items: list[Any], ground_truth: list[CanonicalEvidence], k: int
) -> float:
    """Calculate Hit Rate (1 if any match in top-K else 0)."""
    if not ground_truth or not retrieved_items:
        return 0.0
    for item in retrieved_items[:k]:
        if get_item_relevance(item, ground_truth) > 0:
            return 1.0
    return 0.0


class RetrievalEvaluator:
    """Evaluates multi-stage retrieval metrics against canonical ground truth."""

    def evaluate_stage(
        self,
        stage_name: str,
        samples: list[EvalSample],
        stage_retrievals: list[list[Any]],
    ) -> RetrievalStageMetrics:
        """Calculate aggregate retrieval metrics for in-domain samples with ground truth.

        Out-of-domain samples (query_type == 'out_of_domain' or empty ground truth) are excluded
        from the retrieval denominator to prevent diluting retrieval ranking metrics.
        """
        eval_pairs = [
            (sample, items)
            for sample, items in zip(samples, stage_retrievals, strict=False)
            if sample.query_type == "in_domain" and len(sample.canonical_ground_truth) > 0
        ]

        valid_samples_count = len(eval_pairs)
        if valid_samples_count == 0:
            return RetrievalStageMetrics(
                stage_name=stage_name,
                mrr_1=0.0,
                mrr_5=0.0,
                mrr_10=0.0,
                hit_rate_1=0.0,
                hit_rate_5=0.0,
                hit_rate_10=0.0,
                ndcg_5=0.0,
                ndcg_10=0.0,
                precision_5=0.0,
                recall_5=0.0,
            )

        sum_mrr_1 = 0.0
        sum_mrr_5 = 0.0
        sum_mrr_10 = 0.0
        sum_hit_1 = 0.0
        sum_hit_5 = 0.0
        sum_hit_10 = 0.0
        sum_ndcg_5 = 0.0
        sum_ndcg_10 = 0.0
        sum_prec_5 = 0.0
        sum_rec_5 = 0.0

        for sample, items in eval_pairs:
            gt = sample.canonical_ground_truth

            sum_mrr_1 += calculate_reciprocal_rank_at_k(items, gt, 1)
            sum_mrr_5 += calculate_reciprocal_rank_at_k(items, gt, 5)
            sum_mrr_10 += calculate_reciprocal_rank_at_k(items, gt, 10)

            sum_hit_1 += calculate_hit_rate_at_k(items, gt, 1)
            sum_hit_5 += calculate_hit_rate_at_k(items, gt, 5)
            sum_hit_10 += calculate_hit_rate_at_k(items, gt, 10)

            sum_ndcg_5 += calculate_ndcg_at_k(items, gt, 5)
            sum_ndcg_10 += calculate_ndcg_at_k(items, gt, 10)

            # Precision@5 and Recall@5
            matched_count = 0
            for item in items[:5]:
                if get_item_relevance(item, gt) > 0:
                    matched_count += 1

            sum_prec_5 += matched_count / 5.0 if items else 0.0
            sum_rec_5 += matched_count / float(len(gt)) if gt else 0.0

        count = float(valid_samples_count)
        return RetrievalStageMetrics(
            stage_name=stage_name,
            mrr_1=round(sum_mrr_1 / count, 4),
            mrr_5=round(sum_mrr_5 / count, 4),
            mrr_10=round(sum_mrr_10 / count, 4),
            hit_rate_1=round(sum_hit_1 / count, 4),
            hit_rate_5=round(sum_hit_5 / count, 4),
            hit_rate_10=round(sum_hit_10 / count, 4),
            ndcg_5=round(sum_ndcg_5 / count, 4),
            ndcg_10=round(sum_ndcg_10 / count, 4),
            precision_5=round(sum_prec_5 / count, 4),
            recall_5=round(sum_rec_5 / count, 4),
        )
