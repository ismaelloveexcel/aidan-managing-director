"""
CLI entrypoint for triggering a factory build via local FastAPI service.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import httpx


def _default_build_brief(project_id: str) -> dict[str, Any]:
    """Create a minimal valid BuildBrief payload for manual runs."""
    return {
        "schema_version": "1.0.0",
        "project_id": project_id,
        "idea_id": f"idea-{project_id.lower()}",
        "hypothesis": "A narrow MVP landing page will validate demand quickly.",
        "target_user": "solo founders",
        "problem": "Founders need faster idea-to-launch loops.",
        "solution": "Generate and deploy a single-purpose landing MVP automatically.",
        "mvp_scope": ["Single-page landing", "CTA capture endpoint"],
        "acceptance_criteria": [
            "Landing page is deployed",
            "CTA submit endpoint returns success",
        ],
        "landing_page_requirements": [
            "Primary CTA: Get early access",
            "Hero headline states user outcome clearly",
        ],
        "cta": "Get early access",
        "pricing_hint": "Free waitlist",
        "deployment_target": "vercel",
        "command_bundle": {"entrypoint": "factory.run"},
        "feature_flags": {"dry_run": True, "live_factory": False},
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Trigger a factory build run.")
    parser.add_argument("--project-id", required=True, help="Project ID to build.")
    parser.add_argument(
        "--correlation-id",
        default="",
        help="End-to-end correlation ID from MD dispatch.",
    )
    parser.add_argument(
        "--callback-url",
        default="",
        help="URL for factory to POST results back to MD.",
    )
    parser.add_argument(
        "--dry-run",
        required=True,
        help="Set to true or false.",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("FACTORY_BASE_URL", "http://127.0.0.1:8000"),
        help="Base URL for the AI-DAN API service.",
    )
    return parser.parse_args()


def _parse_bool(raw: str) -> bool:
    """Parse common string booleans."""
    lowered = raw.strip().lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw!r}")


def main() -> int:
    """Execute script."""
    args = parse_args()
    dry_run = _parse_bool(args.dry_run)
    build_brief = _default_build_brief(args.project_id)
    build_brief["feature_flags"]["dry_run"] = dry_run

    payload = {"build_brief": build_brief, "dry_run": dry_run}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{args.api_base_url}/factory/runs", json=payload)
        response.raise_for_status()
        result = response.json()

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
