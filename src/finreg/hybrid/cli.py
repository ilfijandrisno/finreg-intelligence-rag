"""Developer CLI for Phase 4C Hybrid Retrieval (Dense + BM25) query execution."""

import argparse
import logging
import sys
from uuid import UUID

from finreg.hybrid.service import HybridRetrievalService
from finreg.observability.logging import setup_logging

logger = logging.getLogger("finreg.hybrid.cli")


def main() -> None:
    """CLI entrypoint for Phase 4C Hybrid Retrieval execution."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="FinReg Phase 4C — Hybrid Retrieval CLI (Dense Vector + BM25 Lexical)"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query text string",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Final top-K fused search results limit (default: 5)",
    )
    parser.add_argument(
        "--rrf-k",
        type=int,
        default=60,
        help="Reciprocal Rank Fusion smoothing constant k (default: 60)",
    )
    parser.add_argument(
        "--dense-top-k",
        type=int,
        default=20,
        help="Candidate pool size limit for dense vector search branch before fusion (default: 20)",
    )
    parser.add_argument(
        "--lexical-top-k",
        type=int,
        default=20,
        help="Candidate pool size limit for BM25 lexical search branch before fusion (default: 20)",
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

    args = parser.parse_args()

    doc_id: UUID | None = None
    if args.document_id:
        try:
            doc_id = UUID(args.document_id)
        except ValueError:
            logger.error("Invalid UUID format for --document-id: %s", args.document_id)
            sys.exit(1)

    logger.info("Executing Hybrid (Dense + BM25) search for query: '%s'...", args.query)

    service = HybridRetrievalService()

    try:
        results, report = service.search(
            query=args.query,
            top_k=args.top_k,
            rrf_k=args.rrf_k,
            dense_top_k=args.dense_top_k,
            lexical_top_k=args.lexical_top_k,
            source_filter=args.source,
            regulation_type_filter=args.regulation_type,
            regulation_number_filter=args.regulation_number,
            document_id_filter=doc_id,
        )
    except Exception as exc:
        logger.error("Hybrid search execution failed: %s", exc)
        sys.exit(1)

    print("\n" + "=" * 65)
    print("             HYBRID RETRIEVAL RESULTS (DENSE + BM25)")
    print("=" * 65)
    print(f" Query Text      : {args.query}")
    print(f" RRF Constant K  : {report.rrf_k}")
    print(f" Dense Candidates: {args.dense_top_k} limit")
    print(f" BM25 Candidates : {args.lexical_top_k} limit")
    print(f" Returned Results: {len(results)} matches (Top-K: {args.top_k})")
    print("-" * 65)

    for idx, r in enumerate(results, start=1):
        dense_info = (
            f"Rank {r.dense_rank} (Score {r.dense_score:.4f})"
            if r.dense_rank is not None and r.dense_score is not None
            else "None"
        )
        lex_info = (
            f"Rank {r.lexical_rank} (Score {r.lexical_score:.4f})"
            if r.lexical_rank is not None and r.lexical_score is not None
            else "None"
        )

        print(f"\n --- RESULT #{idx} [RRF: {r.fused_score:.6f} | Method: {r.retrieval_method}] ---")
        print(f" Dense Branch    : {dense_info}")
        print(f" BM25 Branch     : {lex_info}")
        print(f" Regulation      : {r.source} - {r.regulation_type} No. {r.regulation_number}")
        print(f" Path            : {r.structural_path}")
        print(f" Page            : {r.page_start} - {r.page_end}")
        print(f" Chunk ID        : {r.chunk_id}")
        preview = r.chunk_text.replace("\n", " ")[:200]
        print(f" Text Preview:\n{preview}...")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
