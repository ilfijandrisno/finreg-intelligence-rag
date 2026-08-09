"""Unit tests for TextNormalizer header removal, hyphenation repair, and boundary protection."""

from finreg.documents.models import ExtractedBlock, NormalizedLine
from finreg.documents.normalizer import TextNormalizer


def test_boundary_marker_detection() -> None:
    """Verify structural boundary marker detection logic."""
    normalizer = TextNormalizer()

    assert normalizer.is_boundary_marker("BAB I") is True
    assert normalizer.is_boundary_marker("Bagian Kesatu") is True
    assert normalizer.is_boundary_marker("Pasal 12A") is True
    assert normalizer.is_boundary_marker("(1) Dalam hal ini...") is True
    assert normalizer.is_boundary_marker("a. Surat Berharga") is True
    assert normalizer.is_boundary_marker("Menimbang:") is True
    assert normalizer.is_boundary_marker("Mengingat:") is True

    assert normalizer.is_boundary_marker("Ini adalah teks paragraf biasa.") is False


def test_dynamic_header_footer_removal() -> None:
    """Verify dynamic detection and removal of repeated header/footer text across pages."""
    normalizer = TextNormalizer()

    blocks = [
        ExtractedBlock(
            page_num=1,
            block_num=0,
            bbox=(50, 50, 500, 70),
            lines=["PERATURAN BANK INDONESIA NOMOR 23/13/PBI/2021"],
            text="PERATURAN BANK INDONESIA NOMOR 23/13/PBI/2021",
        ),
        ExtractedBlock(
            page_num=2,
            block_num=0,
            bbox=(50, 30, 500, 45),
            lines=["www.bi.go.id - Peraturan BI"],
            text="www.bi.go.id - Peraturan BI",
        ),
        ExtractedBlock(
            page_num=2,
            block_num=1,
            bbox=(50, 100, 500, 200),
            lines=["Pasal 2 Bank Indonesia berwenang."],
            text="Pasal 2 Bank Indonesia berwenang.",
        ),
        ExtractedBlock(
            page_num=3,
            block_num=0,
            bbox=(50, 30, 500, 45),
            lines=["www.bi.go.id - Peraturan BI"],
            text="www.bi.go.id - Peraturan BI",
        ),
        ExtractedBlock(
            page_num=3,
            block_num=1,
            bbox=(50, 100, 500, 200),
            lines=["Pasal 3 Penyelenggaraan transfer dana."],
            text="Pasal 3 Penyelenggaraan transfer dana.",
        ),
    ]

    headers = normalizer.detect_headers_and_footers(blocks, total_pages=3)
    assert "www.bi.go.id - Peraturan BI" in headers

    normalized = normalizer.normalize_blocks(blocks, total_pages=3)
    texts = [line.text for line in normalized]

    assert "www.bi.go.id - Peraturan BI" not in texts
    assert "PERATURAN BANK INDONESIA NOMOR 23/13/PBI/2021" in texts
    assert "Pasal 2 Bank Indonesia berwenang." in texts


def test_hyphenation_repair_and_boundary_protection() -> None:
    """Verify hyphenation repair joins split words without merging across structural boundaries."""
    normalizer = TextNormalizer()

    lines = [
        NormalizedLine(text="Penyelenggara wajib melakukan pem-", page_num=1, line_num=1),
        NormalizedLine(text="bangunan sistem pembayaran.", page_num=1, line_num=2),
        NormalizedLine(text="Pasal 2", page_num=1, line_num=3, is_boundary_marker=True),
        NormalizedLine(text="(1)", page_num=1, line_num=4, is_boundary_marker=True),
    ]

    repaired = normalizer._repair_hyphenation_and_wrap(lines)
    texts = [line.text for line in repaired]

    assert "Penyelenggara wajib melakukan pembangunan sistem pembayaran." in texts
    assert "Pasal 2" in texts
    assert "(1)" in texts
