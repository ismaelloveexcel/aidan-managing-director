"""
Multi-layer pipeline that transforms idea input into a BuildBrief contract.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.agents.guardian import GuardianAgent
from app.core.supervisor import run_ai_reasoning_hooks, validate_market_truth
from app.core.validator import validate_idea_input
from app.factory.models import BuildBrief
from app.portfolio.repository import PortfolioRepository


class PipelineBlockedError(RuntimeError):
    """Raised when pipeline guardrails block BuildBrief generation."""


def _clean_list(value: Any, fallback: list[str]) -> list[str]:
    """Normalize list-like values to non-empty string lists."""
    if not isinstance(value, list):
        return fallback
    items = [str(item).strip() for item in value if str(item).strip()]
    return items or fallback


def run_pipeline(
    idea_input: dict[str, Any],
    *,
    repository: PortfolioRepository | None = None,
) -> BuildBrief:
    """Run deterministic validation -> market truth -> guardian -> BuildBrief generation."""
    deterministic = validate_idea_input(idea_input)
    ai_hooks = run_ai_reasoning_hooks(idea_input)
    market_truth = validate_market_truth(idea_input)

    project_id = str(idea_input.get("project_id") or f"prj-{uuid.uuid4().hex[:8]}")
    idea_id = str(idea_input.get("idea_id") or f"idea-{uuid.uuid4().hex[:8]}")
    hypothesis = str(idea_input.get("hypothesis", "")).strip()
    target_user = str(idea_input.get("target_user", "")).strip()
    problem = str(idea_input.get("problem", "")).strip()
    solution = str(idea_input.get("solution", "")).strip()
    cta = str(idea_input.get("cta", "")).strip()
    pricing_hint = str(idea_input.get("pricing_hint", "")).strip()

    if repository is not None:
        if repository.get_project(project_id) is None:
            repository.create_project(
                project_id=project_id,
                name=str(idea_input.get("name", project_id)),
                description=str(idea_input.get("problem", "Pipeline-initiated project")),
            )
        repository.log_event(
            project_id=project_id,
            event_type="idea_scored",
            payload={"validation_score": deterministic.score, "issues": deterministic.issues},
        )

    if not deterministic.valid:
        raise PipelineBlockedError(
            "Deterministic validation failed: " + ", ".join(deterministic.issues),
        )
    if market_truth["decision"] != "PASS":
        raise PipelineBlockedError(f"Validation Gate 0 failed: {market_truth['reason']}")

    guardian = GuardianAgent().review(
        idea_input=idea_input,
        validation_score=deterministic.score,
        monetization_model=ai_hooks["monetization_model"],
        market_truth=market_truth,
    )

    if guardian.decision == "BLOCK":
        raise PipelineBlockedError(f"Guardian blocked pipeline: {guardian.reason}")

    mvp_scope = _clean_list(idea_input.get("mvp_scope"), fallback=[])
    acceptance_criteria = _clean_list(idea_input.get("acceptance_criteria"), fallback=[])
    landing_page_requirements = _clean_list(idea_input.get("landing_page_requirements"), fallback=[])
    cta_value = cta
    if not hypothesis or not target_user or not problem or not solution or not cta_value:
        raise PipelineBlockedError(
            "Missing required BuildBrief fields (hypothesis/target_user/problem/solution/cta).",
        )
    if not mvp_scope or not acceptance_criteria or not landing_page_requirements:
        raise PipelineBlockedError(
            "Missing required list fields (mvp_scope/acceptance_criteria/landing_page_requirements).",
        )
    if not any(cta_value.lower() in requirement.lower() for requirement in landing_page_requirements):
        landing_page_requirements.append(f"Primary CTA: {cta_value}")

    incoming_command_bundle = idea_input.get("command_bundle")
    if not isinstance(incoming_command_bundle, dict):
        incoming_command_bundle = {}

    brief = BuildBrief(
        project_id=project_id,
        idea_id=idea_id,
        hypothesis=hypothesis,
        target_user=target_user,
        problem=problem,
        solution=solution,
        mvp_scope=mvp_scope,
        acceptance_criteria=acceptance_criteria,
        landing_page_requirements=landing_page_requirements,
        cta=cta_value,
        pricing_hint=pricing_hint,
        deployment_target="vercel",
        command_bundle={
            **incoming_command_bundle,
            "pipeline": "v2",
            "market_truth": market_truth,
            "guardian_decision": guardian.decision,
        },
        feature_flags=idea_input.get("feature_flags", {"dry_run": True, "live_factory": False}),
        validation_score=deterministic.score,
        risk_flags=guardian.risk_flags,
        monetization_model=ai_hooks["monetization_model"],
        deployment_plan=ai_hooks["deployment_plan"],
        launch_gate=ai_hooks["launch_gate"],
    )

    if repository is not None:
        repository.save_build_brief(project_id=project_id, brief=brief)

    return brief
