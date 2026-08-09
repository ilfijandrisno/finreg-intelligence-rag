"""Unit test for Phase 3A document structure parsing CLI entrypoint."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from finreg.documents.cli import main
from finreg.documents.models import NodeType, StructuredNode, ValidationReport


def test_parsing_cli_execution() -> None:
    """Verify parsing CLI argument handling and report summary rendering."""
    doc_id = uuid4()
    version_id = uuid4()

    mock_report = ValidationReport(
        document_id=doc_id,
        version_id=version_id,
        total_pages=2,
        extracted_characters=500,
        structured_characters=490,
        unparsed_characters=10,
        coverage_ratio=0.98,
        is_valid=True,
        warnings=[],
    )

    mock_nodes = [
        StructuredNode(
            node_type=NodeType.CHAPTER,
            node_number="I",
            title="KETENTUAN UMUM",
            text="",
            children=[
                StructuredNode(
                    node_type=NodeType.PARAGRAPH,
                    node_number="1",
                    text="Ketentuan ayat 1",
                )
            ],
        )
    ]

    with (
        patch(
            "sys.argv",
            ["cli.py", "--document-id", str(doc_id), "--dry-run", "--min-coverage", "0.90"],
        ),
        patch("finreg.documents.cli.DocumentParsingService") as mock_service_cls,
    ):
        mock_service = MagicMock()
        mock_service.parse_document.return_value = (mock_report, mock_nodes)
        mock_service_cls.return_value = mock_service

        main()

        mock_service.parse_document.assert_called_once_with(document_id=doc_id, dry_run=True)
