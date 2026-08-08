"""Protocol interface for LLM text generation and RAG answer synthesis."""

from typing import Any, Protocol, runtime_checkable

from finreg.domain.models import Chunk, Citation


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for interfacing with Large Language Model inference providers."""

    def generate(self, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> str:
        """Generate text completion from a prompt and optional system instruction."""
        ...

    def generate_grounded_answer(
        self,
        query: str,
        context_chunks: list[Chunk],
        system_prompt: str | None = None,
    ) -> tuple[str, list[Citation]]:
        """Synthesize answer and citations from retrieved regulatory context chunks."""
        ...
