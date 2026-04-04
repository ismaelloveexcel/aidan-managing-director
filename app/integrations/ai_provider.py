"""
ai_provider.py – Unified AI provider for AI-DAN.

Coordinates OpenAI (reasoning/output) and Perplexity (research) to provide
a single interface for AI-powered operations across the system.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.integrations.openai_client import OpenAIClient
from app.integrations.perplexity_client import PerplexityClient

logger = logging.getLogger(__name__)

# System prompt for AI-DAN's reasoning engine
_AIDAN_SYSTEM = (
    "You are AI-DAN, an AI Managing Director that evaluates business ideas.\n"
    "You are direct, data-driven, and commercially focused.\n"
    "You challenge weak ideas and amplify strong ones.\n"
    "Every output must include: clear business idea, target user, "
    "monetization method, pricing suggestion, and distribution plan.\n"
    "Think like a sharp venture investor with execution capability."
)


class AIProvider:
    """Unified AI provider coordinating OpenAI and Perplexity."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        perplexity_client: PerplexityClient,
    ) -> None:
        self.openai = openai_client
        self.perplexity = perplexity_client

    @property
    def ai_enabled(self) -> bool:
        """Return True if at least OpenAI is configured."""
        return self.openai.is_configured

    @property
    def research_enabled(self) -> bool:
        """Return True if Perplexity is configured for research."""
        return self.perplexity.is_configured

    def close(self) -> None:
        """Release resources held by both clients."""
        self.openai.close()
        self.perplexity.close()

    # -- High-level operations -----------------------------------------------

    def analyze_idea(
        self,
        user_input: str,
        research_context: str = "",
    ) -> dict[str, Any]:
        """Run AI-powered idea analysis and return structured output.

        Uses Perplexity for research context (if available), then OpenAI
        for reasoning and structured output generation.
        """
        # Step 1: Research via Perplexity (if configured)
        if not research_context and self.research_enabled:
            research_context = self.perplexity.research(
                f"Market research and competitive analysis for this business idea: {user_input}"
            )

        # Step 2: Structured analysis via OpenAI
        prompt = self._build_analysis_prompt(user_input, research_context)
        result = self.openai.chat_json(
            prompt=prompt,
            system=_AIDAN_SYSTEM,
            temperature=0.5,
            max_tokens=3000,
        )

        if result.get("stub"):
            return self._stub_analysis(user_input)

        return result

    def enrich_idea(
        self,
        title: str,
        target_user: str,
        problem: str,
        monetization_path: str,
    ) -> dict[str, Any]:
        """Enrich an existing idea with AI-generated insights.

        Adds market context, refined pricing, distribution strategy,
        and competitive positioning.
        """
        # Research
        research = ""
        if self.research_enabled:
            research_data = self.perplexity.market_research(title, target_user)
            research = research_data.get("raw_research", "")

        prompt = (
            f"Enrich this business idea with actionable intelligence:\n\n"
            f"Title: {title}\n"
            f"Target User: {target_user}\n"
            f"Problem: {problem}\n"
            f"Monetization: {monetization_path}\n\n"
        )

        if research:
            prompt += f"Market Research Data:\n{research}\n\n"

        prompt += (
            "Return a JSON object with these fields:\n"
            "- market_insight: string (key market finding)\n"
            "- refined_pricing: string (specific pricing recommendation)\n"
            "- distribution_channel: string (best channel to reach target users)\n"
            "- first_10_users: string (specific plan to get first 10 paying users)\n"
            "- competitive_edge: string (what makes this different)\n"
            "- revenue_timeline: string (realistic timeline to first revenue)\n"
            "- risk_assessment: string (top risk and mitigation)\n"
        )

        result = self.openai.chat_json(prompt=prompt, system=_AIDAN_SYSTEM)

        if result.get("stub"):
            return {
                "market_insight": "Configure AI keys for real market insights.",
                "refined_pricing": monetization_path,
                "distribution_channel": "LinkedIn + direct outreach",
                "first_10_users": "Manual outreach to target audience communities",
                "competitive_edge": "Speed to market and focused feature set",
                "revenue_timeline": "4-8 weeks post-launch",
                "risk_assessment": "Market validation needed before scaling",
            }

        return result

    def generate_business_verdict(
        self,
        idea_summary: str,
        score: float,
        research_context: str = "",
    ) -> dict[str, Any]:
        """Generate an AI-powered business verdict for an evaluated idea."""
        prompt = (
            f"Business verdict for this idea:\n\n"
            f"{idea_summary}\n\n"
            f"Evaluation score: {score}/10\n\n"
        )

        if research_context:
            prompt += f"Market Research:\n{research_context}\n\n"

        prompt += (
            "Return a JSON object with:\n"
            "- verdict: 'APPROVE' | 'HOLD' | 'REJECT'\n"
            "- why_now: string (why this is or isn't the right time)\n"
            "- main_risk: string (biggest risk)\n"
            "- recommended_next_move: string (specific action)\n"
            "- monetization_method: string (best revenue approach)\n"
            "- pricing_suggestion: string (specific price point)\n"
            "- distribution_plan: string (how to reach users)\n"
        )

        result = self.openai.chat_json(prompt=prompt, system=_AIDAN_SYSTEM)

        if result.get("stub"):
            verdict = "APPROVE" if score >= 8 else ("HOLD" if score >= 6 else "REJECT")
            return {
                "verdict": verdict,
                "why_now": f"Score {score}/10 — {'strong enough to proceed' if score >= 8 else 'needs improvement'}.",
                "main_risk": "Market validation still required.",
                "recommended_next_move": "Validate with 5 potential customers before building.",
                "monetization_method": "SaaS subscription",
                "pricing_suggestion": "$29-$99/month",
                "distribution_plan": "Content marketing + direct outreach",
            }

        return result

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _build_analysis_prompt(user_input: str, research: str) -> str:
        """Build the full analysis prompt."""
        prompt = (
            f"Analyze this business idea and provide a complete assessment:\n\n"
            f"User Input: {user_input}\n\n"
        )

        if research:
            prompt += f"Market Research Data:\n{research}\n\n"

        prompt += (
            "Return a JSON object with ALL of these fields:\n"
            "{\n"
            '  "title": "concise product name",\n'
            '  "problem": "specific problem being solved",\n'
            '  "target_user": "specific target audience",\n'
            '  "solution": "proposed solution",\n'
            '  "monetization_method": "specific revenue model",\n'
            '  "pricing_suggestion": "specific price point or range",\n'
            '  "distribution_plan": "how to reach first users",\n'
            '  "first_10_users": "specific plan to get 10 paying users",\n'
            '  "competitive_edge": "key differentiator",\n'
            '  "market_size": "estimated addressable market",\n'
            '  "feasibility_score": 0-10,\n'
            '  "profitability_score": 0-10,\n'
            '  "speed_score": 0-10,\n'
            '  "competition_score": 0-10,\n'
            '  "overall_score": 0-10,\n'
            '  "verdict": "APPROVE or HOLD or REJECT",\n'
            '  "why_now": "reason for timing",\n'
            '  "main_risk": "top risk",\n'
            '  "recommended_next_move": "specific next action"\n'
            "}"
        )

        return prompt

    @staticmethod
    def _stub_analysis(user_input: str) -> dict[str, Any]:
        """Return a deterministic stub analysis."""
        return {
            "title": f"Business idea from: {user_input[:50]}",
            "problem": "Problem identified from user input",
            "target_user": "Target users in the described domain",
            "solution": "AI-powered solution addressing the core problem",
            "monetization_method": "SaaS subscription model",
            "pricing_suggestion": "$29-$99/month",
            "distribution_plan": "Content marketing + community outreach",
            "first_10_users": "Direct outreach to target communities",
            "competitive_edge": "AI-powered automation and simplicity",
            "market_size": "Estimated $1B+ addressable market",
            "feasibility_score": 7,
            "profitability_score": 7,
            "speed_score": 8,
            "competition_score": 6,
            "overall_score": 7,
            "verdict": "HOLD",
            "why_now": "Growing demand for AI-powered tools in this space.",
            "main_risk": "Market validation needed before scaling.",
            "recommended_next_move": "Validate with 5 potential customers.",
            "stub": True,
        }
