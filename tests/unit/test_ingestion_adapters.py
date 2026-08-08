"""Unit tests for Bank Indonesia (BI) and OJK source adapters using HTML fixtures."""

from pathlib import Path

from finreg.ingestion.adapters.bi_adapter import BankIndonesiaAdapter
from finreg.ingestion.adapters.ojk_adapter import OjkAdapter
from finreg.ingestion.models import DocumentType, RegulationReference

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_bi_adapter_listing_parsing() -> None:
    """Verify BI listing HTML parsing extracts regulation references correctly."""
    listing_path = FIXTURES_DIR / "bi_pbi_listing.html"
    html_content = listing_path.read_text(encoding="utf-8")

    adapter = BankIndonesiaAdapter()
    refs = adapter.parse_listing_html(html_content, base_url="https://www.bi.go.id")

    assert len(refs) == 2
    assert refs[0].source == "BI"
    assert refs[0].regulation_type == "PBI"
    assert refs[0].regulation_number == "23/13/PBI/2021"
    assert "https://www.bi.go.id/id/publikasi/peraturan/Pages/PBI_231321.aspx" in refs[0].detail_url


def test_bi_adapter_detail_parsing() -> None:
    """Verify BI detail HTML parsing extracts metadata and PDF document references."""
    detail_path = FIXTURES_DIR / "bi_pbi_detail.html"
    html_content = detail_path.read_text(encoding="utf-8")

    ref = RegulationReference(
        source="BI",
        regulation_type="PBI",
        regulation_number="23/13/PBI/2021",
        title="Peraturan Bank Indonesia No. 23/13/PBI/2021 tentang Kehati-hatian Transfer Dana",
        detail_url="https://www.bi.go.id/id/publikasi/peraturan/Pages/PBI_231321.aspx",
    )

    adapter = BankIndonesiaAdapter()
    metadata, documents = adapter.parse_detail_html(html_content, ref)

    assert metadata.source == "BI"
    assert metadata.regulation_number == "23/13/PBI/2021"
    assert metadata.status == "Berlaku"
    assert metadata.published_date is not None
    assert metadata.published_date.day == 15
    assert metadata.published_date.month == 12
    assert metadata.published_date.year == 2021

    assert len(documents) == 2
    assert documents[0].document_type == DocumentType.REGULATION
    assert "PBI_231321.pdf" in documents[0].url
    assert documents[1].document_type == DocumentType.FAQ


def test_ojk_adapter_listing_parsing() -> None:
    """Verify OJK listing HTML parsing extracts regulation references correctly."""
    listing_path = FIXTURES_DIR / "ojk_pojk_listing.html"
    html_content = listing_path.read_text(encoding="utf-8")

    adapter = OjkAdapter()
    refs = adapter.parse_listing_html(html_content, base_url="https://www.ojk.go.id")

    assert len(refs) == 2
    assert refs[0].source == "OJK"
    assert refs[0].regulation_type == "POJK"
    assert refs[0].regulation_number == "12/POJK.03/2020"
    assert "https://www.ojk.go.id/id/regulasi/Pages/POJK-12-2020.aspx" in refs[0].detail_url


def test_ojk_adapter_detail_parsing() -> None:
    """Verify OJK detail HTML parsing extracts metadata and attachment references."""
    detail_path = FIXTURES_DIR / "ojk_pojk_detail.html"
    html_content = detail_path.read_text(encoding="utf-8")

    ref = RegulationReference(
        source="OJK",
        regulation_type="POJK",
        regulation_number="12/POJK.03/2020",
        title="Peraturan OJK Nomor 12/POJK.03/2020 tentang Konsolidasi Bank Umum",
        detail_url="https://www.ojk.go.id/id/regulasi/Pages/POJK-12-2020.aspx",
    )

    adapter = OjkAdapter()
    metadata, documents = adapter.parse_detail_html(html_content, ref)

    assert metadata.source == "OJK"
    assert metadata.regulation_number == "12/POJK.03/2020"
    assert metadata.status == "Berlaku"
    assert metadata.sector == "Perbankan"

    assert len(documents) == 1
    assert documents[0].document_type == DocumentType.REGULATION
    assert "POJK-12-2020.pdf" in documents[0].url
