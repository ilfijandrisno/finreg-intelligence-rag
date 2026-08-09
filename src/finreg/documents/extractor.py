"""PyMuPDF text block extraction layer for regulatory PDF documents."""

import logging
from pathlib import Path

import pymupdf as fitz  # PyMuPDF

from finreg.documents.models import ExtractedBlock

logger = logging.getLogger(__name__)


class PdfExtractor:
    """Extractor leveraging PyMuPDF for page-aware text block extraction."""

    def extract_blocks_from_file(self, pdf_path: str | Path) -> tuple[list[ExtractedBlock], int]:
        """Extract page-by-page text blocks from a local PDF file path.

        Returns:
            (extracted_blocks, total_pages)
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found at {path}")

        doc = fitz.open(str(path))
        return self._extract_blocks_from_doc(doc)

    def extract_blocks_from_bytes(self, pdf_bytes: bytes) -> tuple[list[ExtractedBlock], int]:
        """Extract page-by-page text blocks from raw PDF bytes.

        Returns:
            (extracted_blocks, total_pages)
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return self._extract_blocks_from_doc(doc)

    def _extract_blocks_from_doc(self, doc: fitz.Document) -> tuple[list[ExtractedBlock], int]:
        """Iterate pages and extract structured text blocks retaining page numbers and bboxes."""
        total_pages = len(doc)
        extracted_blocks: list[ExtractedBlock] = []

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]
            blocks = page.get_text("blocks")

            for block_idx, b in enumerate(blocks):
                # b format: (x0, y0, x1, y1, "text_content", block_no, block_type)
                # block_type 0 is text, 1 is image
                if len(b) >= 7 and b[6] != 0:
                    continue

                bbox = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
                raw_text = str(b[4]).strip()
                if not raw_text:
                    continue

                lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
                extracted_blocks.append(
                    ExtractedBlock(
                        page_num=page_num,
                        block_num=block_idx,
                        bbox=bbox,
                        lines=lines,
                        text=raw_text,
                    )
                )

        doc.close()
        logger.info("Extracted %d blocks across %d pages", len(extracted_blocks), total_pages)
        return extracted_blocks, total_pages
