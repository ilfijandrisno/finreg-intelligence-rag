"""Integration tests for BM25 LexicalRetrievalService over PostgreSQL retrieval_chunks."""

from uuid import uuid4

from sqlalchemy.orm import Session

from finreg.database.connection import get_engine, get_session_factory
from finreg.database.models import (
    DocumentNodeORM,
    DocumentORM,
    DocumentVersionORM,
    RegulationORM,
    RetrievalChunkORM,
)
from finreg.lexical.service import LexicalRetrievalService


def test_lexical_retrieval_service_db_search_and_filtering() -> None:
    """Verify LexicalRetrievalService searches database chunks and applies metadata filters."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        unique_num = f"LEX-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Lexical Integration Test Regulation",
            detail_url="https://example.com/lex-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/lex-{unique_num}.pdf",
            filename=f"lex_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_lex.pdf",
            content_length=5555,
            is_current=True,
        )
        session.add(ver)
        session.flush()

        node = DocumentNodeORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            parent_id=None,
            node_type="paragraph",
            node_number="1",
            title=None,
            text="Node text.",
            page_start=1,
            page_end=1,
            sequence=1,
            path="Pasal 1",
        )
        session.add(node)
        session.flush()

        chunk_1 = RetrievalChunkORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            source_node_id=node.id,
            chunk_hash=uuid4().hex,
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Lexical Integration Test",
            structural_path="Pasal 1/Ayat (1)",
            chunk_text="Ketentuan transaksi lindung nilai valuta asing.",
            contextual_text="Header\n\nKetentuan transaksi lindung nilai valuta asing.",
            character_count=46,
            word_count=6,
            page_start=1,
            page_end=1,
            sequence=1,
        )
        chunk_2 = RetrievalChunkORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            source_node_id=node.id,
            chunk_hash=uuid4().hex,
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Lexical Integration Test",
            structural_path="Pasal 2/Ayat (1)",
            chunk_text="Penetapan bank mitra dalam transaksi pasar uang.",
            contextual_text="Header\n\nPenetapan bank mitra dalam transaksi pasar uang.",
            character_count=48,
            word_count=7,
            page_start=2,
            page_end=2,
            sequence=2,
        )
        session.add_all([chunk_1, chunk_2])
        session.commit()

        service = LexicalRetrievalService()

        # 1. Search term 'lindung nilai' with document_id_filter
        results_ln, report_ln = service.search(
            query="lindung nilai",
            top_k=5,
            document_id_filter=doc.id,
            session=session,
        )
        assert len(results_ln) == 1
        assert results_ln[0].chunk_id == chunk_1.id
        assert results_ln[0].structural_path == "Pasal 1/Ayat (1)"
        assert results_ln[0].source == "TEST_BI"
        assert results_ln[0].regulation_type == "PBI"
        assert results_ln[0].regulation_number == unique_num
        assert report_ln.total_chunks >= 2

        # 2. Search term 'bank mitra'
        results_bm, _ = service.search(
            query="bank mitra",
            top_k=5,
            document_id_filter=doc.id,
            session=session,
        )
        assert len(results_bm) == 1
        assert results_bm[0].chunk_id == chunk_2.id

        # 3. Empty query returns []
        results_empty, _ = service.search(query="", top_k=5, session=session)
        assert results_empty == []

        # 4. Non-matching query returns []
        results_nomatch, _ = service.search(query="nonexistenttermxyz99", top_k=5, session=session)
        assert results_nomatch == []

        # 5. Metadata filtering: source filter match & mismatch
        results_filter_match, _ = service.search(
            query="transaksi",
            top_k=5,
            source_filter="TEST_BI",
            document_id_filter=doc.id,
            session=session,
        )
        assert len(results_filter_match) == 2

        results_filter_mismatch, _ = service.search(
            query="transaksi",
            top_k=5,
            source_filter="NONEXISTENT_SOURCE",
            document_id_filter=doc.id,
            session=session,
        )
        assert results_filter_mismatch == []

        # 6. Deterministic repeated search
        run1, _ = service.search(
            query="transaksi", top_k=5, document_id_filter=doc.id, session=session
        )
        run2, _ = service.search(
            query="transaksi", top_k=5, document_id_filter=doc.id, session=session
        )
        assert [r.chunk_id for r in run1] == [r.chunk_id for r in run2]
        assert [r.score for r in run1] == [r.score for r in run2]

    finally:
        session.close()
