"""Developer CLI for Phase 4B BM25 lexical search query execution."""

import argparse
import logging
import sys
from uuid import UUID

from finreg.lexical.service import LexicalRetrievalService
from finreg.observability.logging import setup_logging

logger = logging.getLogger("finreg.lexical.cli")


def main() -> None:
    """CLI entrypoint for BM25 lexical keyword search execution."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="FinReg Phase 4B — Lexical BM25 Keyword Search CLI"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query keyword string",
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

    logger.info("Executing BM25 lexical search for query: '%s'...", args.query)

    service = LexicalRetrievalService()

    try:
        results, report = service.search(
            query=args.query,
            top_k=args.top_k,
            source_filter=args.source,
            regulation_type_filter=args.regulation_type,
            regulation_number_filter=args.regulation_number,
            document_id_filter=doc_id,
        )
    except Exception as exc:
        logger.error("BM25 lexical search failed: %s", exc)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("           BM25 LEXICAL RETRIEVAL RESULTS")
    print("=" * 60)
    print(f" Query Text      : {args.query}")
    print(f" Total Indexed   : {report.total_chunks} chunks")
    print(f" Vocabulary Size : {report.vocabulary_size} terms")
    print(f" Avg Doc Length  : {report.average_doc_length} words")
    print(f" Returned        : {len(results)} matches (Top-K: {args.top_k})")
    print("-" * 60)

    for idx, r in enumerate(results, start=1):
        print(f"\n --- RESULT #{idx} [Score: {r.score:.4f} | Matched: {r.matched_terms_count}] ---")
        print(f" Regulation : {r.source} - {r.regulation_type} No. {r.regulation_number}")
        print(f" Path       : {r.structural_path}")
        print(f" Page       : {r.page_start} - {r.page_end}")
        print(f" Chunk ID   : {r.chunk_id}")
        preview = r.chunk_text.replace("\n", " ")[:200]
        print(f" Text Preview:\n{preview}...")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
