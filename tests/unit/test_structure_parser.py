"""Unit tests for RegulatoryStructureParser legal document state-machine parsing."""

from finreg.documents.models import NodeType, NormalizedLine
from finreg.documents.parser import RegulatoryStructureParser


def test_parser_indonesian_regulation_hierarchy() -> None:
    """Verify state-machine parser parses complete Indonesian regulation hierarchy."""
    lines = [
        NormalizedLine(
            text="PERATURAN BANK INDONESIA NOMOR 23/13/PBI/2021", page_num=1, line_num=1
        ),
        NormalizedLine(
            text="Menimbang : a. bahwa transfer dana perlu diatur;", page_num=1, line_num=2
        ),
        NormalizedLine(
            text="Mengingat : 1. Undang-Undang Nomor 23 Tahun 1999;", page_num=1, line_num=3
        ),
        NormalizedLine(
            text="MEMUTUSKAN: Menetapkan: PERATURAN TRANSFER DANA", page_num=1, line_num=4
        ),
        NormalizedLine(text="BAB I", page_num=1, line_num=5),
        NormalizedLine(text="KETENTUAN UMUM", page_num=1, line_num=6),
        NormalizedLine(text="Bagian Kesatu", page_num=1, line_num=7),
        NormalizedLine(text="Definisi", page_num=1, line_num=8),
        NormalizedLine(text="Pasal 1", page_num=1, line_num=9),
        NormalizedLine(
            text="(1) Bank Indonesia berwenang mengatur transfer dana.", page_num=1, line_num=10
        ),
        NormalizedLine(
            text="a. Kewenangan sebagaimana dimaksud mencakup:", page_num=1, line_num=11
        ),
        NormalizedLine(text="1. Pengawasan penyelenggara.", page_num=1, line_num=12),
        NormalizedLine(text="PASAL PENUTUP", page_num=2, line_num=13),
    ]

    parser = RegulatoryStructureParser()
    nodes = parser.parse(lines)

    assert len(nodes) >= 5

    # Preamble check
    assert nodes[0].node_type == NodeType.PREAMBLE
    assert "PERATURAN BANK INDONESIA" in nodes[0].text

    # Menimbang check
    menimbang = next(n for n in nodes if n.node_type == NodeType.CONSIDERATION)
    assert "transfer dana perlu diatur" in menimbang.text

    # Mengingat check
    mengingat = next(n for n in nodes if n.node_type == NodeType.LEGAL_BASIS)
    assert "Undang-Undang Nomor 23" in mengingat.text

    # BAB check
    bab = next(n for n in nodes if n.node_type == NodeType.CHAPTER)
    assert bab.node_number == "I"
    assert bab.title == "KETENTUAN UMUM"
    assert bab.path == "BAB I"

    # Bagian check (under BAB)
    bagian = bab.children[0]
    assert bagian.node_type == NodeType.PART
    assert bagian.node_number == "Kesatu"
    assert bagian.title == "Definisi"
    assert bagian.path == "BAB I/Bagian Kesatu"

    # Pasal check (under Bagian)
    pasal = bagian.children[0]
    assert pasal.node_type == NodeType.ARTICLE
    assert pasal.node_number == "1"
    assert pasal.path == "BAB I/Bagian Kesatu/Pasal 1"

    # Ayat check (under Pasal)
    ayat = pasal.children[0]
    assert ayat.node_type == NodeType.PARAGRAPH
    assert ayat.node_number == "1"
    assert "Bank Indonesia berwenang" in ayat.text
    assert ayat.path == "BAB I/Bagian Kesatu/Pasal 1/Ayat (1)"

    # Huruf check (under Ayat)
    huruf = ayat.children[0]
    assert huruf.node_type == NodeType.LETTER
    assert huruf.node_number == "a"
    assert huruf.path == "BAB I/Bagian Kesatu/Pasal 1/Ayat (1)/Huruf a"

    # Numbered item check (under Huruf)
    num_item = huruf.children[0]
    assert num_item.node_type == NodeType.NUMBERED_ITEM
    assert num_item.node_number == "1"
    assert num_item.path == "BAB I/Bagian Kesatu/Pasal 1/Ayat (1)/Huruf a/1."

    # Closing check
    closing = nodes[-1]
    assert closing.node_type == NodeType.CLOSING
    assert closing.page_start == 2


def test_single_clause_article_creates_implicit_paragraph() -> None:
    """Verify single-clause Article without (1) creates implicit PARAGRAPH leaf node."""
    lines = [
        NormalizedLine(text="Pasal 3", page_num=1, line_num=1),
        NormalizedLine(
            text="Objek pengaturan meliputi transaksi pasar valuta asing.",
            page_num=1,
            line_num=2,
        ),
    ]
    parser = RegulatoryStructureParser()
    nodes = parser.parse(lines)

    assert len(nodes) == 1
    art = nodes[0]
    assert art.node_type == NodeType.ARTICLE
    assert art.node_number == "3"
    assert art.text == ""  # Container node text remains empty

    assert len(art.children) == 1
    para = art.children[0]
    assert para.node_type == NodeType.PARAGRAPH
    assert para.node_number is None
    assert para.text == "Objek pengaturan meliputi transaksi pasar valuta asing."
    assert para.path == "Pasal 3/Ayat (1)"


