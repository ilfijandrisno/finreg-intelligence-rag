"""Context-aware state-machine parser for Indonesian financial regulations (BI PBI and OJK POJK)."""

import logging
import re

from finreg.documents.models import (
    NodeType,
    NormalizedLine,
    StructuredNode,
)

logger = logging.getLogger(__name__)

# Regular Expressions for Indonesian Legal Structure Markers
RE_BAB = re.compile(r"^BAB\s+([IVXLCDM]+)", re.IGNORECASE)
RE_BAGIAN = re.compile(r"^Bagian\s+([A-Za-z0-9\s]+)", re.IGNORECASE)
RE_PARAGRAF = re.compile(r"^Paragraf\s+(\d+)", re.IGNORECASE)
RE_PASAL = re.compile(r"^Pasal\s+(\d+[A-Z]?)", re.IGNORECASE)
RE_AYAT = re.compile(r"^\((\d+)\)\s*(.*)", re.IGNORECASE)
RE_HURUF = re.compile(r"^([a-z])[\.\)]\s*(.*)", re.IGNORECASE)
RE_NUMBERED = re.compile(r"^(\d+)[\.\)]\s*(.*)", re.IGNORECASE)

RE_MENIMBANG = re.compile(r"^Menimbang\s*:\s*(.*)", re.IGNORECASE)
RE_MENGINGAT = re.compile(r"^Mengingat\s*:\s*(.*)", re.IGNORECASE)
RE_MEMUTUSKAN = re.compile(r"^(MEMUTUSKAN|MENETAPKAN)\s*:\s*(.*)", re.IGNORECASE)
RE_CLOSING = re.compile(
    r"^(PASAL\s+PENUTUP|Agar\s+setiap\s+orang\s+mengetahuinya|Disahkan\s+di|Ditetapkan\s+di)",
    re.IGNORECASE,
)


