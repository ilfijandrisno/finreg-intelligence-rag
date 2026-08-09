"""Command-line interface (CLI) for running regulatory document structure parsing."""

import argparse
from collections import Counter
from uuid import UUID

from finreg.config.settings import get_settings
from finreg.documents.service import DocumentParsingService
from finreg.observability.logging import setup_logging

logger = setup_logging()


def main() -> None:
    """CLI entrypoint for executing document structure parsing."""
    parser = argparse.ArgumentParser(
        description="FinReg Intelligence — Document Structure Parsing CLI"
    )
    parser.add_argument(
        "--document-id",
        required=True,
        type=UUID,
        help="Target regulation document UUID to parse",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute parsing and validation without writing document_nodes to database",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=get_settings().parsing_min_coverage_ratio,
        help="Minimum acceptable character coverage ratio threshold (e.g. 0.90)",
    )

    args = parser.parse_args()

    service = DocumentParsingService()
    service.validator.min_coverage_ratio = args.min_coverage

    logger.info("Executing structure parsing for Document %s...", args.document_id)

    report, nodes = service.parse_document(document_id=args.document_id, dry_run=args.dry_run)

    node_type_counts: Counter[str] = Counter()

    def count_nodes(node_list: list) -> None:
        for n in node_list:
            node_type_counts[n.node_type.value] += 1
            if n.children:
                count_nodes(n.children)

    count_nodes(nodes)

    print("\n==================================================")
    print("       DOCUMENT STRUCTURE PARSING REPORT")
    print("==================================================")
    print(f" Document ID          : {report.document_id}")
    print(f" Version ID           : {report.version_id}")
    print(f" Total PDF Pages      : {report.total_pages}")
    print(f" Extracted Chars      : {report.extracted_characters}")
    print(f" Structured Chars     : {report.structured_characters}")
    print(f" Unparsed Chars       : {report.unparsed_characters}")
    print(f" Coverage Ratio       : {report.coverage_ratio * 100:.2f}%")
    print(f" Status               : {'VALID / SUCCESS' if report.is_valid else 'FAILED'}")
    print("--------------------------------------------------")
    print(" Node Breakdown by Type:")
    for ntype, cnt in sorted(node_type_counts.items()):
        print(f"   - {ntype:<20} : {cnt}")
    print("--------------------------------------------------")
    if report.warnings:
        print(" Warnings:")
        for w in report.warnings:
            print(f"   ! {w}")
    print("==================================================\n")


if __name__ == "__main__":
    main()
