"""Developer CLI for Phase 3B semantic legal chunking execution and dry-run reporting."""

import argparse
import logging
import sys
from collections import Counter
from uuid import UUID

from finreg.documents.chunk_service import DocumentChunkingService
from finreg.observability.logging import setup_logging

logger = logging.getLogger("finreg.documents.chunk_cli")


def main() -> None:
    """CLI entrypoint for semantic legal document chunking."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="FinReg Phase 3B — Semantic Legal Document Chunker CLI"
    )
    parser.add_argument(
        "--document-id",
        type=str,
        required=True,
        help="UUID string of target regulation document to chunk",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run chunking in-memory and display report without database mutations",
    )

    args = parser.parse_args()

    try:
        doc_id = UUID(args.document_id)
    except ValueError:
        logger.error("Invalid UUID format: %s", args.document_id)
        sys.exit(1)

    logger.info(
        "Executing semantic chunking for Document %s (Dry-Run: %s)...",
        doc_id,
        args.dry_run,
    )

    service = DocumentChunkingService()

    try:
        report, chunks = service.chunk_document(document_id=doc_id, dry_run=args.dry_run)
    except Exception as exc:
        logger.error("Chunking failed for Document %s: %s", doc_id, exc)
        sys.exit(1)

    # Print summary report
    print("\n" + "=" * 50)
    print("       DOCUMENT SEMANTIC CHUNKING REPORT")
    print("=" * 50)
    print(f" Document ID          : {report.document_id}")
    print(f" Version ID           : {report.version_id}")
    print(f" Total Chunks         : {report.total_chunks}")
    print(f" Leaf Source Chars    : {report.leaf_source_characters}")
    print(f" Chunked Chars        : {report.chunked_characters}")
    print(f" Source Coverage      : {report.source_text_coverage * 100:.2f}%")
    print(
        f" Min / Max / Avg Size : {report.min_chunk_size} / "
        f"{report.max_chunk_size} / {report.avg_chunk_size:.1f} chars"
    )
    status_str = "VALID / SUCCESS" if report.is_valid else "INVALID / FAILED"
    if args.dry_run:
        status_str += " (DRY-RUN)"
    print(f" Status               : {status_str}")
    print("-" * 50)

    # Breakdown by structural path prefix
    type_counts: Counter[str] = Counter()
    for c in chunks:
        last_seg = c.structural_path.split("/")[-1].split("[")[0].strip()
        type_counts[last_seg] += 1

    print(" Chunk Count Breakdown by Primary Node:")
    for node_name, count in sorted(type_counts.items()):
        print(f"   - {node_name:<20}: {count}")

    print("-" * 50)
    print(" Sample Chunks (First 3):")
    for idx, c in enumerate(chunks[:3], start=1):
        print(f"\n --- CHUNK {idx} [Seq: {c.sequence} | Part {c.part_index}/{c.total_parts}] ---")
        print(f" Path: {c.structural_path}")
        print(f" Hash: {c.chunk_hash[:16]}...")
        print(f" Contextual Text Preview:\n{c.contextual_text[:300]}...")

    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
