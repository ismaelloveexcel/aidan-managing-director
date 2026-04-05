# app/skills/__init__.py
"""Skills package – reusable capability modules for agent invocation."""

from app.skills.competitor_analysis import CompetitorAnalysisResult, analyze_competitors
from app.skills.market_research import MarketResearchSkillResult, research_market
from app.skills.trend_detection import TrendDetectionResult, detect_trends

__all__ = [
    "analyze_competitors",
    "CompetitorAnalysisResult",
    "detect_trends",
    "research_market",
    "MarketResearchSkillResult",
    "TrendDetectionResult",
]
