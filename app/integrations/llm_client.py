"""
llm_client.py – LLM provider integration for AI-DAN.

Provides a typed client for interacting with large language model APIs
(e.g. OpenAI, Anthropic) used by the reasoning and planning layers.

All methods are currently **stub implementations** that return
realistic placeholder data.  Real HTTP calls (via ``httpx``) will
replace the stubs once LLM credentials are provisioned.
"""

from __future__ import annotations

from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Model routing table – maps high-level intent tags to concrete model IDs.
# Extend this as new providers / models are onboarded.
# ---------------------------------------------------------------------------
_MODEL_ROUTES: dict[str, str] = {
    "fast": "gpt-4o-mini",
    "default": "gpt-4o",
    "reasoning": "gpt-4o",
    "creative": "gpt-4o",
    "embedding": "text-embedding-3-small",
}


class LLMClient:
    """
    Wraps LLM provider APIs to provide a consistent interface for text
    generation, embeddings, and function calling.

    Every public method returns structured placeholder data so that
    callers can be developed and tested before live credentials are
    available.
    """

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        """
        Initialise the LLM client.

        Args:
            api_key: Provider API key.
            model: Default model identifier (e.g. ``"gpt-4o"``).
            base_url: Optional override for the provider base URL.
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._http_client: httpx.Client | None = None

    # -- lifecycle --------------------------------------------------------------

    def _client(self) -> httpx.Client:
        """
        Return the shared ``httpx.Client`` instance.

        The client is created lazily and reused for the lifetime of
        this ``LLMClient``.  Call :meth:`close` when the client is no
        longer needed to release network resources.
        """
        if self._http_client is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            self._http_client = httpx.Client(
                base_url=self.base_url or "https://api.openai.com/v1",
                headers=headers,
                timeout=60.0,
            )
        return self._http_client

    def close(self) -> None:
        """Close the underlying HTTP client, releasing held resources."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> LLMClient:
        """Allow ``LLMClient`` to be used as a context manager."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Ensure the underlying client is closed when leaving the context."""
        self.close()

    # -- helpers ----------------------------------------------------------------

    # -- public API -------------------------------------------------------------

    def generate_text(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate text from the LLM and return a structured response.

        This is the primary text-generation entry point.  It wraps the
        provider's chat-completion API and returns both the generated
        text and metadata about the call.

        Args:
            prompt: User-facing input prompt.
            system: Optional system-level instruction.
            model: Model override; falls back to the client default.
            **kwargs: Additional provider-specific parameters.

        Returns:
            A dictionary containing at least ``"text"``, ``"model"``,
            and ``"usage"`` keys.
        """
        resolved_model = model or self.model
        return {
            "text": f"[stub] Response to: {prompt[:80]}",
            "model": resolved_model,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "stub": True,
        }

    def route_model(self, intent: str) -> str:
        """
        Select the most appropriate model for a given intent tag.

        The routing table allows the reasoning layer to request a model
        by *purpose* (e.g. ``"fast"``, ``"reasoning"``) rather than by
        a concrete model identifier, making it easy to swap providers.

        Args:
            intent: High-level intent tag (e.g. ``"fast"``,
                ``"default"``, ``"reasoning"``, ``"creative"``,
                ``"embedding"``).

        Returns:
            The concrete model identifier string.
        """
        return _MODEL_ROUTES.get(intent, self.model)

    # -- additional capabilities ------------------------------------------------

    def complete(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        """
        Generate a text completion for the given prompt.

        Convenience wrapper around :meth:`generate_text` that returns
        only the generated string.

        Args:
            prompt: User-facing input prompt.
            system: Optional system-level instruction.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The model's generated text response.
        """
        result = self.generate_text(prompt, system=system, **kwargs)
        return result["text"]

    def embed(self, text: str) -> list[float]:
        """
        Generate a vector embedding for the given text.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as a list of floats (stub: 8-dim zeros).
        """
        return [0.0] * 8

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
        if not functions:
            raise ValueError(
                "The 'functions' parameter requires at least one function schema."
            )

        fn_name = self._extract_function_name(functions[0])
        if not fn_name:
            raise ValueError(
                "Invalid function schema: missing 'name'. "
                "Expected either {'name': ...} or "
                "{'type': 'function', 'function': {'name': ...}}."
            )

        return {
            "function": fn_name,
            "arguments": {},
            "stub": True,
        }

    # -- private helpers --------------------------------------------------------

    @staticmethod
    def _extract_function_name(schema: dict[str, Any]) -> str | None:
        """Extract the function name from a function-call schema.

        Supports both simple ``{"name": "..."}`` schemas and
        provider-style ``{"type": "function", "function": {"name": "..."}}``
        schemas.

        Args:
            schema: A single function schema dictionary.

        Returns:
            The function name, or ``None`` if it could not be resolved.
        """
        if not isinstance(schema, dict):
            return None

        # Simple {"name": "..."} format
        name_direct = schema.get("name")
        if isinstance(name_direct, str) and name_direct:
            return name_direct

        # Provider-style {"type": "function", "function": {"name": "..."}}
        nested = schema.get("function")
        if isinstance(nested, dict):
            nested_name = nested.get("name")
            if isinstance(nested_name, str) and nested_name:
                return nested_name

        return None
