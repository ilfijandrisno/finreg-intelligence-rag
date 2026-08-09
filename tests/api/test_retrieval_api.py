"""API integration tests for /api/v1/retrieval/search and /api/v1/retrieval/rerank endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient

from finreg.api.main import app
from finreg.hybrid.hybrid_models import HybridSearchResult
from finreg.reranking.rerank_models import RerankedSearchResult


def _make_hybrid_result(path: str, text: str) -> HybridSearchResult:
    return HybridSearchResult(
        fused_score=0.032,
        dense_rank=1,
        lexical_rank=2,
        dense_score=0.85,
        lexical_score=3.5,
        retrieval_method="hybrid",
        chunk_id=uuid4(),
        source_node_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test Title",
        structural_path=path,
        chunk_text=text,
        contextual_text=f"Header\n\n{text}",
        page_start=1,
        page_end=1,
        sequence=1,
    )


def _make_reranked_result(path: str, text: str) -> RerankedSearchResult:
    return RerankedSearchResult(
        rerank_score=0.92,
        rerank_rank=1,
        fused_score=0.032,
        dense_rank=1,
        lexical_rank=2,
        dense_score=0.85,
        lexical_score=3.5,
        retrieval_method="hybrid",
        chunk_id=uuid4(),
        source_node_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        source="BI",
        regulation_type="PBI",
        regulation_number="20/2026",
        title="Test Title",
        structural_path=path,
        chunk_text=text,
        contextual_text=f"Header\n\n{text}",
        page_start=1,
        page_end=1,
        sequence=1,
    )


class MockHybridService:
    def search(self, **kwargs):
        return [_make_hybrid_result("Pasal 1", "Ketentuan valas.")], None


class MockRerankingService:
    def search(self, **kwargs):
        return [_make_reranked_result("Pasal 1", "Ketentuan valas.")], None


def test_hybrid_search_api_success() -> None:
    """Verify POST /api/v1/retrieval/search returns Phase 4C Hybrid RRF search results."""
    app.state.hybrid_service = MockHybridService()
    app.state.reranking_service = None
    client = TestClient(app)

    payload = {"query": "transaksi valas", "top_k": 5}
    response = client.post("/api/v1/retrieval/search", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "transaksi valas"
    assert data["total_results"] == 1
    assert data["results"][0]["fused_score"] == 0.032
    assert "X-Request-ID" in response.headers


def test_rerank_api_success() -> None:
    """Verify POST /api/v1/retrieval/rerank returns Neural Cross-Encoder reranked results."""
    app.state.hybrid_service = None
    app.state.reranking_service = MockRerankingService()
    client = TestClient(app)

    payload = {"query": "transaksi valas", "top_n": 5}
    response = client.post("/api/v1/retrieval/rerank", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "transaksi valas"
    assert data["total_results"] == 1
    assert data["results"][0]["rerank_score"] == 0.92
    assert "X-Request-ID" in response.headers
