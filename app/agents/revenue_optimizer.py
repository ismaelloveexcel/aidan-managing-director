"""
Revenue optimizer agent – deterministic pricing and funnel optimization.

Uses rules-based analysis of analytics data to recommend pricing adjustments,
A/B tests, and funnel improvements. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RevenueOptimizationResult(BaseModel):
    """Structured output from revenue optimization analysis."""

    pricing_recommendation: str
    suggested_tests: list[str] = Field(default_factory=list)
    funnel_analysis: dict[str, float] = Field(default_factory=dict)
    priority_action: str
    estimated_revenue_uplift_pct: float = Field(ge=0.0)


def _safe_rate(numerator: float, denominator: float) -> float:
    """Compute a conversion rate safely, returning 0.0 if denominator is zero."""
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


class RevenueOptimizerAgent:
    """Rules-based agent for pricing adjustments and funnel optimization.

    Decision logic:
    - Visitor → signup conversion < 1%  → prioritise CTA optimisation
    - Visitor → signup conversion 1–3%  → prioritise pricing testing
    - Visitor → signup conversion > 3%  → prioritise distribution scaling
    """

    def _build_funnel_analysis(
        self,
        visits: float,
        clicks: float,
        conversions: float,
        revenue: float,
    ) -> dict[str, float]:
        """Compute conversion rates for each funnel stage."""
        return {
            "visit_to_click_pct": _safe_rate(clicks, visits),
            "click_to_conversion_pct": _safe_rate(conversions, clicks),
            "visit_to_conversion_pct": _safe_rate(conversions, visits),
            "revenue_per_conversion": round(revenue / conversions, 2) if conversions > 0 else 0.0,
            "revenue_per_visit": round(revenue / visits, 4) if visits > 0 else 0.0,
        }

    def _recommend_pricing(
        self,
        conversion_rate: float,
        current_pricing: dict[str, Any],
    ) -> tuple[str, float]:
        """Return (pricing_recommendation, estimated_uplift_pct).

        Args:
            conversion_rate: Visitor-to-conversion percentage (0–100).
            current_pricing: Dict with optional keys ``model``, ``price``,
                ``currency``.

        Returns:
            Tuple of recommendation string and estimated revenue uplift %.
        """
        model = str(current_pricing.get("model", "subscription")).lower()
        price_val = float(current_pricing.get("price", 0) or 0)

        if conversion_rate < 1.0:
            return (
                "Pricing is not the primary blocker. Focus on CTA and value "
                "proposition first. Consider adding a free trial or freemium "
                "tier to reduce friction.",
                15.0,
            )
        if conversion_rate < 3.0:
            if model in ("subscription", "saas") and price_val > 99:
                return (
                    f"Current price of ${price_val:.0f} may be too high for early traction. "
                    "Test a lower entry tier (e.g. $29–$49/month) with upsell path.",
                    25.0,
                )
            if model in ("subscription", "saas") and price_val < 20:
                return (
                    f"Current price of ${price_val:.0f} may be undervaluing the product. "
                    "Test increasing to $29–$49/month — higher price signals quality.",
                    20.0,
                )
            return (
                "Conversion rate is in target range for pricing experimentation. "
                "Test annual billing discount (2 months free) to improve LTV.",
                20.0,
            )

        # conversion_rate >= 3%
        return (
            "Strong conversion rate. Focus on scaling distribution rather than "
            "changing pricing. Consider introducing premium/enterprise tier to "
            "capture higher-value customers.",
            35.0,
        )

    def _suggest_tests(
        self,
        conversion_rate: float,
        visit_to_click: float,
    ) -> list[str]:
        """Generate A/B test priorities based on funnel analysis."""
        tests: list[str] = []

        if conversion_rate < 1.0:
            tests.extend(
                [
                    "A/B test hero headline — value proposition clarity",
                    "A/B test primary CTA button copy and colour",
                    "A/B test social proof placement (above vs below the fold)",
                    "Test free trial vs money-back guarantee offer",
                ]
            )
        elif conversion_rate < 3.0:
            tests.extend(
                [
                    "A/B test pricing page layout — feature table vs card design",
                    "Test annual billing discount prominence",
                    "A/B test pricing tier naming (Starter/Pro/Scale vs Basic/Growth/Enterprise)",
                    "Test checkout flow — single page vs multi-step",
                ]
            )
        else:
            tests.extend(
                [
                    "Test enterprise/team pricing tier",
                    "A/B test referral programme CTA post-signup",
                    "Test expansion revenue trigger — in-app upsell timing",
                    "Test channel-specific landing pages for top acquisition channels",
                ]
            )

        if visit_to_click < 10.0:
            tests.insert(0, "A/B test landing page above-the-fold layout")

        return tests

    def optimize(
        self,
        *,
        analytics: dict[str, Any],
        current_pricing: dict[str, Any] | None = None,
    ) -> RevenueOptimizationResult:
        """Run revenue optimization analysis.

        Args:
            analytics: Dict with keys ``visits``, ``clicks``, ``conversions``,
                ``revenue``.
            current_pricing: Optional dict with keys ``model``, ``price``,
                ``currency``.

        Returns:
            RevenueOptimizationResult with pricing recommendation, suggested
            tests, funnel analysis, priority action, and uplift estimate.
        """
        if current_pricing is None:
            current_pricing = {}

        visits = float(analytics.get("visits", 0) or 0)
        clicks = float(analytics.get("clicks", 0) or 0)
        conversions = float(analytics.get("conversions", 0) or 0)
        revenue = float(analytics.get("revenue", 0) or 0)

        funnel = self._build_funnel_analysis(visits, clicks, conversions, revenue)
        conversion_rate = funnel["visit_to_conversion_pct"]
        visit_to_click = funnel["visit_to_click_pct"]

        pricing_recommendation, uplift = self._recommend_pricing(
            conversion_rate, current_pricing
        )
        suggested_tests = self._suggest_tests(conversion_rate, visit_to_click)

        # Priority action mirrors the conversion-rate decision rules
        if conversion_rate < 1.0:
            priority_action = (
                "Optimise CTA and value proposition — conversion rate is critically low. "
                "Run headline and CTA A/B tests before touching pricing."
            )
        elif conversion_rate < 3.0:
            priority_action = (
                "Test pricing structure — conversion rate is in the experimentation zone. "
                "Run pricing page A/B tests to find optimal price point."
            )
        else:
            priority_action = (
                "Scale distribution — strong conversion rate. "
                "Increase top-of-funnel traffic to grow revenue."
            )

        return RevenueOptimizationResult(
            pricing_recommendation=pricing_recommendation,
            suggested_tests=suggested_tests,
            funnel_analysis=funnel,
            priority_action=priority_action,
            estimated_revenue_uplift_pct=uplift,
        )
