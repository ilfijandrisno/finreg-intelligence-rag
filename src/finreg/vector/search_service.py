"""Vector similarity search service executing pgvector queries with full legal provenance."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from finreg.config.settings import get_settings
from finreg.database.connection import get_engine, get_session_factory
from finreg.database.repository import IngestionRepository
from finreg.vector.providers import EmbeddingProvider, get_embedding_provider
from finreg.vector.vector_models import VectorSearchResult

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Dense vector search service executing pgvector similarity queries."""

    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider or get_embedding_provider()

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
        regulation_type_filter: str | None = None,
        document_id_filter: UUID | None = None,
        session: Session | None = None,
    ) -> list[VectorSearchResult]:
        """Execute pgvector similarity search for query and return top_k enriched results."""
        if not query or not query.strip():
            return []

        own_session = False
        if session is None:
            engine = get_engine()
            session_factory = get_session_factory(engine)
            session = session_factory()
            own_session = True

        try:
            query_vector = self.provider.embed_query(query.strip())
            settings = get_settings()
            expected_dim = settings.embedding_dimension

            if len(query_vector) != expected_dim:
                raise ValueError(
                    f"Query dimension mismatch: expected {expected_dim}, got {len(query_vector)}"
                )

            repo = IngestionRepository(session)
            db_results = repo.vector_similarity_search(
                query_vector=query_vector,
                top_k=top_k,
                embedding_model=self.provider.model_name,
                source_filter=source_filter,
                regulation_type_filter=regulation_type_filter,
                document_id_filter=document_id_filter,
            )

            search_results: list[VectorSearchResult] = []
            for emb_orm, chunk_orm, distance in db_results:
                score = max(0.0, round(1.0 - distance, 4))
                result = VectorSearchResult(
                    score=score,
                    distance=round(distance, 4),
                    chunk_id=chunk_orm.id,
                    source_node_id=chunk_orm.source_node_id,
                    document_id=chunk_orm.document_id,
                    document_version_id=chunk_orm.document_version_id,
                    embedding_model=emb_orm.embedding_model,
                    source=chunk_orm.source,
                    regulation_type=chunk_orm.regulation_type,
                    regulation_number=chunk_orm.regulation_number,
                    title=chunk_orm.title,
                    chapter_title=chunk_orm.chapter_title,
                    part_title=chunk_orm.part_title,
                    section_title=chunk_orm.section_title,
                    article_number=chunk_orm.article_number,
                    paragraph_number=chunk_orm.paragraph_number,
                    letter_code=chunk_orm.letter_code,
                    numbered_item=chunk_orm.numbered_item,
                    part_index=chunk_orm.part_index,
                    total_parts=chunk_orm.total_parts,
                    structural_path=chunk_orm.structural_path,
                    chunk_text=chunk_orm.chunk_text,
                    contextual_text=chunk_orm.contextual_text,
                    page_start=chunk_orm.page_start,
                    page_end=chunk_orm.page_end,
                    sequence=chunk_orm.sequence,
                )
                search_results.append(result)

            return search_results

        finally:
            if own_session:
                session.close()
