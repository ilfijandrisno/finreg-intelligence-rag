"""Pluggable embedding provider protocol, OpenAI batch provider, and Mock provider."""

import hashlib
import logging
import math
from abc import ABC, abstractmethod

import httpx

from finreg.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract protocol for text embedding providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return embedding model identifier string."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return expected vector dimension length."""
        pass

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate batch vector embeddings for a list of text strings."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """Generate vector embedding for a single search query string."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI API embedding provider with HTTP batching and dimension validation."""

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        dimension: int = 1536,
        api_key: str | None = None,
        base_url: str | None = None,
        batch_size: int = 50,
    ):
        settings = get_settings()
        self._model_name = model_name or settings.embedding_model
        self._dimension = dimension or settings.embedding_dimension
        self._api_key = api_key or settings.embedding_api_key
        self._base_url = base_url or settings.llm_base_url or "https://api.openai.com/v1"
        self._batch_size = batch_size

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch embed texts using OpenAI API endpoint with HTTP POST."""
        if not texts:
            return []

        embeddings: list[list[float]] = []
        url = f"{self._base_url.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=30.0) as client:
            for i in range(0, len(texts), self._batch_size):
                batch = texts[i : i + self._batch_size]
                payload = {
                    "model": self._model_name,
                    "input": batch,
                    "dimensions": self._dimension,
                }
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract vectors sorted by index
                batch_embeddings = [
                    item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])
                ]

                for vec in batch_embeddings:
                    if len(vec) != self._dimension:
                        raise ValueError(
                            f"Vector dimension mismatch: expected {self._dimension}, got {len(vec)}"
                        )
                embeddings.extend(batch_embeddings)

        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed a single search query."""
        results = self.embed_texts([query])
        return results[0]


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic pseudo-vector embedding provider for offline testing and dry-runs."""

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        dimension: int = 1536,
    ):
        self._model_name = model_name
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate L2-normalized pseudo-random vectors derived from text SHA-256 hash."""
        return [self._generate_pseudo_vector(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        """Embed query string using deterministic pseudo-vector generator."""
        return self._generate_pseudo_vector(query)

    def _generate_pseudo_vector(self, text: str) -> list[float]:
        """Create a unit-length normalized float vector from text hash."""
        raw_hash = hashlib.sha256(text.encode("utf-8")).digest()
        vec: list[float] = []

        for i in range(self._dimension):
            byte_val = raw_hash[i % len(raw_hash)]
            # Map byte value (0-255) to float (-1.0 to 1.0)
            val = (byte_val / 127.5) - 1.0 + (i * 0.0001)
            vec.append(val)

        # L2 Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec


def get_embedding_provider(
    provider_name: str | None = None,
    model_name: str | None = None,
    dimension: int | None = None,
    api_key: str | None = None,
) -> EmbeddingProvider:
    """Factory creating configured EmbeddingProvider instance."""
    settings = get_settings()
    p_name = (provider_name or settings.embedding_provider).lower()
    m_name = model_name or settings.embedding_model
    dim = dimension or settings.embedding_dimension

    if p_name in ("mock", "fake", "test"):
        return MockEmbeddingProvider(model_name=m_name, dimension=dim)
    elif p_name in ("openai", "default"):
        key = api_key or settings.embedding_api_key
        if not key or key == "your-api-key-here":
            logger.warning(
                "No valid OpenAI API key provided. Falling back to MockEmbeddingProvider."
            )
            return MockEmbeddingProvider(model_name=m_name, dimension=dim)
        return OpenAIEmbeddingProvider(model_name=m_name, dimension=dim, api_key=key)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider_name}")
