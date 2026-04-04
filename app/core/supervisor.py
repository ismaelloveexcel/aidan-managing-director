"""
Supervisor layer with deterministic AI checks and hard validation gate.
"""

from __future__ import annotations

from typing import Any

from app.core.validator import validate_market_truth as _validate_market_truth


def validate_market_truth(build_brief: dict[str, Any]) -> dict[str, Any]:
    """Run Validation Gate 0 and return a strict PASS/FAIL payload."""
    return _validate_market_truth(build_brief).model_dump()


def run_ai_reasoning_hooks(idea_input: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic planning hooks used by the pipeline."""
    pricing_hint = str(idea_input.get("pricing_hint", "")).lower()
    if "subscription" in pricing_hint or "/month" in pricing_hint or "monthly" in pricing_hint:
        monetization_model = "subscription"
    elif "preorder" in pricing_hint or "one-time" in pricing_hint:
        monetization_model = "one_time"
    elif "free" in pricing_hint:
        monetization_model = "waitlist"
    else:
        monetization_model = "unspecified"

    return {
        "monetization_model": monetization_model,
        "deployment_plan": {
            "target": "vercel",
            "strategy": "single_region_global_edge",
            "healthcheck_path": "/api/health",
        },
        "launch_gate": {
            "requires_landing_page": True,
            "requires_cta": True,
            "requires_deploy_url": True,
        },
    }
