"""Orchestrator service for BM25 lexical retrieval over PostgreSQL retrieval chunks."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finreg.database.connection import get_engine, get_session_factory
from finreg.database.models import DocumentVersionORM, RetrievalChunkORM
from finreg.lexical.lexical_models import LexicalIndexReport, LexicalSearchResult
from finreg.lexical.providers import BM25LexicalRetriever, LexicalRetriever

logger = logging.getLogger(__name__)


class LexicalRetrievalService:
    """Service executing lexical keyword search using BM25 over database retrieval chunks."""

    def __init__(self, retriever: LexicalRetriever | None = None):
        self._retriever = retriever

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
        regulation_type_filter: str | None = None,
        regulation_number_filter: str | None = None,
        document_id_filter: UUID | None = None,
        session: Session | None = None,
    ) -> tuple[list[LexicalSearchResult], LexicalIndexReport]:
        """Execute BM25 lexical search over database retrieval chunks with metadata filtering."""
        if not query or not query.strip() or top_k <= 0:
            empty_report = LexicalIndexReport(
                total_chunks=0, vocabulary_size=0, average_doc_length=0.0
            )
            return [], empty_report

        own_session = False
        if session is None:
            engine = get_engine()
            session_factory = get_session_factory(engine)
            session = session_factory()
            own_session = True

        try:
            retriever = self._retriever
            if retriever is None:
                # Query active retrieval_chunks for current document versions
                stmt = (
                    select(RetrievalChunkORM)
                    .join(
                        DocumentVersionORM,
                        RetrievalChunkORM.document_version_id == DocumentVersionORM.id,
                    )
                    .where(DocumentVersionORM.is_current.is_(True))
                )

                if document_id_filter:
                    stmt = stmt.where(RetrievalChunkORM.document_id == document_id_filter)

                chunks = list(session.scalars(stmt))
                if not chunks:
                    logger.warning("No active retrieval chunks found for lexical indexing.")
                    empty_report = LexicalIndexReport(
                        total_chunks=0, vocabulary_size=0, average_doc_length=0.0
                    )
                    return [], empty_report

                retriever = BM25LexicalRetriever(chunks)

            report = retriever.get_index_report()
            results = retriever.search(
                query=query.strip(),
                top_k=top_k,
                source_filter=source_filter,
                regulation_type_filter=regulation_type_filter,
                regulation_number_filter=regulation_number_filter,
                document_id_filter=document_id_filter,
            )

            return results, report

        finally:
            if own_session:
                session.close()