def test_article_introductory_text_with_numbered_items() -> None:
    """Verify Article with intro text and NUMBERED_ITEM creates implicit PARAGRAPH."""
    lines = [
        NormalizedLine(text="Pasal 4", page_num=1, line_num=1),
        NormalizedLine(text="Ruang lingkup meliputi:", page_num=1, line_num=2),
        NormalizedLine(text="1. Transaksi spot;", page_num=1, line_num=3),
        NormalizedLine(text="2. Transaksi derivatif.", page_num=1, line_num=4),
    ]
    parser = RegulatoryStructureParser()
    nodes = parser.parse(lines)

    art = nodes[0]
    assert art.node_type == NodeType.ARTICLE
    assert art.text == ""

    # Implicit paragraph for introductory text
    intro_para = art.children[0]
    assert intro_para.node_type == NodeType.PARAGRAPH
    assert intro_para.text == "Ruang lingkup meliputi:"

    # Numbered items under implicit paragraph
    num1 = intro_para.children[0]
    assert num1.node_type == NodeType.NUMBERED_ITEM
    assert num1.node_number == "1"
    assert "Transaksi spot" in num1.text


def test_multiline_chapter_title_concatenation() -> None:
    """Verify multi-line CHAPTER title lines are combined into title with empty text."""
    lines = [
        NormalizedLine(text="BAB II", page_num=1, line_num=1),
        NormalizedLine(
            text="PENYELENGGARAAN TRANSAKSI PASAR VALUTA ASING",
            page_num=1,
            line_num=2,
        ),
        NormalizedLine(text="MELALUI BANK MITRA", page_num=1, line_num=3),
        NormalizedLine(text="Pasal 3", page_num=1, line_num=4),
    ]
    parser = RegulatoryStructureParser()
    nodes = parser.parse(lines)

    chap = nodes[0]
    assert chap.node_type == NodeType.CHAPTER
    assert chap.title == "PENYELENGGARAAN TRANSAKSI PASAR VALUTA ASING MELALUI BANK MITRA"
    assert chap.text == ""


def test_non_overlapping_coverage_container_text_empty() -> None:
    """Verify container nodes (CHAPTER, PART, SECTION, ARTICLE) have empty text."""
    lines = [
        NormalizedLine(text="BAB I", page_num=1, line_num=1),
        NormalizedLine(text="KETENTUAN UMUM", page_num=1, line_num=2),
        NormalizedLine(text="Bagian Kesatu", page_num=1, line_num=3),
        NormalizedLine(text="Definisi", page_num=1, line_num=4),
        NormalizedLine(text="Pasal 1", page_num=1, line_num=5),
        NormalizedLine(text="Dalam Peraturan ini:", page_num=1, line_num=6),
    ]
    parser = RegulatoryStructureParser()
    nodes = parser.parse(lines)

    def assert_container_text_empty(node_list):
        for n in node_list:
            if n.node_type in (
                NodeType.CHAPTER,
                NodeType.PART,
                NodeType.SECTION,
                NodeType.ARTICLE,
            ):
                assert n.text == ""
            if n.children:
                assert_container_text_empty(n.children)

    assert_container_text_empty(nodes)


def test_realistic_padg_pbi_structure_pattern() -> None:
    """Verify realistic PADG structure with mixed single-clause Articles and multi-line titles."""
    lines = [
        NormalizedLine(text="BAB I", page_num=1, line_num=1),
        NormalizedLine(text="KETENTUAN UMUM", page_num=1, line_num=2),
        NormalizedLine(text="Pasal 1", page_num=1, line_num=3),
        NormalizedLine(text="Ketentuan umum ini berlaku.", page_num=1, line_num=4),
        NormalizedLine(text="BAB II", page_num=1, line_num=5),
        NormalizedLine(text="TRANSAKSI VALUTA ASING", page_num=1, line_num=6),
        NormalizedLine(text="Pasal 2", page_num=1, line_num=7),
        NormalizedLine(text="Transaksi dilakukan dengan bank.", page_num=1, line_num=8),
    ]
    parser = RegulatoryStructureParser()
    nodes = parser.parse(lines)

    assert len(nodes) == 2
    assert nodes[0].title == "KETENTUAN UMUM"
    assert nodes[1].title == "TRANSAKSI VALUTA ASING"

    art1 = nodes[0].children[0]
    assert art1.node_number == "1"
    assert art1.children[0].text == "Ketentuan umum ini berlaku."

    art2 = nodes[1].children[0]
    assert art2.node_number == "2"
    assert art2.children[0].text == "Transaksi dilakukan dengan bank."
