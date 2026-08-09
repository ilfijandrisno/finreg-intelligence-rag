"""Command-line interface (CLI) for running regulatory data ingestion."""

import argparse

from finreg.config.settings import get_settings
from finreg.ingestion.adapters.bi_adapter import BankIndonesiaAdapter
from finreg.ingestion.adapters.ojk_adapter import OjkAdapter
from finreg.ingestion.protocols import RegulatorySourceAdapter
from finreg.ingestion.service import IngestionService
from finreg.observability.logging import setup_logging

logger = setup_logging()


def main() -> None:
    """CLI entrypoint for executing regulatory ingestion."""
    parser = argparse.ArgumentParser(
        description="FinReg Intelligence — Regulatory Data Ingestion CLI"
    )
    parser.add_argument(
        "--source",
        choices=["bi", "ojk", "all"],
        default="all",
        help="Target regulatory data source adapter to ingest (bi, ojk, or all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=get_settings().max_discovered_documents,
        help="Maximum document count limit to discover",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute discovery without downloading PDFs or writing to database",
    )

    args = parser.parse_args()

    service = IngestionService()
    adapters: list[RegulatorySourceAdapter] = []

    if args.source in ("bi", "all"):
        adapters.append(BankIndonesiaAdapter())
    if args.source in ("ojk", "all"):
        adapters.append(OjkAdapter())

    logger.info("Executing ingestion for %d adapter(s)...", len(adapters))

    for adapter in adapters:
        summary = service.run_ingestion(adapter=adapter, limit=args.limit, dry_run=args.dry_run)

        print("\n==================================================")
        print(f"       INGESTION SUMMARY — {summary.source}")
        print("==================================================")
        print(f" Discovered Regulations  : {summary.discovered}")
        print(f" Metadata Parsed        : {summary.metadata_parsed}")
        print(f" Attachments Resolved   : {summary.documents_found}")
        print(f" Downloaded Files       : {summary.downloaded}")
        print(f" Idempotent Skipped     : {summary.skipped}")
        print(f" New Document Versions  : {summary.new_versions}")
        print(f" Ingestion Failures     : {summary.failed}")
        print(f" Execution Duration     : {summary.duration_seconds:.2f}s")
        print("==================================================\n")


if __name__ == "__main__":
    main()
