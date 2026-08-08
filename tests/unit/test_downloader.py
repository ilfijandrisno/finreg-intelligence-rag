"""Unit tests for DownloadManager and SHA-256 checksumming."""

import hashlib

from finreg.ingestion.downloader import (
    PERMANENT_HTTP_STATUSES,
    TRANSIENT_HTTP_STATUSES,
    DownloadManager,
)


def test_sha256_checksum_calculation() -> None:
    """Verify deterministic SHA-256 checksum computation for raw bytes."""
    manager = DownloadManager()
    sample_content = b"%PDF-1.4 sample regulation pdf document payload"

    expected_hash = hashlib.sha256(sample_content).hexdigest()
    calculated_hash = manager.calculate_sha256(sample_content)

    assert calculated_hash == expected_hash
    assert len(calculated_hash) == 64


def test_pdf_magic_byte_validation() -> None:
    """Verify PDF magic byte detection (%PDF)."""
    manager = DownloadManager()

    valid_pdf_content = b"%PDF-1.7 header content..."
    invalid_content = b"<html><body>Not a PDF</body></html>"

    assert manager.is_valid_pdf(valid_pdf_content) is True
    assert manager.is_valid_pdf(invalid_content) is False


def test_http_status_classification() -> None:
    """Verify transient vs permanent status code classification."""
    assert 500 in TRANSIENT_HTTP_STATUSES
    assert 503 in TRANSIENT_HTTP_STATUSES
    assert 429 in TRANSIENT_HTTP_STATUSES

    assert 404 in PERMANENT_HTTP_STATUSES
    assert 403 in PERMANENT_HTTP_STATUSES
    assert 401 in PERMANENT_HTTP_STATUSES