class RegulatoryStructureParser:
    """Context-aware structural parser building hierarchical node trees from normalized lines."""

    def parse(self, lines: list[NormalizedLine]) -> list[StructuredNode]:
        """Parse normalized lines into a list of top-level StructuredNode roots.

        Returns:
            List of root StructuredNode instances forming the document tree hierarchy.
        """
        if not lines:
            return []

        root_nodes: list[StructuredNode] = []
        sequence_counter = 0

        current_chapter: StructuredNode | None = None
        current_part: StructuredNode | None = None
        current_section: StructuredNode | None = None
        current_article: StructuredNode | None = None
        current_paragraph: StructuredNode | None = None
        current_letter: StructuredNode | None = None

        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            text = line.text.strip()
            page_num = line.page_num

            # 1. BAB (Chapter)
            bab_match = RE_BAB.match(text)
            if bab_match:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                bab_num = bab_match.group(1).upper()

                title_parts: list[str] = []
                while i + 1 < n and not self._is_any_marker(lines[i + 1].text):
                    title_parts.append(lines[i + 1].text.strip())
                    i += 1

                title = " ".join(title_parts) if title_parts else f"BAB {bab_num}"

                current_chapter = StructuredNode(
                    node_type=NodeType.CHAPTER,
                    node_number=bab_num,
                    title=title,
                    text="",
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path=f"BAB {bab_num}",
                )
                root_nodes.append(current_chapter)
                current_part = None
                current_section = None
                current_article = None
                current_paragraph = None
                current_letter = None
                i += 1
                continue

            # 2. Bagian (Part)
            bagian_match = RE_BAGIAN.match(text)
            if bagian_match:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                part_num = bagian_match.group(1).strip()

                title_parts = []
                while i + 1 < n and not self._is_any_marker(lines[i + 1].text):
                    title_parts.append(lines[i + 1].text.strip())
                    i += 1

                title = " ".join(title_parts) if title_parts else f"Bagian {part_num}"

                parent_path = current_chapter.path if current_chapter else ""
                part_path = (
                    f"{parent_path}/Bagian {part_num}" if parent_path else f"Bagian {part_num}"
                )

                current_part = StructuredNode(
                    node_type=NodeType.PART,
                    node_number=part_num,
                    title=title,
                    text="",
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path=part_path,
                )
                if current_chapter:
                    current_chapter.children.append(current_part)
                else:
                    root_nodes.append(current_part)

                current_section = None
                current_article = None
                current_paragraph = None
                current_letter = None
                i += 1
                continue

            # 3. Paragraf (Section)
            paragraf_match = RE_PARAGRAF.match(text)
            if paragraf_match:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                sec_num = paragraf_match.group(1).strip()

                title_parts = []
                while i + 1 < n and not self._is_any_marker(lines[i + 1].text):
                    title_parts.append(lines[i + 1].text.strip())
                    i += 1

                title = " ".join(title_parts) if title_parts else f"Paragraf {sec_num}"

                parent_path = (
                    current_part.path
                    if current_part
                    else (current_chapter.path if current_chapter else "")
                )
                sec_path = (
                    f"{parent_path}/Paragraf {sec_num}" if parent_path else f"Paragraf {sec_num}"
                )

                current_section = StructuredNode(
                    node_type=NodeType.SECTION,
                    node_number=sec_num,
                    title=title,
                    text="",
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path=sec_path,
                )
                if current_part:
                    current_part.children.append(current_section)
                elif current_chapter:
                    current_chapter.children.append(current_section)
                else:
                    root_nodes.append(current_section)

                current_article = None
                current_paragraph = None
                current_letter = None
                i += 1
                continue

            # 4. Pasal (Article)
            pasal_match = RE_PASAL.match(text)
            if pasal_match:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                article_num = pasal_match.group(1).upper()

                parent_path = (
                    current_section.path
                    if current_section
                    else (
                        current_part.path
                        if current_part
                        else (current_chapter.path if current_chapter else "")
                    )
                )
                art_path = (
                    f"{parent_path}/Pasal {article_num}" if parent_path else f"Pasal {article_num}"
                )

                current_article = StructuredNode(
                    node_type=NodeType.ARTICLE,
                    node_number=article_num,
                    title=None,
                    text="",
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path=art_path,
                )
                if current_section:
                    current_section.children.append(current_article)
                elif current_part:
                    current_part.children.append(current_article)
                elif current_chapter:
                    current_chapter.children.append(current_article)
                else:
                    root_nodes.append(current_article)

                current_paragraph = None
                current_letter = None
                i += 1
                continue

            # 5. Ayat (Paragraph under Article)
            ayat_match = RE_AYAT.match(text)
            if ayat_match and current_article:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                ayat_num = ayat_match.group(1)
                ayat_text = ayat_match.group(2).strip()

                para_path = f"{current_article.path}/Ayat ({ayat_num})"
                current_paragraph = StructuredNode(
                    node_type=NodeType.PARAGRAPH,
                    node_number=ayat_num,
                    title=None,
                    text=ayat_text,
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path=para_path,
                )
                current_article.children.append(current_paragraph)
                current_letter = None
                i += 1
                continue

            # 6. Huruf (Letter under Paragraph or Article)
            huruf_match = RE_HURUF.match(text)
            if huruf_match and (current_paragraph or current_article):
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                letter_code = huruf_match.group(1).lower()
                letter_text = huruf_match.group(2).strip()

                parent = current_paragraph or current_article
                letter_path = (
                    f"{parent.path}/Huruf {letter_code}" if parent else f"Huruf {letter_code}"
                )

                current_letter = StructuredNode(
                    node_type=NodeType.LETTER,
                    node_number=letter_code,
                    title=None,
                    text=letter_text,
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path=letter_path,
                )
                if parent:
                    parent.children.append(current_letter)
                else:
                    root_nodes.append(current_letter)
                i += 1
                continue

            # 7. Numbered List Item under Huruf, Paragraph, or Article
            num_match = RE_NUMBERED.match(text)
            if num_match and (current_letter or current_paragraph or current_article):
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                num_code = num_match.group(1)
                num_text = num_match.group(2).strip()

                parent = current_letter or current_paragraph or current_article
                num_path = f"{parent.path}/{num_code}." if parent else f"{num_code}."

                num_node = StructuredNode(
                    node_type=NodeType.NUMBERED_ITEM,
                    node_number=num_code,
                    title=None,
                    text=num_text,
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path=num_path,
                )
                if parent:
                    parent.children.append(num_node)
                else:
                    root_nodes.append(num_node)
                i += 1
                continue

            # 8. Menimbang (Considerations)
            menimbang_match = RE_MENIMBANG.match(text)
            if menimbang_match:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                body = menimbang_match.group(1).strip()
                node = StructuredNode(
                    node_type=NodeType.CONSIDERATION,
                    node_number=None,
                    title="Menimbang",
                    text=body,
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path="Menimbang",
                )
                root_nodes.append(node)
                i += 1
                continue

            # 9. Mengingat (Legal Basis)
            mengingat_match = RE_MENGINGAT.match(text)
            if mengingat_match:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                body = mengingat_match.group(1).strip()
                node = StructuredNode(
                    node_type=NodeType.LEGAL_BASIS,
                    node_number=None,
                    title="Mengingat",
                    text=body,
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path="Mengingat",
                )
                root_nodes.append(node)
                i += 1
                continue

            # 10. Memutuskan / Menetapkan (Decision)
            memutuskan_match = RE_MEMUTUSKAN.match(text)
            if memutuskan_match:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                body = memutuskan_match.group(2).strip()
                node = StructuredNode(
                    node_type=NodeType.DECISION,
                    node_number=None,
                    title="MEMUTUSKAN:",
                    text=body,
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path="MEMUTUSKAN",
                )
                root_nodes.append(node)
                i += 1
                continue

            # 11. Closing Provisions
            closing_match = RE_CLOSING.match(text)
            if closing_match:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                node = StructuredNode(
                    node_type=NodeType.CLOSING,
                    node_number=None,
                    title="KETENTUAN PENUTUP",
                    text=text,
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path="KETENTUAN PENUTUP",
                )
                root_nodes.append(node)
                i += 1
                continue

            # Default / Preamble / Implicit Paragraph handling
            if not root_nodes:
                seq = self._next_seq(sequence_counter)
                sequence_counter = seq
                preamble_node = StructuredNode(
                    node_type=NodeType.PREAMBLE,
                    node_number=None,
                    title=text,
                    text=text,
                    page_start=page_num,
                    page_end=page_num,
                    sequence=seq,
                    path="PREAMBLE",
                )
                root_nodes.append(preamble_node)
            else:
                if current_article and not current_paragraph and not current_letter:
                    seq = self._next_seq(sequence_counter)
                    sequence_counter = seq
                    current_paragraph = StructuredNode(
                        node_type=NodeType.PARAGRAPH,
                        node_number=None,
                        title=None,
                        text=text,
                        page_start=page_num,
                        page_end=page_num,
                        sequence=seq,
                        path=f"{current_article.path}/Ayat (1)",
                    )
                    current_article.children.append(current_paragraph)
                else:
                    last_target = current_letter or current_paragraph or root_nodes[-1]
                    if last_target:
                        last_target.text = f"{last_target.text}\n{text}".strip()
                        last_target.page_end = page_num

            i += 1

        self._assign_page_spans(root_nodes)
        return root_nodes

    def _next_seq(self, current_seq: int) -> int:
        return current_seq + 1

    def _is_any_marker(self, text: str) -> bool:
        c = text.strip()
        return bool(
            RE_BAB.match(c)
            or RE_BAGIAN.match(c)
            or RE_PARAGRAF.match(c)
            or RE_PASAL.match(c)
            or RE_AYAT.match(c)
            or RE_MENIMBANG.match(c)
            or RE_MENGINGAT.match(c)
            or RE_MEMUTUSKAN.match(c)
        )

    def _assign_page_spans(self, nodes: list[StructuredNode]) -> None:
        """Recursively calculate page_start and page_end spans for container parent nodes."""
        for node in nodes:
            if node.children:
                self._assign_page_spans(node.children)
                node.page_start = min(c.page_start for c in node.children)
                node.page_end = max(c.page_end for c in node.children)
