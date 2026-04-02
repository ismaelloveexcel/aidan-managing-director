"""
llm_client.py – LLM provider integration for AI-DAN.

Provides a typed client for interacting with large language model APIs
(e.g. OpenAI, Anthropic) used by the reasoning and planning layers.
"""

from typing import Any


class LLMClient:
    """
    Wraps LLM provider APIs to provide a consistent interface for text
    generation, embeddings, and function calling.

    Business logic to be implemented in a future iteration.
    """

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        """
        Initialise the LLM client.

        Args:
            api_key: Provider API key.
            model: Model identifier (e.g. "gpt-4o", "claude-3-5-sonnet").
            base_url: Optional override for the provider base URL.
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def complete(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        """
        Generate a text completion for the given prompt.

        Args:
            prompt: User-facing input prompt.
            system: Optional system-level instruction.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The model's generated text response.
        """
        raise NotImplementedError

    def embed(self, text: str) -> list[float]:
        """
        Generate a vector embedding for the given text.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as a list of floats.
        """
        raise NotImplementedError

    def function_call(
        self,
        prompt: str,
        functions: list[dict[str, Any]],
        system: str | None = None,
    ) -> dict[str, Any]:
        """
        Invoke function-calling mode with the LLM.

        Args:
            prompt: User-facing input prompt.
            functions: List of function schemas available to the model.
            system: Optional system-level instruction.

        Returns:
            The model's function-call result as a dictionary.
        """
        raise NotImplementedError
