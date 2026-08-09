"""Unit tests for deterministic generation & grounding metrics evaluator."""

from uuid import uuid4

from finreg.evaluation.eval_models import (
    CanonicalEvidence,
    EvalSample,
    GoldClaim,
    GoldGeneration,
)
from finreg.evaluation.generation_evaluator import GenerationEvaluator, extract_claims
from finreg.rag.rag_models import GenerationResult, LegalCitation, RAGExecutionReport


def test_extract_claims() -> None:
    text = "Ketentuan lindung nilai diatur dalam [C1]. Bank mitra wajib mematuhi [C2]."
    claims = extract_claims(text)
    assert len(claims) == 2
    assert "Ketentuan lindung nilai" in claims[0]
    assert "Bank mitra" in claims[1]


def test_generation_evaluator_metrics() -> None:
    doc1 = uuid4()
    ev1 = CanonicalEvidence(
        document_id=doc1, structural_path="Pasal 1", page_start=1, page_end=1, relevance=3
    )

    sample = EvalSample(
        sample_id="s1",
        query="q1",
        canonical_ground_truth=[ev1],
        gold_generation=GoldGeneration(
            expected_abstain=False,
            expected_claims=[
                GoldClaim(
                    claim_id="c1", claim_description="Ketentuan valas", supporting_evidence=[ev1]
                )
            ],
        ),
    )

    cit1 = LegalCitation(
        context_id="C1",
        chunk_id=uuid4(),
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        structural_path="Pasal 1",
        page_start=1,
        page_end=1,
    )

    res = GenerationResult(
        query="q1",
        answer="Ketentuan valas diatur [C1].",
        citations=[cit1],
        abstained=False,
        execution_report=RAGExecutionReport(
            provider_name="mock",
            model_name="mock",
            context_blocks_count=1,
            estimated_input_tokens=10,
            execution_time_ms=1.0,
            abstained=False,
        ),
    )

    evaluator = GenerationEvaluator()
    metrics = evaluator.evaluate_generation([sample], [res])

    assert metrics.total_samples == 1
    assert metrics.citation_validity == 1.0
    assert metrics.citation_precision == 1.0
    assert metrics.citation_recall == 1.0
    assert metrics.grounding_coverage == 1.0
    assert metrics.gold_claim_coverage == 1.0
    assert metrics.unsupported_claim_rate == 0.0
    assert metrics.abstention_accuracy == 1.0
