"""Text normalization layer handling header/footer removal and boundary preservation."""

import logging
import re
from collections import Counter

from finreg.documents.models import ExtractedBlock, NormalizedLine

logger = logging.getLogger(__name__)

STRUCTURAL_BOUNDARY_REGEX = re.compile(
    r"^("
    r"PERATURAN\s+BANK\s+INDONESIA|"
    r"PERATURAN\s+OTORITAS\s+JASA\s+KEUANGAN|"
    r"BAB\s+[IVXLCDM]+|"
    r"Bagian\s+[A-Za-z0-9\s]+|"
    r"Paragraf\s+\d+|"
    r"Pasal\s+\d+[A-Z]?|"
    r"\(\d+\)|"
    r"[a-z]\.|\b[a-z]\)|"
    r"\d+\.|\b\d+\)|"
    r"Menimbang\s*:|"
    r"Mengingat\s*:|"
    r"MEMUTUSKAN\s*:|"
    r"MENETAPKAN\s*:|"
    r"KETENTUAN\s+PENUTUP"
    r")",
    re.IGNORECASE,
)


class TextNormalizer:
    """Normalizer for PDF text blocks ensuring header/footer removal and structural protection."""

    def is_boundary_marker(self, line_text: str) -> bool:
        """Check if line matches a recognized Indonesian legal structural boundary marker."""
        cleaned = line_text.strip()
        return bool(STRUCTURAL_BOUNDARY_REGEX.search(cleaned))

    def detect_headers_and_footers(
        self, blocks: list[ExtractedBlock], total_pages: int
    ) -> set[str]:
        """Detect repeated header and footer lines appearing on multiple pages.

        Excludes page 1 to protect legitimate regulation title headers.
        """
        if total_pages < 2:
            return set()

        line_page_counts: Counter[str] = Counter()

        for b in blocks:
            # Skip page 1 for header detection
            if b.page_num == 1:
                continue

            for line in b.lines:
                clean = line.strip()
                # Check if short line appearing at top or bottom margin
                if len(clean) < 120 and (b.bbox[1] < 80 or b.bbox[3] > 700):
                    line_page_counts[clean] += 1

        # Any line appearing on at least 2 non-first pages is classified as header/footer
        headers_footers = {text for text, count in line_page_counts.items() if count >= 2}
        logger.debug("Detected %d dynamic header/footer strings across pages", len(headers_footers))
        return headers_footers

    def normalize_blocks(
        self, blocks: list[ExtractedBlock], total_pages: int
    ) -> list[NormalizedLine]:
        """Normalize extracted blocks into structured lines while preserving structural boundaries.

        Args:
            blocks: Raw ExtractedBlock list from PdfExtractor.
            total_pages: Total PDF page count.

        Returns:
            List of NormalizedLine instances with exact page provenance.
        """
        headers_footers = self.detect_headers_and_footers(blocks, total_pages)
        normalized_lines: list[NormalizedLine] = []
        global_line_num = 0

        for b in blocks:
            for line in b.lines:
                text = line.strip()
                if not text:
                    continue

                # Skip detected dynamic header/footer lines (except page 1 title)
                if b.page_num > 1 and text in headers_footers:
                    continue

                is_boundary = self.is_boundary_marker(text)
                global_line_num += 1

                normalized_lines.append(
                    NormalizedLine(
                        text=text,
                        page_num=b.page_num,
                        line_num=global_line_num,
                        is_boundary_marker=is_boundary,
                    )
                )

        # Hyphenation repair across non-boundary lines
        repaired_lines = self._repair_hyphenation_and_wrap(normalized_lines)
        return repaired_lines

    def _repair_hyphenation_and_wrap(self, lines: list[NormalizedLine]) -> list[NormalizedLine]:
        """Repair hyphenated line breaks (e.g., 'pembangunan-' + 'an' -> 'pembangunan').

        Strictly preserves boundary markers without unwrapping across boundaries.
        """
        if not lines:
            return []

        result: list[NormalizedLine] = []
        i = 0
        n = len(lines)

        while i < n:
            curr = lines[i]

            # If current line ends with hyphen and next line is not a boundary marker
            if (
                curr.text.endswith("-")
                and len(curr.text) > 1
                and not curr.is_boundary_marker
                and i + 1 < n
                and not lines[i + 1].is_boundary_marker
            ):
                next_line = lines[i + 1]
                joined_text = curr.text[:-1] + next_line.text
                result.append(
                    NormalizedLine(
                        text=joined_text,
                        page_num=curr.page_num,
                        line_num=curr.line_num,
                        is_boundary_marker=curr.is_boundary_marker,
                    )
                )
                i += 2
                continue

            result.append(curr)
            i += 1

        return result
