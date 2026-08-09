"""Developer CLI for Phase 4A document vector embedding generation and dry-run reporting."""

import argparse
import logging
import sys
from uuid import UUID

from finreg.observability.logging import setup_logging
from finreg.vector.service import DocumentEmbeddingService

logger = logging.getLogger("finreg.vector.cli")


def main() -> None:
    """CLI entrypoint for document chunk vector embedding generation."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="FinReg Phase 4A — Vector Embedding Generation CLI"
    )
    parser.add_argument(
        "--document-id",
        type=str,
        required=True,
        help="UUID string of target regulation document to embed",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate embeddings in-memory and display report without database persistence",
    )

    args = parser.parse_args()

    try:
        doc_id = UUID(args.document_id)
    except ValueError:
        logger.error("Invalid UUID format: %s", args.document_id)
        sys.exit(1)

    logger.info(
        "Executing vector embedding generation for Document %s (Dry-Run: %s)...",
        doc_id,
        args.dry_run,
    )

    service = DocumentEmbeddingService()

    try:
        report, _ = service.embed_document(document_id=doc_id, dry_run=args.dry_run)
    except Exception as exc:
        logger.error("Embedding generation failed for Document %s: %s", doc_id, exc)
        sys.exit(1)

    print("\n" + "=" * 50)
    print("       DOCUMENT VECTOR EMBEDDING REPORT")
    print("=" * 50)
    print(f" Document ID          : {report.document_id}")
    print(f" Version ID           : {report.version_id}")
    print(f" Embedding Model      : {report.embedding_model}")
    print(f" Target Dimension     : {report.dimension}")
    print(f" Chunks Embedded      : {report.chunks_embedded}")
    print(f" Vectors Persisted    : {report.total_vectors_persisted}")
    status_str = "VALID / SUCCESS" if report.is_valid else "INVALID / FAILED"
    if args.dry_run:
        status_str += " (DRY-RUN)"
    print(f" Status               : {status_str}")
    if report.warnings:
        print("-" * 50)
        print(" Warnings:")
        for w in report.warnings:
            print(f"   - {w}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
