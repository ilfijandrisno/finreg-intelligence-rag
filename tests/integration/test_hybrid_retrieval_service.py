"""Integration tests for Phase 4C HybridRetrievalService combining dense and BM25 search."""

from uuid import uuid4

from sqlalchemy.orm import Session

from finreg.database.connection import get_engine, get_session_factory
from finreg.database.models import (
    ChunkEmbeddingORM,
    DocumentNodeORM,
    DocumentORM,
    DocumentVersionORM,
    RegulationORM,
    RetrievalChunkORM,
)
from finreg.hybrid.providers import RRFHybridRetriever
from finreg.hybrid.service import HybridRetrievalService
from finreg.lexical.providers import BM25LexicalRetriever
from finreg.lexical.service import LexicalRetrievalService
from finreg.vector.providers import MockEmbeddingProvider
from finreg.vector.search_service import VectorSearchService


def test_hybrid_retrieval_service_db_search_and_filtering() -> None:
    """Verify HybridRetrievalService combines dense vector and BM25 search with RRF."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        unique_num = f"HYB-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Hybrid Integration Test Regulation",
            detail_url="https://example.com/hyb-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/hyb-{unique_num}.pdf",
            filename=f"hyb_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_hyb.pdf",
            content_length=6666,
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
            title="Hybrid Integration Test",
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
            title="Hybrid Integration Test",
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
        session.flush()

        # Add mock embeddings for dense vector branch
        mock_provider = MockEmbeddingProvider(dimension=1536)
        vec_1 = mock_provider.embed_query("transaksi lindung nilai")
        vec_2 = mock_provider.embed_query("bank mitra")

        emb_1 = ChunkEmbeddingORM(
            chunk_id=chunk_1.id,
            document_id=doc.id,
            document_version_id=ver.id,
            embedding_model="text-embedding-3-small",
            embedding=vec_1,
        )
        emb_2 = ChunkEmbeddingORM(
            chunk_id=chunk_2.id,
            document_id=doc.id,
            document_version_id=ver.id,
            embedding_model="text-embedding-3-small",
            embedding=vec_2,
        )
        session.add_all([emb_1, emb_2])
        session.commit()

        # Build services with mock embedding provider
        dense_service = VectorSearchService(provider=mock_provider)
        lexical_service = LexicalRetrievalService(
            retriever=BM25LexicalRetriever([chunk_1, chunk_2])
        )
        retriever = RRFHybridRetriever(dense_service=dense_service, lexical_service=lexical_service)

        service = HybridRetrievalService(retriever=retriever)

        # 1. Test hybrid search with document_id filter
        results, report = service.search(
            query="transaksi lindung nilai",
            top_k=5,
            document_id_filter=doc.id,
        )

        assert len(results) > 0
        assert report.fused_results_count == len(results)
        assert results[0].source == "TEST_BI"
        assert results[0].regulation_type == "PBI"
        assert results[0].regulation_number == unique_num
        assert results[0].document_id == doc.id
        assert results[0].document_version_id == ver.id

        # 2. Test empty query handling
        empty_res, empty_rep = service.search(query="", top_k=5)
        assert empty_res == []
        assert empty_rep.fused_results_count == 0

        # 3. Test metadata filter mismatch
        mismatch_res, _ = service.search(
            query="transaksi",
            top_k=5,
            source_filter="NONEXISTENT_SOURCE",
            document_id_filter=doc.id,
        )
        assert mismatch_res == []

        # 4. Test repeated search determinism
        run1, _ = service.search(query="transaksi", top_k=5, document_id_filter=doc.id)
        run2, _ = service.search(query="transaksi", top_k=5, document_id_filter=doc.id)
        assert [r.chunk_id for r in run1] == [r.chunk_id for r in run2]
        assert [r.fused_score for r in run1] == [r.fused_score for r in run2]

    finally:
        session.close()
