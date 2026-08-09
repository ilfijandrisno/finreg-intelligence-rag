"""Unit tests for EmbeddingProvider protocol implementations."""

import math
from unittest.mock import MagicMock, patch

import pytest

from finreg.vector.providers import (
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)


def test_mock_embedding_provider_dimension_and_normalization() -> None:
    """Verify MockEmbeddingProvider generates L2-normalized 1536-dimensional vectors."""
    provider = MockEmbeddingProvider(model_name="text-embedding-3-small", dimension=1536)

    assert provider.model_name == "text-embedding-3-small"
    assert provider.dimension == 1536

    vectors = provider.embed_texts(["Text A", "Text B"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 1536
    assert len(vectors[1]) == 1536

    # Verify L2 normalization
    norm0 = math.sqrt(sum(v * v for v in vectors[0]))
    assert pytest.approx(norm0, abs=1e-4) == 1.0

    query_vec = provider.embed_query("Sample query")
    assert len(query_vec) == 1536


def test_openai_embedding_provider_batching_and_validation() -> None:
    """Verify OpenAIEmbeddingProvider sends HTTP batch request and validates vector dimensions."""
    provider = OpenAIEmbeddingProvider(
        model_name="text-embedding-3-small",
        dimension=4,
        api_key="test-api-key",
    )

    fake_vec = [0.1, 0.2, 0.3, 0.4]
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"index": 0, "embedding": fake_vec},
            {"index": 1, "embedding": fake_vec},
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        results = provider.embed_texts(["Doc 1", "Doc 2"])
        assert len(results) == 2
        assert results[0] == fake_vec
        assert mock_post.called


def test_get_embedding_provider_factory() -> None:
    """Verify get_embedding_provider creates appropriate provider instance based on settings."""
    p_mock = get_embedding_provider(provider_name="mock")
    assert isinstance(p_mock, MockEmbeddingProvider)

    p_fallback = get_embedding_provider(provider_name="openai", api_key="your-api-key-here")
    assert isinstance(p_fallback, MockEmbeddingProvider)
