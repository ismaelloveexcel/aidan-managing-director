"""
Supervisor layer with deterministic stubs for external and AI checks.
"""

from __future__ import annotations

from typing import Any


def run_external_validation_stub(idea_input: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic placeholder external validation response."""
    title = str(idea_input.get("title", "")).strip()
    status = "pass" if title else "warn"
    findings = [] if title else ["missing_title_for_external_signal"]
    return {
        "status": status,
        "findings": findings,
        "source": "external_validation_stub",
    }


def run_ai_reasoning_hooks(idea_input: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic AI-hook placeholders used by the pipeline."""
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
