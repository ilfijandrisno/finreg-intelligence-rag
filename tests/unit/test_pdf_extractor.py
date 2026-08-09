"""Unit tests for PdfExtractor using PyMuPDF."""

import pymupdf as fitz

from finreg.documents.extractor import PdfExtractor


def create_sample_pdf_bytes() -> bytes:
    """Create in-memory PDF bytes with 2 pages for testing extractor."""
    doc = fitz.open()

    page1 = doc.new_page()
    page1.insert_text((50, 50), "PERATURAN BANK INDONESIA NOMOR 23/13/PBI/2021")
    page1.insert_text((50, 100), "BAB I KETENTUAN UMUM")
    page1.insert_text((50, 150), "Pasal 1 Dalam Peraturan ini yang dimaksud dengan:")

    page2 = doc.new_page()
    page2.insert_text((50, 50), "Pasal 2 Bank Indonesia berwenang mengatur transfer dana.")

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_extractor_from_bytes() -> None:
    """Verify PdfExtractor extracts page-aware text blocks and total page count."""
    pdf_bytes = create_sample_pdf_bytes()
    extractor = PdfExtractor()

    blocks, total_pages = extractor.extract_blocks_from_bytes(pdf_bytes)

    assert total_pages == 2
    assert len(blocks) >= 3

    # Page provenance check
    assert blocks[0].page_num == 1
    assert "PERATURAN BANK INDONESIA" in blocks[0].text
    assert blocks[-1].page_num == 2
    assert "Pasal 2" in blocks[-1].text
