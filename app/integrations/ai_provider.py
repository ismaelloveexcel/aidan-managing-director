"""
ai_provider.py – Unified AI provider for AI-DAN.

Coordinates multiple AI models (Claude, OpenAI, Groq, Deepseek, Grok)
and Perplexity for research.  Provides a single interface for all
AI-powered operations across the system.

Model priority for reasoning tasks:
  Claude (best quality) > OpenAI > Groq (fast/free) > Deepseek (cheap)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.integrations.openai_client import OpenAIClient
from app.integrations.perplexity_client import PerplexityClient

logger = logging.getLogger(__name__)

# Scoring thresholds for verdict determination
APPROVE_THRESHOLD = 8
HOLD_THRESHOLD = 6

# System prompt for idea analysis / scoring
_AIDAN_SYSTEM = (
    "You are AI-DAN, an AI Managing Director that evaluates business ideas.\n"
    "You are direct, data-driven, and commercially focused.\n"
    "You challenge weak ideas and amplify strong ones.\n"
    "Every output must include: clear business idea, target user, "
    "monetization method, pricing suggestion, and distribution plan.\n"
    "Think like a sharp venture investor with execution capability."
)

# System prompt for the conversational AI-DAN advisor
_AIDAN_CHAT_SYSTEM = """\
You are AI-DAN, a no-bullshit venture-loop advisor to a solo founder.

PERSONALITY:
- Brutally honest. Never flatter or say what people want to hear.
- Push back hard on weak ideas. Get genuinely excited about good ones.
- Think like a sharp investor who can also build fast.
- One focus: make money FAST with MINIMUM complexity.
- The founder is currently between jobs. Urgency is REAL. Treat it that way.
- Short punchy answers unless depth is needed.
- Specific beats generic always: "post to r/SaaS" not "consider social media."
- Celebrate real wins. Call out bad ideas clearly and offer a better alternative.
- Occasional humor is fine. Stay real, stay direct.

EVALUATION FRAMEWORK (apply mentally to every idea):
\u2192 Who EXACTLY pays? \u2192 How much per month? \u2192 How fast to first sale?
\u2192 How hard to build in days (not months)? \u2192 What kills this?

CAPABILITIES:
- Score and dissect any business idea ruthlessly
- Suggest fastest path to first dollar
- Generate launch content (X posts, outreach, landing page copy)
- Review project status and give ONE clear next action
- Prioritize and kill ideas in the pipeline

GOLDEN RULE: Every response must end with a specific next step or a direct question.
Never end with vague advice. End with \"So: [specific action]\" or ask something pointed."""


