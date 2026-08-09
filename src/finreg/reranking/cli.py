"""Developer CLI for Phase 5 Neural Cross-Encoder Reranking execution."""

import argparse
import logging
import sys
from uuid import UUID

from finreg.observability.logging import setup_logging
from finreg.reranking.providers import CrossEncoderRerankerProvider, MockRerankerProvider
from finreg.reranking.service import RerankingService

logger = logging.getLogger("finreg.reranking.cli")


def main() -> None:
    """CLI entrypoint for Phase 5 Neural Reranking execution."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="FinReg Phase 5 — Neural Cross-Encoder Reranking CLI"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query text string",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Final top-N reranked search results limit (default: 5)",
    )
    parser.add_argument(
        "--hybrid-top-k",
        type=int,
        default=20,
        help="Candidate pool size retrieved from Phase 4C before reranking (default: 20)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Optional filter by regulatory authority source (e.g. 'BI', 'OJK')",
    )
    parser.add_argument(
        "--regulation-type",
        type=str,
        default=None,
        help="Optional filter by regulation type (e.g. 'PBI', 'PADG')",
    )
    parser.add_argument(
        "--regulation-number",
        type=str,
        default=None,
        help="Optional filter by official regulation number string",
    )
    parser.add_argument(
        "--document-id",
        type=str,
        default=None,
        help="Optional filter by document UUID string",
    )
    parser.add_argument(
        "--use-mock",
        action="store_true",
        help="Use MockRerankerProvider instead of CrossEncoderRerankerProvider",
    )

    args = parser.parse_args()

    doc_id: UUID | None = None
    if args.document_id:
        try:
            doc_id = UUID(args.document_id)
        except ValueError:
            logger.error("Invalid UUID format for --document-id: %s", args.document_id)
            sys.exit(1)

    reranker = MockRerankerProvider() if args.use_mock else CrossEncoderRerankerProvider()
    logger.info("Executing Phase 5 Neural Reranking using model '%s'...", reranker.model_name)

    service = RerankingService(reranker=reranker)

    try:
        results, report = service.search(
            query=args.query,
            top_n=args.top_n,
            hybrid_top_k=args.hybrid_top_k,
            source_filter=args.source,
            regulation_type_filter=args.regulation_type,
            regulation_number_filter=args.regulation_number,
            document_id_filter=doc_id,
        )
    except Exception as exc:
        logger.error("Neural reranking execution failed: %s", exc)
        sys.exit(1)

    print("\n" + "=" * 68)
    print("         PHASE 5 NEURAL CROSS-ENCODER RERANKING RESULTS")
    print("=" * 68)
    print(f" Query Text      : {args.query}")
    print(f" Model Name      : {report.model_name}")
    print(f" Input Candidates: {report.candidates_in_count} chunks")
    print(f" Returned Results: {report.reranked_out_count} matches (Top-N: {args.top_n})")
    print(f" Execution Latency: {report.execution_time_ms:.2f} ms")
    print("-" * 68)

    for idx, r in enumerate(results, start=1):
        dense_str = f"Rank {r.dense_rank}" if r.dense_rank is not None else "None"
        lex_str = f"Rank {r.lexical_rank}" if r.lexical_rank is not None else "None"

        print(f"\n --- RESULT #{idx} [Rerank: {r.rerank_score:.4f} | RRF: {r.fused_score:.6f}] ---")
        print(f" Method / Provenance: {r.retrieval_method} (Dense: {dense_str} | BM25: {lex_str})")
        print(f" Regulation         : {r.source} - {r.regulation_type} No. {r.regulation_number}")
        print(f" Path               : {r.structural_path}")
        print(f" Page               : {r.page_start} - {r.page_end}")
        print(f" Chunk ID           : {r.chunk_id}")
        preview = r.chunk_text.replace("\n", " ")[:200]
        print(f" Text Preview:\n{preview}...")

    print("=" * 68 + "\n")


if __name__ == "__main__":
    main()
