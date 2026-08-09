"""Pluggable LLM provider protocol and concrete provider implementations."""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Sequence

from pydantic import BaseModel, Field

from finreg.config.settings import get_settings
from finreg.rag.rag_models import ContextBlock

logger = logging.getLogger(__name__)


class RawLLMResponse(BaseModel):
    """Raw response output container from LLM generation call."""

    text: str = Field(description="Raw generated text from LLM provider")
    output_tokens: int | None = Field(default=None, description="Reported output token count")


class LLMProvider(ABC):
    """Abstract protocol for LLM provider implementations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider implementation identifier."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model identifier string."""
        pass

    @abstractmethod
    def generate(
        self,
        query: str,
        context_blocks: Sequence[ContextBlock],
        system_instructions: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> RawLLMResponse:
        """Generate response from query and context blocks using LLM."""
        pass


class MockLLMProvider(LLMProvider):
    """Deterministic offline mock LLM provider for unit testing."""

    def __init__(
        self,
        provider_name: str = "mock-provider",
        model_name: str = "mock-gpt-4o-mini",
        custom_response: str | None = None,
    ):
        self._provider_name = provider_name
        self._model_name = model_name
        self._custom_response = custom_response

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        query: str,
        context_blocks: Sequence[ContextBlock],
        system_instructions: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> RawLLMResponse:
        """Produce deterministic mock answers with valid context IDs for offline unit tests."""
        if self._custom_response:
            return RawLLMResponse(text=self._custom_response, output_tokens=42)

        if not context_blocks:
            msg = (
                "The supplied financial regulation context does not contain "
                "sufficient legal evidence to answer the query."
            )
            return RawLLMResponse(text=msg, output_tokens=20)

        if "conflict" in query.lower():
            text = (
                "The supplied regulatory context contains conflicting provisions: "
                "Context [C1] specifies mandatory hedging for all transactions, whereas "
                "Context [C2] allows exemptions for bilateral bank agreements. The supplied "
                "text does not establish which provision controls."
            )
            return RawLLMResponse(text=text, output_tokens=45)

        # Default grounded response citing [C1]
        text = (
            "Berdasarkan ketentuan [C1], transaksi pasar valuta asing untuk lindung nilai "
            "dapat dilaksanakan melalui bank mitra."
        )
        return RawLLMResponse(text=text, output_tokens=30)


class OpenAILLMProvider(LLMProvider):
    """Production OpenAI LLM provider with strict fail-fast error handling."""

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self._model_name = model_name or settings.llm_model
        self._api_key = api_key if api_key is not None else settings.llm_api_key
        self._base_url = settings.llm_base_url

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        query: str,
        context_blocks: Sequence[ContextBlock],
        system_instructions: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> RawLLMResponse:
        """Call OpenAI API endpoint or fail fast with clear exception."""
        if not self._api_key or not self._api_key.strip():
            err_msg = (
                "OpenAI API key missing. Configure LLM_API_KEY environment variable or settings."
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        try:
            import httpx

            url = f"{self._base_url or 'https://api.openai.com/v1'}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }

            # Build user payload with system instructions and formatted prompt
            payload = {
                "model": self._model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": query},
                ],
            }

            start_time = time.perf_counter()
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            elapsed = (time.perf_counter() - start_time) * 1000
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            out_tokens = usage.get("completion_tokens")

            logger.info("OpenAI LLM completion successful in %.2fms.", elapsed)
            return RawLLMResponse(text=content, output_tokens=out_tokens)

        except Exception as exc:
            err_msg = f"OpenAI LLM provider call failed for model '{self._model_name}': {exc}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from exc
