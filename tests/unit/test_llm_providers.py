"""Unit tests for MockLLMProvider determinism and OpenAILLMProvider fail-fast exception handling."""

import pytest

from finreg.rag.providers import MockLLMProvider, OpenAILLMProvider


def test_mock_llm_provider_behavior() -> None:
    """Verify MockLLMProvider generates deterministic responses and handles empty contexts."""
    provider = MockLLMProvider()
    assert provider.provider_name == "mock-provider"
    assert provider.model_name == "mock-gpt-4o-mini"

    empty_resp = provider.generate("query", context_blocks=[], system_instructions="sys")
    assert "does not contain sufficient legal evidence" in empty_resp.text


def test_openai_llm_provider_fail_fast_without_api_key() -> None:
    """Verify OpenAILLMProvider raises RuntimeError immediately if LLM_API_KEY is missing."""
    provider = OpenAILLMProvider(api_key="")
    with pytest.raises(RuntimeError, match="OpenAI API key missing"):
        provider.generate("query", context_blocks=[], system_instructions="sys")
