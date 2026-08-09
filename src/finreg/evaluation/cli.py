"""Terminal CLI entrypoint for running Phase 8 RAG evaluation benchmark."""

import argparse
import sys
from pathlib import Path

from finreg.evaluation.benchmark_runner import BenchmarkRunner
from finreg.evaluation.dataset_loader import load_eval_dataset
from finreg.observability.logging import setup_logging

logger = setup_logging()


def main() -> None:
    """CLI handler executing RAG benchmark evaluation suite and exporting report artifacts."""
    parser = argparse.ArgumentParser(
        description="FinReg Intelligence RAG Evaluation & Benchmarking CLI"
    )
    parser.add_argument(
        "--dataset-path",
        type=str,
        default="data/evaluation/benchmark_gold_dataset.json",
        help="Path to evaluation benchmark dataset JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/evaluation/reports",
        help="Directory to save JSON and Markdown benchmark report artifacts",
    )
    parser.add_argument(
        "--use-mock-llm",
        action="store_true",
        default=True,
        help="Use MockLLMProvider for offline deterministic generation evaluation",
    )

    args = parser.parse_args()
    ds_path = Path(args.dataset_path)
    out_dir = Path(args.output_dir)

    logger.info("Loading evaluation dataset from '%s'...", ds_path)
    try:
        dataset = load_eval_dataset(ds_path)
    except Exception as exc:
        logger.error("Failed to load evaluation dataset: %s", exc)
        sys.exit(1)

    logger.info("Initializing BenchmarkRunner and executing evaluation...")
    runner = BenchmarkRunner(use_mock_llm=args.use_mock_llm)
    report = runner.run_benchmark(dataset)

    json_artifact, md_artifact = runner.export_reports(report, out_dir)

    logger.info("Benchmark execution complete!")
    logger.info("JSON Report Artifact saved to: %s", json_artifact.resolve())
    logger.info("Markdown Report Artifact saved to: %s", md_artifact.resolve())

    # Output summary to console
    print("\n" + "=" * 70)
    print("      FINREG INTELLIGENCE RAG EVALUATION BENCHMARK SUMMARY")
    print("=" * 70)
    print(f" Dataset Version : {report.dataset_version}")
    print(f" Total Samples   : {report.total_samples}")
    print(f" Timestamp       : {report.benchmark_timestamp}")
    print("-" * 70)
    print(" RETRIEVAL STAGE COMPARISON (MRR@5 / nDCG@5 / Precision@5):")
    for s in report.retrieval_stages:
        m_str = f"MRR@5: {s.mrr_5:.4f} | nDCG@5: {s.ndcg_5:.4f} | P@5: {s.precision_5:.4f}"
        print(f"  • {s.stage_name:36s} | {m_str}")

    if report.generation_metrics:
        gm = report.generation_metrics
        print("-" * 70)
        print(" GENERATION & GROUNDING METRICS (Phase 6 RAG):")
        print(f"  • Citation Validity     : {gm.citation_validity * 100:.2f}%")
        print(f"  • Citation Precision    : {gm.citation_precision * 100:.2f}%")
        print(f"  • Citation Recall       : {gm.citation_recall * 100:.2f}%")
        print(f"  • Grounding Coverage    : {gm.grounding_coverage * 100:.2f}%")
        print(f"  • Gold Claim Coverage   : {gm.gold_claim_coverage * 100:.2f}%")
        print(f"  • Unsupported Claim Rate: {gm.unsupported_claim_rate * 100:.2f}%")
        print(f"  • Abstention Accuracy   : {gm.abstention_accuracy * 100:.2f}%")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
