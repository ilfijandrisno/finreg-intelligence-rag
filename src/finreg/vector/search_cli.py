"""Developer CLI for Phase 4A pgvector similarity search query execution."""

import argparse
import logging
import sys

from finreg.observability.logging import setup_logging
from finreg.vector.search_service import VectorSearchService

logger = logging.getLogger("finreg.vector.search_cli")


def main() -> None:
    """CLI entrypoint for dense vector similarity search execution."""
    setup_logging()

    parser = argparse.ArgumentParser(description="FinReg Phase 4A — Vector Similarity Search CLI")
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
        help="Maximum top-K similarity search results limit (default: 5)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Optional filter by regulatory authority source (e.g. 'BI', 'OJK')",
    )

    args = parser.parse_args()

    logger.info("Executing pgvector similarity search for query: '%s'...", args.query)

    service = VectorSearchService()

    try:
        results = service.search(
            query=args.query,
            top_k=args.top_k,
            source_filter=args.source,
        )
    except Exception as exc:
        logger.error("Vector search failed: %s", exc)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("           PGVECTOR DENSE RETRIEVAL RESULTS")
    print("=" * 60)
    print(f" Query Text : {args.query}")
    print(f" Returned   : {len(results)} matches (Top-K: {args.top_k})")
    print("-" * 60)

    for idx, r in enumerate(results, start=1):
        print(f"\n --- RESULT #{idx} [Score: {r.score:.4f} | Dist: {r.distance:.4f}] ---")
        print(
            f" Regulation : {r.source} - {r.regulation_type} No. {r.regulation_number} ({r.title})"
        )
        print(f" Path       : {r.structural_path}")
        print(f" Page       : {r.page_start} - {r.page_end}")
        print(f" Chunk ID   : {r.chunk_id}")
        print(f" Text Preview:\n{r.chunk_text[:250]}...")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
