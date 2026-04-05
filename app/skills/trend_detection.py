"""
trend_detection.py – Keyword-based technology trend detection skill.

Scans idea text for trending technology and market terms, returns a
structured ``TrendDetectionResult`` with detected trends, an alignment
score, and an optional pivot recommendation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Trend keyword lookup table: category -> keywords
# ---------------------------------------------------------------------------
_TREND_KEYWORDS: dict[str, list[str]] = {
    "AI / Machine Learning": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "ml",
        "llm",
        "gpt",
        "generative ai",
        "neural network",
        "deep learning",
        "copilot",
        "agent",
        "chatbot",
        "nlp",
        "computer vision",
    ],
    "Blockchain / Web3": [
        "blockchain",
        "web3",
        "crypto",
        "nft",
        "defi",
        "smart contract",
        "dao",
        "token",
        "ethereum",
        "solana",
        "decentralized",
    ],
    "AR / VR / Spatial Computing": [
        "ar",
        "vr",
        "augmented reality",
        "virtual reality",
        "mixed reality",
        "spatial computing",
        "metaverse",
        "apple vision",
        "headset",
        "immersive",
    ],
    "Sustainability / CleanTech": [
        "sustainability",
        "green",
        "carbon",
        "climate",
        "renewable",
        "cleantech",
        "net zero",
        "esg",
        "circular economy",
        "solar",
        "electric vehicle",
        "ev",
    ],
    "No-Code / Low-Code": [
        "no-code",
        "nocode",
        "low-code",
        "lowcode",
        "drag and drop",
        "visual builder",
        "workflow automation",
        "zapier",
        "make.com",
    ],
    "Remote Work / Future of Work": [
        "remote work",
        "hybrid work",
        "async",
        "distributed team",
        "work from home",
        "virtual office",
        "team collaboration",
        "digital nomad",
    ],
    "Health & Wellness Tech": [
        "mental health",
        "wellness",
        "wearable",
        "telehealth",
        "telemedicine",
        "biometric",
        "personalized health",
        "longevity",
        "gut health",
    ],
    "Creator Economy": [
        "creator",
        "creator economy",
        "influencer",
        "newsletter",
        "substack",
        "patreon",
        "monetize audience",
        "community led",
        "fan engagement",
    ],
    "FinTech / Embedded Finance": [
        "embedded finance",
        "buy now pay later",
        "bnpl",
        "open banking",
        "neobank",
        "crypto payments",
        "cross-border payment",
        "micro-lending",
    ],
    "Cybersecurity": [
        "cybersecurity",
        "zero trust",
        "devsecops",
        "threat detection",
        "soc",
        "pen test",
        "vulnerability",
        "data privacy",
        "gdpr",
        "compliance",
    ],
}

# Pivot suggestions keyed by missing high-value trends for generic ideas
_PIVOT_SUGGESTIONS: dict[str, str] = {
    "AI / Machine Learning": "Consider adding an AI-powered feature to increase perceived value.",
    "Sustainability / CleanTech": "A sustainability angle could differentiate in a crowded market.",
    "No-Code / Low-Code": "A no-code interface could dramatically expand your addressable market.",
    "Creator Economy": "Targeting creators or influencers could accelerate viral growth.",
}


class TrendDetectionResult(BaseModel):
    """Structured output from the trend detection skill."""

    detected_trends: list[str] = Field(
        default_factory=list,
        description="Trend categories detected in the idea text",
    )
    trend_alignment_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How well the idea aligns with current trends (0–1)",
    )
    recommended_pivot: str = Field(
        default="",
        description="Optional pivot suggestion if trend alignment is weak",
    )


def detect_trends(idea_text: str, target_user: str) -> TrendDetectionResult:
    """Detect trending technology/market themes in an idea.

    Performs keyword-based matching against a lookup table of trending
    categories.  Returns detected trends, a normalized alignment score
    (0–1), and an optional pivot recommendation for low-scoring ideas.

    Args:
        idea_text: The idea title or description.
        target_user: The intended user / customer segment.

    Returns:
        ``TrendDetectionResult`` with ``detected_trends``,
        ``trend_alignment_score``, and ``recommended_pivot``.
    """
    combined = f"{idea_text} {target_user}".lower()

    detected: list[str] = []
    for category, keywords in _TREND_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            detected.append(category)

    total_categories = len(_TREND_KEYWORDS)
    alignment_score = round(min(1.0, len(detected) / max(1, total_categories // 3)), 2)

    # Suggest a pivot only when alignment is weak (below 0.35)
    pivot = ""
    if alignment_score < 0.35 and not detected:
        # Recommend the first high-value trend not already present
        for trend, suggestion in _PIVOT_SUGGESTIONS.items():
            if trend not in detected:
                pivot = suggestion
                break

    return TrendDetectionResult(
        detected_trends=detected,
        trend_alignment_score=alignment_score,
        recommended_pivot=pivot,
    )
