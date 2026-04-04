"""
openai_client.py – Real OpenAI API integration for AI-DAN.

Provides async-compatible client for text generation, structured output,
and reasoning tasks using the OpenAI Chat Completions API.
Falls back to stub responses when no API key is configured.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OPENAI_BASE_URL = "https://api.openai.com/v1"


_PLACEHOLDER_KEYS = {"", "your-openai-api-key-here"}


class OpenAIClient:
    """Wraps the OpenAI Chat Completions API for AI-DAN reasoning tasks."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or _OPENAI_BASE_URL).rstrip("/")
        self._http: httpx.Client | None = None

    # -- lifecycle -----------------------------------------------------------

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=90.0,
            )
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    @property
    def is_configured(self) -> bool:
        """Return True when a real API key is available."""
        return bool(self.api_key) and self.api_key not in _PLACEHOLDER_KEYS

    # -- public API ----------------------------------------------------------

    def chat(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Send a chat completion request and return the assistant message.

        Returns a stub response when no API key is configured.
        """
        if not self.is_configured:
            return self._stub_response(prompt)

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = self._client().post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            logger.warning("OpenAI API call failed: %s", exc)
            return self._stub_response(prompt)

    def chat_json(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 3000,
    ) -> dict[str, Any]:
        """Send a chat request expecting JSON output.

        Instructs the model to return valid JSON via system prompt
        and ``response_format``.
        """
        json_system = (system or "") + "\nYou MUST respond with valid JSON only. No markdown, no explanation."

        if not self.is_configured:
            return {"stub": True, "text": self._stub_response(prompt)}

        messages: list[dict[str, str]] = [
            {"role": "system", "content": json_system},
            {"role": "user", "content": prompt},
        ]

        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            resp = self._client().post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.warning("OpenAI JSON call failed: %s", exc)
            return {"stub": True, "error": str(exc)}

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _stub_response(prompt: str) -> str:
        """Return a deterministic stub when no API key is available."""
        return f"[AI stub – OpenAI not configured] Received: {prompt[:120]}"
