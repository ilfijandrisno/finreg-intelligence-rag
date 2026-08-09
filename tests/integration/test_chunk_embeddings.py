"""Integration tests for chunk_embeddings DB persistence and vector search."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
from finreg.vector.providers import MockEmbeddingProvider
from finreg.vector.search_service import VectorSearchService
from finreg.vector.service import DocumentEmbeddingService


def test_chunk_embeddings_persistence_and_controlled_vector_search() -> None:
    """Verify chunk_embeddings persistence and pgvector cosine distance search."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        # 1. Setup DB hierarchy
        unique_num = f"VEC-TEST-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Peraturan Test Vector Search",
            detail_url="https://example.com/vec-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/vec-{unique_num}.pdf",
            filename=f"vec_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_vec.pdf",
            content_length=9999,
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
            text="Ketentuan valas.",
            page_start=1,
            page_end=1,
            sequence=1,
            path="Pasal 1/Ayat (1)",
        )
        session.add(node)
        session.flush()

        chunk_a = RetrievalChunkORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            source_node_id=node.id,
            chunk_hash=uuid4().hex,
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Peraturan Test",
            structural_path="Pasal 1/Ayat (1)",
            chunk_text="Chunk A text about FX trading.",
            contextual_text="Header\n\nChunk A text about FX trading.",
            character_count=29,
            word_count=6,
            page_start=1,
            page_end=1,
            sequence=1,
        )
        chunk_b = RetrievalChunkORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            source_node_id=node.id,
            chunk_hash=uuid4().hex,
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Peraturan Test",
            structural_path="Pasal 1/Ayat (2)",
            chunk_text="Chunk B text about liquidity.",
            contextual_text="Header\n\nChunk B text about liquidity.",
            character_count=29,
            word_count=5,
            page_start=1,
            page_end=1,
            sequence=2,
        )
        session.add_all([chunk_a, chunk_b])
        session.commit()

        # 2. Insert controlled mathematical unit vectors:
        # Vector A: [1.0, 0.0, ..., 0.0]
        # Vector B: [0.0, 1.0, ..., 0.0]
        vec_a = [1.0] + [0.0] * 1535
        vec_b = [0.0, 1.0] + [0.0] * 1534

        emb_a = ChunkEmbeddingORM(
            document_id=doc.id,
            document_version_id=ver.id,
            chunk_id=chunk_a.id,
            embedding_model="text-embedding-3-small",
            embedding=vec_a,
        )
        emb_b = ChunkEmbeddingORM(
            document_id=doc.id,
            document_version_id=ver.id,
            chunk_id=chunk_b.id,
            embedding_model="text-embedding-3-small",
            embedding=vec_b,
        )
        session.add_all([emb_a, emb_b])
        session.commit()

        # 3. Query vector matching Vector A: [1.0, 0.0, ..., 0.0]
        mock_provider = MockEmbeddingProvider(model_name="text-embedding-3-small", dimension=1536)
        mock_provider.embed_query = lambda q: vec_a  # type: ignore

        search_service = VectorSearchService(provider=mock_provider)
        results = search_service.search(
            query="FX trading query",
            top_k=2,
            document_id_filter=doc.id,
            session=session,
        )

        assert len(results) == 2
        # Chunk A must rank first with distance ~0.0 and score 1.0
        assert results[0].chunk_id == chunk_a.id
        assert pytest.approx(results[0].distance, abs=1e-3) == 0.0
        assert pytest.approx(results[0].score, abs=1e-3) == 1.0

        # Chunk B must rank second with distance ~1.0 (orthogonal) and score 0.0
        assert results[1].chunk_id == chunk_b.id
        assert pytest.approx(results[1].distance, abs=1e-3) == 1.0
        assert pytest.approx(results[1].score, abs=1e-3) == 0.0

    finally:
        session.close()


