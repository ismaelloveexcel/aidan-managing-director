# app/skills/__init__.py
"""Reusable skill modules for AI-DAN agents."""

from app.skills.competitor_analysis import CompetitorAnalysis, analyze_competitors
from app.skills.market_research import MarketResearchReport, research_market
from app.skills.trend_detection import TrendReport, detect_trends

__all__ = [
    "analyze_competitors",
    "CompetitorAnalysis",
    "detect_trends",
    "MarketResearchReport",
    "research_market",
    "TrendReport",
]

