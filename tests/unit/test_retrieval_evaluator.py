"""Unit tests for pure mathematical retrieval metrics and canonical identity normalization."""

from uuid import uuid4

from finreg.evaluation.eval_models import CanonicalEvidence, EvalSample, normalize_structural_path
from finreg.evaluation.retrieval_evaluator import (
    RetrievalEvaluator,
    calculate_hit_rate_at_k,
    calculate_reciprocal_rank_at_k,
    canonical_matches,
)


class MockRetrievedItem:
    def __init__(self, doc_id: str, path: str, start: int, end: int):
        self.document_id = doc_id
        self.structural_path = path
        self.page_start = start
        self.page_end = end


def test_normalize_structural_path() -> None:
    assert (
        normalize_structural_path("BAB I/Pasal 1/Ayat (1) [Part 1/2]") == "BAB I/Pasal 1/Ayat (1)"
    )
    assert (
        normalize_structural_path("BAB I/Pasal 1/Ayat (1) [Part 2/2]") == "BAB I/Pasal 1/Ayat (1)"
    )
    assert normalize_structural_path("BAB I/Pasal 1/Ayat (1)") == "BAB I/Pasal 1/Ayat (1)"


def test_canonical_matches_rules() -> None:
    doc_id_a = uuid4()
    doc_id_b = uuid4()

    gt = CanonicalEvidence(
        document_id=doc_id_a,
        structural_path="BAB I/Pasal 1/Ayat (1)",
        page_start=2,
        page_end=2,
        relevance=3,
    )

    # Test A: Part 1/2 matches
    item_part1 = MockRetrievedItem(doc_id_a, "BAB I/Pasal 1/Ayat (1) [Part 1/2]", 2, 2)
    assert canonical_matches(item_part1, gt) is True

    # Test B: Part 2/2 matches
    item_part2 = MockRetrievedItem(doc_id_a, "BAB I/Pasal 1/Ayat (1) [Part 2/2]", 2, 2)
    assert canonical_matches(item_part2, gt) is True

    # Test C: Different legal path does NOT match
    item_diff_path = MockRetrievedItem(doc_id_a, "BAB I/Pasal 1/Ayat (2)", 2, 2)
    assert canonical_matches(item_diff_path, gt) is False

    # Test D: Different pages do NOT match
    item_diff_pages = MockRetrievedItem(doc_id_a, "BAB I/Pasal 1/Ayat (1)", 3, 3)
    assert canonical_matches(item_diff_pages, gt) is False

    # Test E: Different document_id values do NOT match
    item_diff_doc = MockRetrievedItem(doc_id_b, "BAB I/Pasal 1/Ayat (1)", 2, 2)
    assert canonical_matches(item_diff_doc, gt) is False

    # Test F: Original item structural_path string remains unchanged
    assert item_part1.structural_path == "BAB I/Pasal 1/Ayat (1) [Part 1/2]"


def test_reciprocal_rank_and_hit_rate() -> None:
    doc1 = uuid4()
    doc2 = uuid4()
    gt = [
        CanonicalEvidence(
            document_id=doc1, structural_path="Pasal 1", page_start=1, page_end=1, relevance=3
        )
    ]

    items = [
        MockRetrievedItem(doc2, "Pasal 10", 1, 1),
        MockRetrievedItem(doc1, "Pasal 1", 1, 1),
    ]

    rr_1 = calculate_reciprocal_rank_at_k(items, gt, 1)
    rr_5 = calculate_reciprocal_rank_at_k(items, gt, 5)

    hit_1 = calculate_hit_rate_at_k(items, gt, 1)
    hit_5 = calculate_hit_rate_at_k(items, gt, 5)

    assert rr_1 == 0.0
    assert rr_5 == 0.5
    assert hit_1 == 0.0
    assert hit_5 == 1.0


def test_ood_sample_exclusion_from_retrieval_denominator() -> None:
    doc1 = uuid4()
    gt = [
        CanonicalEvidence(
            document_id=doc1, structural_path="Pasal 1", page_start=1, page_end=1, relevance=3
        )
    ]
    in_domain_sample = EvalSample(
        sample_id="s1", query="q1", query_type="in_domain", canonical_ground_truth=gt
    )
    ood_sample = EvalSample(
        sample_id="s2", query="ood", query_type="out_of_domain", canonical_ground_truth=[]
    )

    items_in_domain = [MockRetrievedItem(doc1, "Pasal 1", 1, 1)]
    items_ood: list[MockRetrievedItem] = []

    evaluator = RetrievalEvaluator()

    # Run with in-domain sample only
    m_in = evaluator.evaluate_stage("Stage", [in_domain_sample], [items_in_domain])

    # Run with in-domain + OOD sample
    m_with_ood = evaluator.evaluate_stage(
        "Stage", [in_domain_sample, ood_sample], [items_in_domain, items_ood]
    )

    # Prove adding OOD sample does NOT alter retrieval metrics
    assert m_in.mrr_5 == m_with_ood.mrr_5 == 1.0
    assert m_in.hit_rate_5 == m_with_ood.hit_rate_5 == 1.0
    assert m_in.ndcg_5 == m_with_ood.ndcg_5 == 1.0
    assert m_in.precision_5 == m_with_ood.precision_5 == 0.2
    assert m_in.recall_5 == m_with_ood.recall_5 == 1.0


def test_retrieval_evaluator_stage() -> None:
    doc1 = uuid4()
    gt = [
        CanonicalEvidence(
            document_id=doc1, structural_path="Pasal 1", page_start=1, page_end=1, relevance=3
        )
    ]
    sample = EvalSample(
        sample_id="s1", query="q1", query_type="in_domain", canonical_ground_truth=gt
    )

    items = [MockRetrievedItem(doc1, "Pasal 1", 1, 1)]

    evaluator = RetrievalEvaluator()
    metrics = evaluator.evaluate_stage("Test Stage", [sample], [items])

    assert metrics.stage_name == "Test Stage"
    assert metrics.mrr_1 == 1.0
    assert metrics.mrr_5 == 1.0
    assert metrics.hit_rate_1 == 1.0
    assert metrics.hit_rate_5 == 1.0
    assert metrics.ndcg_5 == 1.0
    assert metrics.precision_5 == 0.2
    assert metrics.recall_5 == 1.0
