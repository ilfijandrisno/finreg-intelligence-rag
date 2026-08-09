"""Developer CLI for Phase 6 Grounded LLM Generation and RAG Answer Assembly."""

import argparse
import logging
import sys
from uuid import UUID

from finreg.observability.logging import setup_logging
from finreg.rag.providers import MockLLMProvider, OpenAILLMProvider
from finreg.rag.service import RAGService

logger = logging.getLogger("finreg.rag.cli")


def main() -> None:
    """CLI entrypoint for Phase 6 RAG Answer Generation execution."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="FinReg Phase 6 — Grounded LLM Answer Generation CLI"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="User query text string",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Top-N reranked context limit (default: 5)",
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
        help="Use MockLLMProvider instead of OpenAILLMProvider (for offline testing)",
    )

    args = parser.parse_args()

    doc_id: UUID | None = None
    if args.document_id:
        try:
            doc_id = UUID(args.document_id)
        except ValueError:
            logger.error("Invalid UUID format for --document-id: %s", args.document_id)
            sys.exit(1)

    llm_provider = MockLLMProvider() if args.use_mock else OpenAILLMProvider()
    logger.info("Executing Phase 6 RAG Generation via '%s'...", llm_provider.provider_name)

    service = RAGService(llm_provider=llm_provider)

    try:
        result = service.search_and_generate(
            query=args.query,
            top_n=args.top_n,
            source_filter=args.source,
            regulation_type_filter=args.regulation_type,
            regulation_number_filter=args.regulation_number,
            document_id_filter=doc_id,
        )
    except Exception as exc:
        logger.error("RAG Answer Generation execution failed: %s", exc)
        sys.exit(1)

    rep = result.execution_report

    print("\n" + "=" * 68)
    print("         PHASE 6 GROUNDED LLM GENERATION RESULTS")
    print("=" * 68)
    print(f" Query Text      : {result.query}")
    print(f" LLM Provider    : {rep.provider_name} ({rep.model_name})")
    print(f" Context Blocks  : {rep.context_blocks_count} chunks")
    print(f" Input Tokens    : ~{rep.estimated_input_tokens}")
    print(f" Abstained       : {result.abstained}")
    if result.abstained:
        print(f" Abstention Cause: {result.abstention_reason}")
    print(f" Legal Conflict  : {result.has_legal_conflict}")
    print(f" Execution Time  : {rep.execution_time_ms:.2f} ms")
    print("-" * 68)

    print(f"\n GENERATED ANSWER:\n{result.answer}\n")
    print("-" * 68)

    print(" VALIDATED LEGAL PROVENANCE CITATIONS:")
    if result.citations:
        for idx, cit in enumerate(result.citations, start=1):
            print(f"  {idx}. [{cit.context_id}] {cit.format_display_string()}")
            print(f"      Chunk ID: {cit.chunk_id}")
    else:
        print("  (No legal citations applicable)")

    print("=" * 68 + "\n")


if __name__ == "__main__":
    main()
