"""Deterministic generation & grounding metrics evaluator."""

import re
from typing import Any

from finreg.evaluation.eval_models import (
    CanonicalEvidence,
    EvalSample,
    GenerationMetrics,
    normalize_structural_path,
)
from finreg.rag.citation_validator import CITATION_REGEX
from finreg.rag.rag_models import GenerationResult


def extract_claims(text: str) -> list[str]:
    """Split generated text into discrete claims/sentences for claim-level analysis."""
    if not text or not text.strip():
        return []
    raw_claims = re.split(r"(?<=[.!?\n;])\s+", text.strip())
    return [c.strip() for c in raw_claims if c.strip() and len(c.strip()) > 5]


def citation_matches_gt(cit: Any, gt: CanonicalEvidence) -> bool:
    """Check if citation matches canonical evidence ground truth.

    Matching uses normalized structural_path without mutating the original item.
    Equality comparison: (document_id, normalized_path, page_start, page_end).
    """
    cit_doc = getattr(cit, "document_id", None)
    cit_path = getattr(cit, "structural_path", None)
    cit_start = getattr(cit, "page_start", None)
    cit_end = getattr(cit, "page_end", None)

    if cit_doc is not None and cit_doc != gt.document_id:
        return False
    if (
        cit_start is not None
        and cit_end is not None
        and (cit_start != gt.page_start or cit_end != gt.page_end)
    ):
        return False

    norm_cit = normalize_structural_path(str(cit_path or ""))
    norm_gt = gt.normalized_path()

    return norm_cit == norm_gt


class GenerationEvaluator:
    """Evaluates Phase 6 RAG generation outputs deterministically without LLM-as-a-judge."""

    def evaluate_generation(
        self,
        samples: list[EvalSample],
        results: list[GenerationResult],
    ) -> GenerationMetrics:
        """Calculate aggregate deterministic generation and grounding metrics."""
        total_samples = len(samples)
        if total_samples == 0:
            return GenerationMetrics(
                total_samples=0,
                citation_validity=0.0,
                citation_precision=0.0,
                citation_recall=0.0,
                grounding_coverage=0.0,
                gold_claim_coverage=0.0,
                unsupported_claim_rate=0.0,
                abstention_accuracy=0.0,
            )

        valid_citations_count = 0
        total_citations_count = 0

        cited_gt_matches = 0
        total_citations_made = 0
        total_gt_items = 0

        grounded_claims_count = 0
        total_claims_count = 0

        covered_gold_claims = 0
        total_gold_claims = 0

        correct_abstentions = 0

        for sample, res in zip(samples, results, strict=False):
            gold_gen = sample.gold_generation

            # 1. Abstention Accuracy
            if gold_gen:
                if (gold_gen.expected_abstain and res.abstained) or (
                    not gold_gen.expected_abstain and not res.abstained
                ):
                    correct_abstentions += 1
            elif not res.abstained:
                correct_abstentions += 1

            if res.abstained:
                continue

            # 2. Citation Validity & Precision/Recall
            tags = CITATION_REGEX.findall(res.answer)
            total_citations_count += len(tags)
            total_citations_made += len(res.citations)
            valid_citations_count += len(res.citations)

            gt_list = sample.canonical_ground_truth
            total_gt_items += len(gt_list)

            for c in res.citations:
                for gt in gt_list:
                    if citation_matches_gt(c, gt):
                        cited_gt_matches += 1
                        break

            # 3. Grounding Coverage
            claims = extract_claims(res.answer)
            total_claims_count += len(claims)
            for claim in claims:
                if CITATION_REGEX.search(claim):
                    grounded_claims_count += 1

            # 4. Gold Claim Coverage
            if gold_gen and gold_gen.expected_claims:
                total_gold_claims += len(gold_gen.expected_claims)
                for gold_claim in gold_gen.expected_claims:
                    claim_covered = True
                    for ev in gold_claim.supporting_evidence:
                        ev_cited = any(citation_matches_gt(c, ev) for c in res.citations)
                        if not ev_cited:
                            claim_covered = False
                            break
                    if claim_covered and gold_claim.supporting_evidence:
                        covered_gold_claims += 1

        # Aggregate Metrics Calculation
        cit_validity = (
            valid_citations_count / float(total_citations_count)
            if total_citations_count > 0
            else 1.0
        )
        cit_precision = (
            cited_gt_matches / float(total_citations_made) if total_citations_made > 0 else 1.0
        )
        cit_recall = cited_gt_matches / float(total_gt_items) if total_gt_items > 0 else 1.0

        grounding_cov = (
            grounded_claims_count / float(total_claims_count) if total_claims_count > 0 else 1.0
        )
        gold_claim_cov = (
            covered_gold_claims / float(total_gold_claims) if total_gold_claims > 0 else 1.0
        )
        unsupported_rate = 1.0 - grounding_cov
        abstain_acc = correct_abstentions / float(total_samples)

        return GenerationMetrics(
            total_samples=total_samples,
            citation_validity=round(cit_validity, 4),
            citation_precision=round(cit_precision, 4),
            citation_recall=round(cit_recall, 4),
            grounding_coverage=round(grounding_cov, 4),
            gold_claim_coverage=round(gold_claim_cov, 4),
            unsupported_claim_rate=round(unsupported_rate, 4),
            abstention_accuracy=round(abstain_acc, 4),
        )
