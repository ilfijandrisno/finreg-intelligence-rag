"""Live smoke test script for testing ingestion against official BI & OJK portals."""

import argparse
import time

from finreg.ingestion.adapters.bi_adapter import BankIndonesiaAdapter
from finreg.ingestion.adapters.ojk_adapter import OjkAdapter
from finreg.ingestion.service import IngestionService
from finreg.observability.logging import setup_logging

logger = setup_logging()


def main() -> None:
    """Execute live smoke test against Bank Indonesia and Otoritas Jasa Keuangan portals."""
    parser = argparse.ArgumentParser(description="FinReg Intelligence — Ingestion Live Smoke Test")
    parser.add_argument(
        "--source",
        choices=["bi", "ojk", "all"],
        default="all",
        help="Target source for smoke test ('bi', 'ojk', or 'all')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2,
        help="Configurable document limit for smoke test (default: 2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute discovery and metadata parsing without downloading raw PDFs or mutating DB",
    )

    args = parser.parse_args()

    service = IngestionService()
    adapters = []

    if args.source in ("bi", "all"):
        adapters.append(BankIndonesiaAdapter())
    if args.source in ("ojk", "all"):
        adapters.append(OjkAdapter())

    logger.info(
        "Starting Live Smoke Test for %d adapter(s) (Limit: %d, Dry-Run: %s)...",
        len(adapters),
        args.limit,
        args.dry_run,
    )

    for adapter in adapters:
        print(
            f"\n>>> Running Smoke Test for {adapter.source_name} "
            f"({adapter.target_regulation_type})..."
        )

        # Run 1: Initial Ingestion Run
        summary_1 = service.run_ingestion(adapter=adapter, limit=args.limit, dry_run=args.dry_run)

        print("\n--------------------------------------------------")
        print(f" SMOKE TEST RUN 1 RESULT — {summary_1.source}")
        print("--------------------------------------------------")
        print(f" Discovered Regulations  : {summary_1.discovered}")
        print(f" Metadata Parsed        : {summary_1.metadata_parsed}")
        print(f" Attachments Resolved   : {summary_1.documents_found}")
        print(f" Downloaded Files       : {summary_1.downloaded}")
        print(f" Idempotent Skipped     : {summary_1.skipped}")
        print(f" New Document Versions  : {summary_1.new_versions}")
        print(f" Ingestion Failures     : {summary_1.failed}")
        print(f" Execution Duration     : {summary_1.duration_seconds:.2f}s")
        print("--------------------------------------------------")

        if not args.dry_run and summary_1.discovered > 0:
            # Run 2: Idempotency Re-run Verification
            print(f"\n>>> Running Idempotency Re-run Verification for {adapter.source_name}...")
            time.sleep(1)
            summary_2 = service.run_ingestion(adapter=adapter, limit=args.limit, dry_run=False)

            print("\n--------------------------------------------------")
            print(f" SMOKE TEST RUN 2 RESULT (IDEMPOTENCY) — {summary_2.source}")
            print("--------------------------------------------------")
            print(f" Discovered Regulations  : {summary_2.discovered}")
            print(f" Downloaded Files       : {summary_2.downloaded}")
            print(f" Idempotent Skipped     : {summary_2.skipped}  <-- (Expect >0 if unchanged)")
            print(f" New Document Versions  : {summary_2.new_versions}")
            print(f" Execution Duration     : {summary_2.duration_seconds:.2f}s")
            print("--------------------------------------------------")


if __name__ == "__main__":
    main()
