"""Unit tests for pure-Python BM25Engine and BM25LexicalRetriever."""

from uuid import uuid4

from finreg.database.models import RetrievalChunkORM
from finreg.lexical.bm25 import BM25Engine, tokenize
from finreg.lexical.providers import BM25LexicalRetriever


def test_tokenize_lowercasing_and_word_extraction() -> None:
    """Verify tokenizer lowercases text and strips punctuation."""
    assert tokenize("Pasal 1 Ayat (1) - Lindung Nilai!") == [
        "pasal",
        "1",
        "ayat",
        "1",
        "lindung",
        "nilai",
    ]
    assert tokenize("") == []


def test_bm25_engine_scoring_and_idf() -> None:
    """Verify BM25Engine calculates term scores and Robertson-Spärck Jones IDF."""
    corpus = [
        "Transaksi pasar valuta asing dan lindung nilai.",
        "Ketentuan mengenai penetapan bank mitra pasar uang.",
        "Pengawasan kehati-hatian transaksi valuta asing.",
    ]
    engine = BM25Engine(corpus)

    assert engine.corpus_size == 3
    assert engine.vocabulary_size > 0

    scores = engine.get_scores("valuta asing")
    assert len(scores) == 3
    # Doc 0 and Doc 2 contain both 'valuta' and 'asing', Doc 1 contains neither
    assert scores[0] > 0.0
    assert scores[2] > 0.0
    assert scores[1] == 0.0


def test_bm25_engine_empty_and_unmatched_queries() -> None:
    """Verify empty queries or non-matching terms return zero scores."""
    corpus = ["Pengawasan perbankan dan lembaga keuangan."]
    engine = BM25Engine(corpus)

    assert engine.get_scores("") == [0.0]
    assert engine.get_scores("   ") == [0.0]
    assert engine.get_scores("nonexistentterm12345") == [0.0]


def test_bm25_deterministic_tie_breaking() -> None:
    """Verify BM25LexicalRetriever applies multi-key tie-breaking sort order."""
    doc_id = uuid4()
    ver_id = uuid4()

    # Create 2 chunks with identical text (identical BM25 score) but different paths/sequences
    chunk_b = RetrievalChunkORM(
        id=uuid4(),
        document_id=doc_id,
        document_version_id=ver_id,
        source_node_id=uuid4(),
        chunk_hash="hash_b",
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        structural_path="Pasal 2",
        chunk_text="Pengawasan transaksi valas.",
        contextual_text="Header B",
        character_count=20,
        word_count=3,
        page_start=2,
        page_end=2,
        sequence=2,
    )
    chunk_a = RetrievalChunkORM(
        id=uuid4(),
        document_id=doc_id,
        document_version_id=ver_id,
        source_node_id=uuid4(),
        chunk_hash="hash_a",
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        structural_path="Pasal 1",
        chunk_text="Pengawasan transaksi valas.",
        contextual_text="Header A",
        character_count=20,
        word_count=3,
        page_start=1,
        page_end=1,
        sequence=1,
    )

    retriever = BM25LexicalRetriever([chunk_b, chunk_a])
    results = retriever.search("valas", top_k=2)

    assert len(results) == 2
    # Equal BM25 scores must be tie-broken by structural_path ASC: "Pasal 1" before "Pasal 2"
    assert results[0].structural_path == "Pasal 1"
    assert results[1].structural_path == "Pasal 2"


def test_bm25_top_k_zero_or_negative() -> None:
    """Verify top_k <= 0 returns an empty result list."""
    chunk = RetrievalChunkORM(
        id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        source_node_id=uuid4(),
        chunk_hash="hash_1",
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test",
        structural_path="Pasal 1",
        chunk_text="Ketentuan transaksi valas.",
        contextual_text="Header",
        character_count=20,
        word_count=3,
        page_start=1,
        page_end=1,
        sequence=1,
    )
    retriever = BM25LexicalRetriever([chunk])

    assert retriever.search("valas", top_k=0) == []
    assert retriever.search("valas", top_k=-5) == []
