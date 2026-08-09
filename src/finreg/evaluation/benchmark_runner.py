"""Benchmark execution runner orchestrating multi-stage retrieval and RAG evaluation."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finreg.config.settings import get_settings
from finreg.evaluation.eval_models import BenchmarkReport, EvalDataset
from finreg.evaluation.generation_evaluator import GenerationEvaluator
from finreg.evaluation.retrieval_evaluator import RetrievalEvaluator
from finreg.hybrid.service import HybridRetrievalService
from finreg.lexical.service import LexicalRetrievalService
from finreg.rag.providers import MockLLMProvider
from finreg.rag.rag_models import GenerationResult, RAGExecutionReport
from finreg.rag.service import RAGService
from finreg.reranking.service import RerankingService
from finreg.vector.search_service import VectorSearchService

logger = logging.getLogger("finreg.evaluation.runner")


class BenchmarkRunner:
    """Orchestrates benchmark evaluation across all 4 retrieval stages and Phase 6 RAG."""

    def __init__(
        self,
        vector_service: VectorSearchService | None = None,
        lexical_service: LexicalRetrievalService | None = None,
        hybrid_service: HybridRetrievalService | None = None,
        reranking_service: RerankingService | None = None,
        rag_service: RAGService | None = None,
        use_mock_llm: bool = False,
    ):
        self.vector_service = vector_service or VectorSearchService()
        self.lexical_service = lexical_service or LexicalRetrievalService()
        self.hybrid_service = hybrid_service or HybridRetrievalService()
        self.reranking_service = reranking_service or RerankingService()

        if rag_service is None:
            settings = get_settings()
            llm_provider = None
            if use_mock_llm or not settings.llm_api_key:
                llm_provider = MockLLMProvider()
            self.rag_service = RAGService(
                llm_provider=llm_provider,
                reranking_service=self.reranking_service,
            )
        else:
            self.rag_service = rag_service

        self.retrieval_evaluator = RetrievalEvaluator()
        self.generation_evaluator = GenerationEvaluator()

    def run_benchmark(self, dataset: EvalDataset) -> BenchmarkReport:
        """Execute full benchmark evaluation suite against dataset.

        Args:
            dataset: Validated evaluation dataset object.

        Returns:
            BenchmarkReport: Complete metrics report object.
        """
        logger.info("Starting Phase 8 Benchmark Run over %d samples...", len(dataset.samples))

        stage1_results: list[list[Any]] = []
        stage2_results: list[list[Any]] = []
        stage3_results: list[list[Any]] = []
        stage4_results: list[list[Any]] = []
        rag_gen_results: list[GenerationResult] = []

        for sample in dataset.samples:
            query = sample.query

            # Stage 1: Dense Vector Retrieval (Phase 4A)
            res1: list[Any] = []
            try:
                res1_out = self.vector_service.search(query=query, top_k=10)
                res1 = list(res1_out)
            except Exception as exc:
                logger.warning(
                    "Stage 1 Dense search failed for sample '%s': %s", sample.sample_id, exc
                )
            stage1_results.append(res1)

            # Stage 2: BM25 Lexical Retrieval (Phase 4B)
            res2: list[Any] = []
            try:
                res2_out, _ = self.lexical_service.search(query=query, top_k=10)
                res2 = list(res2_out)
            except Exception as exc:
                logger.warning(
                    "Stage 2 Lexical search failed for sample '%s': %s", sample.sample_id, exc
                )
            stage2_results.append(res2)

            # Stage 3: Hybrid RRF Fusion (Phase 4C)
            res3: list[Any] = []
            try:
                res3_out, _ = self.hybrid_service.search(query=query, top_k=10)
                res3 = list(res3_out)
            except Exception as exc:
                logger.warning(
                    "Stage 3 Hybrid search failed for sample '%s': %s", sample.sample_id, exc
                )
            stage3_results.append(res3)

            # Stage 4: Hybrid + Cross-Encoder Reranking (Phase 5)
            res4: list[Any] = []
            try:
                res4_out, _ = self.reranking_service.search(query=query, top_n=10)
                res4 = list(res4_out)
            except Exception as exc:
                logger.warning(
                    "Stage 4 Reranking failed for sample '%s': %s", sample.sample_id, exc
                )
                res4 = []
            stage4_results.append(res4)

            # Phase 6 Grounded RAG Generation
            try:
                gen_res = self.rag_service.search_and_generate(query=query, top_n=5)
            except Exception as exc:
                logger.warning(
                    "Phase 6 RAG generation failed for sample '%s': %s", sample.sample_id, exc
                )
                gen_res = GenerationResult(
                    query=query,
                    answer="",
                    citations=[],
                    abstained=True,
                    abstention_reason=str(exc),
                    execution_report=RAGExecutionReport(
                        provider_name="error",
                        model_name="error",
                        context_blocks_count=0,
                        estimated_input_tokens=0,
                        execution_time_ms=0.0,
                        abstained=True,
                    ),
                )
            rag_gen_results.append(gen_res)

        # Compute Retrieval Metrics
        m1 = self.retrieval_evaluator.evaluate_stage(
            "Stage 1: Dense Vector (Phase 4A) [Non-production / Mock Embedding Benchmark]",
            dataset.samples,
            stage1_results,
        )
        m2 = self.retrieval_evaluator.evaluate_stage(
            "Stage 2: BM25 Lexical (Phase 4B)", dataset.samples, stage2_results
        )
        m3 = self.retrieval_evaluator.evaluate_stage(
            "Stage 3: Hybrid RRF (Phase 4C)", dataset.samples, stage3_results
        )
        m4 = self.retrieval_evaluator.evaluate_stage(
            "Stage 4: Hybrid + Rerank (Phase 5)", dataset.samples, stage4_results
        )

        # Compute Generation Metrics
        gen_metrics = self.generation_evaluator.evaluate_generation(
            dataset.samples, rag_gen_results
        )

        timestamp_str = datetime.now(UTC).isoformat()
        return BenchmarkReport(
            benchmark_timestamp=timestamp_str,
            dataset_version=dataset.dataset_version,
            total_samples=len(dataset.samples),
            retrieval_stages=[m1, m2, m3, m4],
            generation_metrics=gen_metrics,
        )

    def export_reports(self, report: BenchmarkReport, output_dir: str | Path) -> tuple[Path, Path]:
        """Export benchmark report to JSON and Markdown files.

        Returns:
            tuple[Path, Path]: Paths to created JSON and Markdown report artifacts.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        json_path = out_path / "benchmark_report.json"
        md_path = out_path / "benchmark_report.md"

        # Save JSON
        json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        # Save Markdown
        md_content = self.generate_markdown_report(report)
        md_path.write_text(md_content, encoding="utf-8")

        return json_path, md_path

    def generate_markdown_report(self, report: BenchmarkReport) -> str:
        """Generate human-readable Markdown summary report."""
        lines = [
            "# FinReg Intelligence RAG Evaluation Benchmark Report",
            "",
            f"- **Execution Timestamp**: `{report.benchmark_timestamp}`",
            f"- **Dataset Version**: `{report.dataset_version}`",
            f"- **Total Evaluation Samples**: `{report.total_samples}`",
            "",
            "## 1. Multi-Stage Retrieval Performance Comparison",
            "",
            (
                "| Retrieval Pipeline Stage | MRR@1 (=HitRate@1) | MRR@5 | MRR@10 | "
                "HitRate@5 | HitRate@10 | nDCG@5 | nDCG@10 | Precision@5 | Recall@5 |"
            ),
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for s in report.retrieval_stages:
            lines.append(
                f"| **{s.stage_name}** | {s.mrr_1:.4f} | {s.mrr_5:.4f} | {s.mrr_10:.4f} | "
                f"{s.hit_rate_5:.4f} | {s.hit_rate_10:.4f} | {s.ndcg_5:.4f} | {s.ndcg_10:.4f} | "
                f"{s.precision_5:.4f} | {s.recall_5:.4f} |"
            )

        lines.extend(
            [
                "",
                "## 2. Generation & Grounding Performance (Phase 6 RAG)",
                "",
            ]
        )

        gm = report.generation_metrics
        if gm:
            lines.extend(
                [
                    f"- **Citation Validity**: `{gm.citation_validity * 100:.2f}%`",
                    f"- **Citation Precision**: `{gm.citation_precision * 100:.2f}%`",
                    f"- **Citation Recall**: `{gm.citation_recall * 100:.2f}%`",
                    f"- **Grounding Coverage**: `{gm.grounding_coverage * 100:.2f}%`",
                    f"- **Gold Claim Coverage**: `{gm.gold_claim_coverage * 100:.2f}%`",
                    f"- **Unsupported Claim Rate**: `{gm.unsupported_claim_rate * 100:.2f}%`",
                    f"- **Abstention Accuracy**: `{gm.abstention_accuracy * 100:.2f}%`",
                ]
            )
        else:
            lines.append("_No generation metrics calculated._")

        lines.append("")
        return "\n".join(lines)
