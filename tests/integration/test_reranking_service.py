"""Integration tests for Phase 5 RerankingService using MockRerankerProvider."""

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
from finreg.reranking.providers import MockRerankerProvider
from finreg.reranking.service import RerankingService
from finreg.vector.providers import MockEmbeddingProvider
from finreg.vector.search_service import VectorSearchService


def test_reranking_service_end_to_end_flow() -> None:
    """Verify RerankingService processes Phase 4C candidates and produces reranked results."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        unique_num = f"RRK-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Reranking Integration Test Regulation",
            detail_url="https://example.com/rrk-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/rrk-{unique_num}.pdf",
            filename=f"rrk_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_rrk.pdf",
            content_length=7777,
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
            title="Reranking Integration Test",
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
            title="Reranking Integration Test",
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

        # Build pipeline using offline mock providers
        dense_service = VectorSearchService(provider=mock_provider)
        lex_ret = BM25LexicalRetriever([chunk_1, chunk_2])
        lexical_service = LexicalRetrievalService(retriever=lex_ret)
        hybrid_retriever = RRFHybridRetriever(
            dense_service=dense_service, lexical_service=lexical_service
        )
        hybrid_service = HybridRetrievalService(retriever=hybrid_retriever)

        mock_reranker = MockRerankerProvider(model_name="mock-reranker-v1")
        reranking_service = RerankingService(reranker=mock_reranker, hybrid_service=hybrid_service)

        # Execute end-to-end rerank search
        results, report = reranking_service.search(
            query="transaksi lindung nilai",
            top_n=5,
            document_id_filter=doc.id,
        )

        assert len(results) > 0
        assert report.model_name == "mock-reranker-v1"
        assert report.reranked_out_count == len(results)
        assert results[0].source == "TEST_BI"
        assert results[0].regulation_type == "PBI"
        assert results[0].regulation_number == unique_num
        assert results[0].document_id == doc.id
        assert results[0].rerank_rank == 1

        # Test empty query handling
        empty_res, empty_rep = reranking_service.search(query="", top_n=5)
        assert empty_res == []
        assert empty_rep.reranked_out_count == 0

    finally:
        session.close()
