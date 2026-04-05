"""
Market researcher agent – deterministic TAM/SAM/SOM estimation.

Uses keyword heuristics and category-based lookup tables to estimate
market size without any external API calls.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MarketResearchResult(BaseModel):
    """Structured output from market research analysis."""

    vertical: str
    tam_estimate: str
    sam_estimate: str
    som_estimate: str
    market_growth: Literal["LOW", "MEDIUM", "HIGH"]
    recommended_channels: list[str] = Field(default_factory=list)
    confidence: Literal["LOW", "MEDIUM", "HIGH"]


# ---------------------------------------------------------------------------
# Market vertical definitions: keywords + TAM/SAM/SOM + growth + channels
# ---------------------------------------------------------------------------
_VERTICAL_RULES: dict[str, dict[str, Any]] = {
    "B2B SaaS": {
        "keywords": (
            "saas",
            "enterprise",
            "b2b",
            "workflow",
            "automation",
            "crm",
            "erp",
            "dashboard",
            "analytics",
            "reporting",
            "team",
            "collaboration",
        ),
        "tam": "$120B",
        "sam": "$18B",
        "som": "$180M",
        "growth": "HIGH",
        "channels": [
            "LinkedIn cold outreach",
            "Product Hunt",
            "G2 / Capterra listings",
            "Content marketing",
            "Partner channel",
        ],
    },
    "AI Tools": {
        "keywords": (
            "ai",
            "llm",
            "gpt",
            "machine learning",
            "ml",
            "copilot",
            "agent",
            "chatbot",
            "generative",
            "neural",
        ),
        "tam": "$200B",
        "sam": "$30B",
        "som": "$300M",
        "growth": "HIGH",
        "channels": [
            "Product Hunt",
            "Hacker News",
            "Dev communities (Discord/Slack)",
            "Twitter/X",
            "Dev.to / technical content",
        ],
    },
    "Developer Tools": {
        "keywords": (
            "developer",
            "engineer",
            "api",
            "sdk",
            "open source",
            "cli",
            "devops",
            "ci/cd",
            "programmer",
            "coder",
            "github",
        ),
        "tam": "$80B",
        "sam": "$12B",
        "som": "$120M",
        "growth": "HIGH",
        "channels": [
            "GitHub / open-source",
            "Hacker News",
            "Product Hunt",
            "Dev communities",
            "Technical blog content",
        ],
    },
    "Marketplace": {
        "keywords": (
            "marketplace",
            "freelancer",
            "gig",
            "vendor",
            "buyer",
            "seller",
            "platform",
            "two-sided",
        ),
        "tam": "$500B",
        "sam": "$50B",
        "som": "$500M",
        "growth": "MEDIUM",
        "channels": [
            "SEO / content marketing",
            "Community building",
            "Influencer partnerships",
            "Direct outreach to early sellers",
            "PR / press",
        ],
    },
    "Education & E-learning": {
        "keywords": (
            "education",
            "course",
            "learning",
            "training",
            "certification",
            "edtech",
            "skill",
            "bootcamp",
            "tutoring",
            "curriculum",
        ),
        "tam": "$350B",
        "sam": "$25B",
        "som": "$250M",
        "growth": "MEDIUM",
        "channels": [
            "SEO / YouTube content",
            "Influencer / instructor partnerships",
            "LinkedIn learning audience",
            "Reddit communities",
            "Email newsletters",
        ],
    },
    "FinTech": {
        "keywords": (
            "fintech",
            "payment",
            "invoice",
            "billing",
            "finance",
            "bank",
            "crypto",
            "wallet",
            "accounting",
            "revenue",
            "expense",
        ),
        "tam": "$300B",
        "sam": "$35B",
        "som": "$350M",
        "growth": "HIGH",
        "channels": [
            "LinkedIn B2B outreach",
            "Partnership with accountants / CFOs",
            "App store / fintech communities",
            "Cold email to finance teams",
            "Industry conferences",
        ],
    },
    "HealthTech": {
        "keywords": (
            "health",
            "medical",
            "wellness",
            "fitness",
            "mental health",
            "telemedicine",
            "patient",
            "clinic",
            "doctor",
            "therapy",
            "nutrition",
        ),
        "tam": "$280B",
        "sam": "$20B",
        "som": "$200M",
        "growth": "HIGH",
        "channels": [
            "Healthcare professional communities",
            "App Store / Google Play",
            "Health influencers",
            "B2B outreach to clinics",
            "SEO / health content",
        ],
    },
    "E-commerce & Retail": {
        "keywords": (
            "ecommerce",
            "e-commerce",
            "shop",
            "retail",
            "store",
            "product",
            "inventory",
            "dropship",
            "shopify",
        ),
        "tam": "$6T",
        "sam": "$600B",
        "som": "$6B",
        "growth": "MEDIUM",
        "channels": [
            "Social media advertising",
            "SEO",
            "Email marketing",
            "Influencer marketing",
            "Marketplace listings (Amazon, Etsy)",
        ],
    },
    "B2C Consumer App": {
        "keywords": (
            "consumer",
            "personal",
            "individual",
            "lifestyle",
            "social",
            "family",
            "mobile",
            "app",
        ),
        "tam": "$400B",
        "sam": "$40B",
        "som": "$400M",
        "growth": "MEDIUM",
        "channels": [
            "TikTok / Instagram / Reels",
            "App Store optimization (ASO)",
            "Influencer partnerships",
            "Viral referral loops",
            "PR / product reviews",
        ],
    },
}

_DEFAULT_VERTICAL = "General Software"
_DEFAULT_MARKET: dict[str, Any] = {
    "tam": "$50B",
    "sam": "$5B",
    "som": "$50M",
    "growth": "MEDIUM",
    "channels": [
        "SEO / content marketing",
        "LinkedIn outreach",
        "Product Hunt",
        "Direct sales",
        "Community building",
    ],
}


class MarketResearchAgent:
    """Deterministic market research agent using keyword/category heuristics."""

    def _detect_vertical(self, combined_text: str) -> tuple[str, dict[str, Any]]:
        """Detect market vertical from combined idea text.

        Returns the vertical name and its associated market data.
        Matches are scored by keyword hit count; highest score wins.
        """
        scores: dict[str, int] = {}
        for vertical, data in _VERTICAL_RULES.items():
            score = sum(1 for kw in data["keywords"] if kw in combined_text)
            if score > 0:
                scores[vertical] = score

        if not scores:
            return _DEFAULT_VERTICAL, _DEFAULT_MARKET

        best_vertical = max(scores, key=lambda k: scores[k])
        return best_vertical, _VERTICAL_RULES[best_vertical]

    def _estimate_confidence(self, combined_text: str, matched_keywords: int) -> Literal["LOW", "MEDIUM", "HIGH"]:
        """Estimate confidence based on text richness and keyword density."""
        word_count = len(combined_text.split())
        if matched_keywords >= 3 and word_count >= 20:
            return "HIGH"
        if matched_keywords >= 1 and word_count >= 10:
            return "MEDIUM"
        return "LOW"

    def research(self, *, idea_brief: dict[str, Any]) -> MarketResearchResult:
        """Run deterministic market research on an idea brief.

        Args:
            idea_brief: Dict with keys like ``title``, ``problem``,
                ``solution``, ``target_user``, ``idea``.

        Returns:
            MarketResearchResult with vertical, TAM/SAM/SOM estimates,
            growth rating, recommended channels, and confidence level.
        """
        title = str(idea_brief.get("title", "")).lower()
        problem = str(idea_brief.get("problem", "")).lower()
        solution = str(idea_brief.get("solution", "")).lower()
        target_user = str(idea_brief.get("target_user", "")).lower()
        idea = str(idea_brief.get("idea", "")).lower()

        combined_text = f"{title} {problem} {solution} {target_user} {idea}".strip()

        vertical, market_data = self._detect_vertical(combined_text)

        matched_keywords = sum(
            1
            for data in _VERTICAL_RULES.values()
            for kw in data["keywords"]
            if kw in combined_text
        )

        confidence = self._estimate_confidence(combined_text, matched_keywords)

        return MarketResearchResult(
            vertical=vertical,
            tam_estimate=market_data["tam"],
            sam_estimate=market_data["sam"],
            som_estimate=market_data["som"],
            market_growth=market_data["growth"],
            recommended_channels=list(market_data["channels"]),
            confidence=confidence,
        )