class AIProvider:
    """Unified AI provider coordinating multiple models."""

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

    # -- Conversational AI-DAN ---------------------------------------------------

    def aidan_chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Chat with AI-DAN using the best available model.

        Returns (reply_text, model_name_used).
        Tries models in order: Claude > OpenAI > Groq > Deepseek > Grok > Stub.
        """
        from app.core.config import get_settings
        settings = get_settings()

        # Build message list
        msgs: list[dict[str, str]] = []
        if context:
            ctx_snippet = json.dumps(context, indent=2)[:800]
            msgs.append({"role": "user", "content": f"Context: {ctx_snippet}"})
            msgs.append({"role": "assistant", "content": "Got it, I have your context."})

        for h in (history or []):
            if h.get("role") and h.get("content"):
                msgs.append({"role": h["role"], "content": h["content"]})

        msgs.append({"role": "user", "content": message})

        # 1. Claude (Anthropic)
        if settings.anthropic_api_key:
            reply = self._call_anthropic(
                msgs,
                settings.anthropic_api_key,
                settings.anthropic_model,
            )
            if reply:
                return reply, f"claude ({settings.anthropic_model})"

        # 2. OpenAI
        if self.openai.is_configured:
            try:
                reply_raw = self.openai.chat(
                    prompt=message,
                    system=_AIDAN_CHAT_SYSTEM,
                    temperature=0.8,
                    max_tokens=1000,
                )
                if reply_raw and not str(reply_raw).startswith("[stub"):
                    return str(reply_raw), f"openai ({self.openai.model})"
            except Exception as exc:
                logger.warning("OpenAI chat failed: %s", exc)

        # 3. Groq (fast, generous free tier)
        if settings.groq_api_key:
            reply = self._call_openai_compatible(
                msgs,
                settings.groq_api_key,
                "https://api.groq.com/openai/v1/chat/completions",
                settings.groq_model,
            )
            if reply:
                return reply, f"groq ({settings.groq_model})"

        # 4. Deepseek (cheap, great for coding / analysis)
        if settings.deepseek_api_key:
            reply = self._call_openai_compatible(
                msgs,
                settings.deepseek_api_key,
                "https://api.deepseek.com/v1/chat/completions",
                settings.deepseek_model,
            )
            if reply:
                return reply, f"deepseek ({settings.deepseek_model})"

        # 5. xAI Grok (real-time web access)
        if settings.grok_api_key:
            reply = self._call_openai_compatible(
                msgs,
                settings.grok_api_key,
                "https://api.x.ai/v1/chat/completions",
                settings.grok_model,
            )
            if reply:
                return reply, f"grok ({settings.grok_model})"

        # Fallback stub
        return (
            "\u26a0\ufe0f No AI model is configured yet.\n\n"
            "To activate me, add ONE of these to your Vercel environment variables:\n"
            "\u2022 ANTHROPIC_API_KEY (recommended \u2014 Claude)\n"
            "\u2022 OPENAI_API_KEY (GPT-4o)\n"
            "\u2022 GROQ_API_KEY (free tier, fast)\n"
            "\u2022 DEEPSEEK_API_KEY (cheapest option)\n\n"
            "Once added, redeploy and I'll be fully operational.",
            "stub",
        )

    def _call_anthropic(
        self,
        messages: list[dict[str, str]],
        api_key: str,
        model: str,
    ) -> str | None:
        """Call Anthropic Claude API and return the reply text."""
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 1024,
                        "system": _AIDAN_CHAT_SYSTEM,
                        "messages": messages,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["content"][0]["text"]
        except Exception as exc:
            logger.warning("Anthropic call failed: %s", exc)
            return None

    def _call_openai_compatible(
        self,
        messages: list[dict[str, str]],
        api_key: str,
        endpoint: str,
        model: str,
    ) -> str | None:
        """Call any OpenAI-compatible API (Groq, Deepseek, xAI)."""
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": _AIDAN_CHAT_SYSTEM},
                            *messages,
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.8,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("OpenAI-compatible call failed (%s): %s", endpoint, exc)
            return None

    # -- Idea analysis (existing public API) -----------------------------------

    def analyze_idea(
        self,
        user_input: str,
        research_context: str = "",
    ) -> dict[str, Any]:
        """Run AI-powered idea analysis and return structured output."""
        if not research_context and self.research_enabled:
            research_context = self.perplexity.research(
                f"Market research and competitive analysis for this business idea: {user_input}"
            )

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
        """Enrich an existing idea with AI-generated insights."""
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
            "- market_insight: string\n"
            "- refined_pricing: string\n"
            "- distribution_channel: string\n"
            "- first_10_users: string\n"
            "- competitive_edge: string\n"
            "- revenue_timeline: string\n"
            "- risk_assessment: string\n"
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
            "- why_now: string\n"
            "- main_risk: string\n"
            "- recommended_next_move: string\n"
            "- monetization_method: string\n"
            "- pricing_suggestion: string\n"
            "- distribution_plan: string\n"
        )

        result = self.openai.chat_json(prompt=prompt, system=_AIDAN_SYSTEM)

        if result.get("stub"):
            if score >= APPROVE_THRESHOLD:
                verdict = "APPROVE"
            elif score >= HOLD_THRESHOLD:
                verdict = "HOLD"
            else:
                verdict = "REJECT"
            return {
                "verdict": verdict,
                "why_now": f"Score {score}/10 \u2014 {'strong enough to proceed' if score >= APPROVE_THRESHOLD else 'needs improvement'}.",
                "main_risk": "Market validation still required.",
                "recommended_next_move": "Validate with 5 potential customers before building.",
                "monetization_method": "SaaS subscription",
                "pricing_suggestion": "$29-$99/month",
                "distribution_plan": "Content marketing + direct outreach",
            }

        return result

    # -- Private helpers -------------------------------------------------------

    @staticmethod
    def _build_analysis_prompt(user_input: str, research: str) -> str:
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