def test_model_coexistence_and_idempotency() -> None:
    """Verify different embedding models coexist safely and replacement is idempotent per model."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        unique_num = f"MODEL-TEST-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Coexistence Test",
            detail_url="https://example.com/model-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/mod-{unique_num}.pdf",
            filename=f"mod_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_mod.pdf",
            content_length=8888,
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
            text="Text node.",
            page_start=1,
            page_end=1,
            sequence=1,
            path="Pasal 1",
        )
        session.add(node)
        session.flush()

        chunk = RetrievalChunkORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            source_node_id=node.id,
            chunk_hash=uuid4().hex,
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Coexistence Test",
            structural_path="Pasal 1",
            chunk_text="Text node.",
            contextual_text="Header\n\nText node.",
            character_count=10,
            word_count=2,
            page_start=1,
            page_end=1,
            sequence=1,
        )
        session.add(chunk)
        session.commit()

        # 1. Embed using Model A: text-embedding-3-small
        provider_a = MockEmbeddingProvider(model_name="text-embedding-3-small", dimension=1536)
        service_a = DocumentEmbeddingService(provider=provider_a)
        report_a, _ = service_a.embed_document(document_id=doc.id, dry_run=False, session=session)
        assert report_a.is_valid is True

        # 2. Embed using Model B: text-embedding-3-large
        provider_b = MockEmbeddingProvider(model_name="text-embedding-3-large", dimension=1536)
        service_b = DocumentEmbeddingService(provider=provider_b)
        report_b, _ = service_b.embed_document(document_id=doc.id, dry_run=False, session=session)
        assert report_b.is_valid is True

        # 3. Assert both models exist concurrently in DB
        db_embeddings = list(
            session.scalars(
                select(ChunkEmbeddingORM).where(ChunkEmbeddingORM.document_id == doc.id)
            )
        )
        assert len(db_embeddings) == 2
        models_in_db = {e.embedding_model for e in db_embeddings}
        assert models_in_db == {"text-embedding-3-small", "text-embedding-3-large"}

        # 4. Re-embed using Model A (Idempotency check)
        report_a2, _ = service_a.embed_document(document_id=doc.id, dry_run=False, session=session)
        assert report_a2.is_valid is True

        db_embeddings2 = list(
            session.scalars(
                select(ChunkEmbeddingORM).where(ChunkEmbeddingORM.document_id == doc.id)
            )
        )
        assert len(db_embeddings2) == 2  # Still 2 total rows (Model A replaced, Model B untouched)

    finally:
        session.close()


def test_composite_provenance_fk_rejection() -> None:
    """Verify PostgreSQL composite FK rejects chunk_embeddings with mismatched document_id."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        unique_num = f"FK-TEST-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="FK Rejection Test",
            detail_url="https://example.com/fk-test",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/fk-{unique_num}.pdf",
            filename=f"fk_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_fk.pdf",
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
            text="FK test text.",
            page_start=1,
            page_end=1,
            sequence=1,
            path="Pasal 1",
        )
        session.add(node)
        session.flush()

        chunk = RetrievalChunkORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            source_node_id=node.id,
            chunk_hash=uuid4().hex,
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="FK Rejection Test",
            structural_path="Pasal 1",
            chunk_text="FK test text.",
            contextual_text="Header\n\nFK test text.",
            character_count=13,
            word_count=3,
            page_start=1,
            page_end=1,
            sequence=1,
        )
        session.add(chunk)
        session.commit()

        # Attempt to insert ChunkEmbeddingORM with MISMATCHED document_version_id
        mismatched_ver_id = uuid4()
        mismatched_emb = ChunkEmbeddingORM(
            document_id=doc.id,
            document_version_id=mismatched_ver_id,  # Mismatched!
            chunk_id=chunk.id,
            embedding_model="text-embedding-3-small",
            embedding=[0.1] * 1536,
        )
        session.add(mismatched_emb)

        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        assert "fk_chunk_embeddings_retrieval_chunk" in str(exc_info.value)
        session.rollback()

    finally:
        session.close()


def test_dry_run_causes_zero_db_mutations() -> None:
    """Verify that vector embedding --dry-run performs zero database mutations."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session: Session = session_factory()

    try:
        unique_num = f"DRY-VEC-{uuid4().hex[:8]}"
        reg = RegulationORM(
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Dry Vector Test",
            detail_url="https://example.com/dry-vec",
        )
        session.add(reg)
        session.flush()

        doc = DocumentORM(
            regulation_id=reg.id,
            document_type="regulation",
            document_url=f"https://example.com/dryv-{unique_num}.pdf",
            filename=f"dryv_{unique_num}.pdf",
            content_type="application/pdf",
        )
        session.add(doc)
        session.flush()

        ver = DocumentVersionORM(
            document_id=doc.id,
            sha256=uuid4().hex,
            storage_path="/tmp/fake_dryv.pdf",
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
            text="Dry text.",
            page_start=1,
            page_end=1,
            sequence=1,
            path="Pasal 1",
        )
        session.add(node)
        session.flush()

        chunk = RetrievalChunkORM(
            id=uuid4(),
            document_id=doc.id,
            document_version_id=ver.id,
            source_node_id=node.id,
            chunk_hash=uuid4().hex,
            source="TEST_BI",
            regulation_type="PBI",
            regulation_number=unique_num,
            title="Dry Vector Test",
            structural_path="Pasal 1",
            chunk_text="Dry text.",
            contextual_text="Header\n\nDry text.",
            character_count=9,
            word_count=2,
            page_start=1,
            page_end=1,
            sequence=1,
        )
        session.add(chunk)
        session.commit()

        provider = MockEmbeddingProvider(model_name="text-embedding-3-small", dimension=1536)
        service = DocumentEmbeddingService(provider=provider)

        report, items = service.embed_document(document_id=doc.id, dry_run=True, session=session)

        assert report.is_valid is True
        assert report.chunks_embedded == 1
        assert len(items) == 1

        # Query database to confirm 0 rows in chunk_embeddings
        db_embeddings = list(
            session.scalars(
                select(ChunkEmbeddingORM).where(ChunkEmbeddingORM.document_id == doc.id)
            )
        )
        assert len(db_embeddings) == 0

    finally:
        session.close()
