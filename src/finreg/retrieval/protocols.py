"""Protocol interfaces for embedding generation, vector/keyword retrieval, and reranking."""

from typing import Any, Protocol, runtime_checkable

from finreg.domain.models import Chunk


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for generating vector embeddings from text inputs."""

    def embed_text(self, text: str) -> list[float]:
        """Embed a single string into a float vector embedding."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple strings into a list of float vector embeddings."""
        ...


@runtime_checkable
class Retriever(Protocol):
    """Protocol for searching and retrieving relevant chunks given a natural language query."""

    def retrieve(
        self, query: str, top_k: int = 10, filters: dict[str, Any] | None = None
    ) -> list[Chunk]:
        """Retrieve top_k candidate Chunks matching the query and optional metadata filters."""
        ...


@runtime_checkable
class Reranker(Protocol):
    """Protocol for scoring and re-ordering candidate retrieved chunks based on query relevance."""

    def rerank(self, query: str, chunks: list[Chunk], top_n: int = 5) -> list[Chunk]:
        """Rescore and truncate candidate Chunks to top_n reranked results."""
        ...
