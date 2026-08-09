"""Orchestrator service for legal chunk embedding generation and persistence (Phase 4A)."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from finreg.config.settings import get_settings
from finreg.database.connection import get_engine, get_session_factory
from finreg.database.repository import IngestionRepository
from finreg.documents.models import NoCurrentDocumentVersionError
from finreg.vector.providers import EmbeddingProvider, get_embedding_provider
from finreg.vector.vector_models import EmbeddingExecutionReport

logger = logging.getLogger(__name__)


class DocumentEmbeddingService:
    """Service managing document chunk vector embedding generation and atomic DB replacement."""

    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider or get_embedding_provider()

    def embed_document(
        self,
        document_id: UUID,
        dry_run: bool = False,
        session: Session | None = None,
    ) -> tuple[EmbeddingExecutionReport, list[dict]]:
        """Generate vector embeddings for all chunks of a document and persist to PostgreSQL."""
        own_session = False
        if session is None:
            engine = get_engine()
            session_factory = get_session_factory(engine)
            session = session_factory()
            own_session = True

        try:
            repo = IngestionRepository(session)
            version = repo.get_current_document_version(document_id)
            if not version:
                raise NoCurrentDocumentVersionError(
                    f"No active document_version with is_current=True for Document {document_id}"
                )

            chunks = repo.get_retrieval_chunks(document_id)
            if not chunks:
                logger.warning("No retrieval chunks found for Document %s", document_id)
                report = EmbeddingExecutionReport(
                    document_id=document_id,
                    version_id=version.id,
                    embedding_model=self.provider.model_name,
                    dimension=self.provider.dimension,
                    chunks_embedded=0,
                    total_vectors_persisted=0,
                    is_valid=True,
                    warnings=["No retrieval chunks found to embed"],
                )
                return report, []

            # contextual_text is the sole embedding input
            input_texts = [c.contextual_text for c in chunks]

            # Batch generate vectors via provider
            vectors = self.provider.embed_texts(input_texts)

            settings = get_settings()
            expected_dim = settings.embedding_dimension

            warnings: list[str] = []
            is_valid = True

            # Validate vector dimensions
            for idx, vec in enumerate(vectors):
                if len(vec) != expected_dim:
                    is_valid = False
                    msg = (
                        f"Dimension mismatch at chunk {chunks[idx].id}: "
                        f"expected {expected_dim}, got {len(vec)}"
                    )
                    warnings.append(msg)
                    logger.error(msg)

            items = [
                {
                    "chunk_id": chunks[idx].id,
                    "embedding": vec,
                }
                for idx, vec in enumerate(vectors)
            ]

            persisted_count = 0
            if not dry_run and is_valid:
                created_orm = repo.replace_chunk_embeddings(
                    document_id=document_id,
                    document_version_id=version.id,
                    embedding_model=self.provider.model_name,
                    embeddings=items,
                )
                session.commit()
                persisted_count = len(created_orm)
                logger.info(
                    "Successfully committed %d chunk embeddings for Document %s (Model: %s)",
                    persisted_count,
                    document_id,
                    self.provider.model_name,
                )

            report = EmbeddingExecutionReport(
                document_id=document_id,
                version_id=version.id,
                embedding_model=self.provider.model_name,
                dimension=self.provider.dimension,
                chunks_embedded=len(vectors),
                total_vectors_persisted=persisted_count if not dry_run else len(vectors),
                is_valid=is_valid,
                warnings=warnings,
            )

            return report, items

        except Exception as exc:
            session.rollback()
            logger.error("Failed to embed document %s: %s", document_id, exc)
            raise

        finally:
            if own_session:
                session.close()
