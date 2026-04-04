"""
perplexity_client.py – Perplexity API integration for AI-DAN market research.

Uses the Perplexity chat completions API for real-time market research,
competitor analysis, demand validation, and pricing insights.
Falls back to deterministic stubs when no API key is configured.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_PERPLEXITY_BASE_URL = "https://api.perplexity.ai"


class PerplexityClient:
    """Wraps the Perplexity API for AI-DAN research tasks."""

    def __init__(
        self,
        api_key: str,
        model: str = "sonar",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._http: httpx.Client | None = None

    # -- lifecycle -----------------------------------------------------------

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                base_url=_PERPLEXITY_BASE_URL,
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
        return bool(self.api_key and self.api_key != "your-perplexity-api-key-here")

    # -- public API ----------------------------------------------------------

    def research(
        self,
        query: str,
        system: str | None = None,
    ) -> str:
        """Run a research query via Perplexity and return the text response.

        Returns a stub when no API key is configured.
        """
        if not self.is_configured:
            return self._stub_research(query)

        default_system = (
            "You are a market research analyst. Provide concise, data-driven "
            "insights with specific numbers, competitor names, and market trends. "
            "Focus on actionable information for business decision-making."
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system or default_system},
            {"role": "user", "content": query},
        ]

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        try:
            resp = self._client().post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            logger.warning("Perplexity API call failed: %s", exc)
            return self._stub_research(query)

    def market_research(self, idea_title: str, target_user: str) -> dict[str, Any]:
        """Perform structured market research for an idea.

        Returns a dict with market_size, competitors, demand_level,
        pricing_insights, and trends.
        """
        query = (
            f"Market research for a product called '{idea_title}' "
            f"targeting '{target_user}'.\n\n"
            "Provide:\n"
            "1. Estimated market size (TAM/SAM/SOM)\n"
            "2. Top 3-5 existing competitors with their pricing\n"
            "3. Current demand level (HIGH/MEDIUM/LOW) with evidence\n"
            "4. Pricing insights and willingness-to-pay data\n"
            "5. Key market trends\n\n"
            "Be specific with numbers and names."
        )

        raw = self.research(query)

        return {
            "raw_research": raw,
            "idea_title": idea_title,
            "target_user": target_user,
            "source": "perplexity" if self.is_configured else "stub",
        }

    def competitor_analysis(self, idea_title: str, domain: str) -> dict[str, Any]:
        """Analyse competitors for a given idea and domain."""
        query = (
            f"Competitor analysis for '{idea_title}' in the '{domain}' space.\n\n"
            "List:\n"
            "1. Direct competitors (name, pricing, key features)\n"
            "2. Indirect competitors\n"
            "3. Market gaps and opportunities\n"
            "4. Differentiation strategies\n"
            "5. Market saturation level (HIGH/MEDIUM/LOW)\n\n"
            "Be specific with names, URLs, and pricing."
        )

        raw = self.research(query)

        return {
            "raw_analysis": raw,
            "idea_title": idea_title,
            "domain": domain,
            "source": "perplexity" if self.is_configured else "stub",
        }

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _stub_research(query: str) -> str:
        """Return deterministic stub research data."""
        return (
            f"[Research stub – Perplexity not configured]\n"
            f"Query: {query[:200]}\n\n"
            "Market indicators (estimated):\n"
            "- Demand: MEDIUM (based on general market patterns)\n"
            "- Competition: MODERATE (typical for SaaS/digital products)\n"
            "- Pricing benchmark: $19-$99/month for SaaS\n"
            "- Market trend: Growing adoption of AI-powered tools\n"
            "- Key risk: Market saturation in broad categories\n\n"
            "Note: Configure PERPLEXITY_API_KEY for real-time market data."
        )
