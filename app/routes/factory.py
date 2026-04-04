"""
factory.py - Routes for BuildBrief validation and factory orchestration.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.dependencies import get_factory_client, get_factory_orchestrator, get_portfolio_repository
from app.core.pipeline import run_pipeline
from app.factory.build_brief_validator import validate_build_brief
from app.factory.factory_client import FactoryTrackingResult
from app.factory.models import (
    BuildBrief,
    BuildBriefValidationResult,
    FactoryBuildRequest,
    FactoryRunResult,
)
from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import DecisionAction
from app.reasoning.strategist import Strategist

router = APIRouter()

_orchestrator = get_factory_orchestrator()
_factory_client = get_factory_client()
_portfolio = get_portfolio_repository()
_strategist = Strategist()
_idea_engine = IdeaEngine()


class IdeaExecutionRequest(BaseModel):
    """Input payload for decision-gated factory execution from raw idea text."""

    message: str
    context: dict[str, Any] | None = None
    project_id: str | None = None
    dry_run: bool = True


class IdeaExecutionResult(BaseModel):
    """Output payload for idea->decision->build execution."""

    project_id: str
    idea_id: str
    approved_for_build: bool
    decision: str
    run_id: str | None = None
    status: str | None = None
    repo_url: str | None = None
    deployment_url: str | None = None
    workflow_dispatched: bool = False
    workflow_run_id: str | None = None
    brief_hash: str | None = None
    brief_payload: dict[str, Any] | None = None


@router.post("/briefs/validate", response_model=BuildBriefValidationResult)
async def validate_brief(brief: BuildBrief) -> BuildBriefValidationResult:
    """Validate BuildBrief payloads before queueing a factory run."""
    return validate_build_brief(brief)


@router.post("/runs", response_model=FactoryRunResult)
async def create_factory_run(request: FactoryBuildRequest) -> FactoryRunResult:
    """Create a factory run from a validated BuildBrief."""
    dry_run = request.dry_run
    if dry_run is None:
        dry_run = request.build_brief.feature_flags.get("dry_run", True)
    run, _ = _factory_client.trigger_build(build_brief=request.build_brief, dry_run=dry_run)
    if _portfolio.get_project(run.project_id) is not None:
        _portfolio.save_factory_run(run)
    return run


@router.get("/runs/{run_id}", response_model=FactoryRunResult)
async def get_factory_run(run_id: str) -> FactoryRunResult:
    """Return status and outputs of a factory run."""
    run = _orchestrator.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Factory run not found")
    return run


@router.get("/runs/{run_id}/tracking", response_model=FactoryTrackingResult)
async def get_factory_run_tracking(run_id: str) -> FactoryTrackingResult:
    """Return parsed workflow/build tracking payload for a run."""
    tracking = _factory_client.get_tracking(run_id)
    if tracking is None:
        raise HTTPException(status_code=404, detail="Factory run not found")
    return tracking


@router.post("/ideas/execute", response_model=IdeaExecutionResult)
async def execute_idea_build(request: IdeaExecutionRequest) -> IdeaExecutionResult:
    """Execute the full flow: idea -> decision -> BuildBrief -> factory trigger."""
    context = dict(request.context or {})
    founder_response = _strategist.process_founder_input(request.message, context=context)
    decision_action = founder_response.decision_output.decision if founder_response.decision_output else None
    aggregate = founder_response.score.aggregate if founder_response.score is not None else 0.0
    approved_for_build = decision_action == DecisionAction.APPROVE or (
        decision_action == DecisionAction.PARK and aggregate >= 0.70
    )
    if not approved_for_build:
        return IdeaExecutionResult(
            project_id=request.project_id or "not-approved",
            idea_id="not-approved",
            approved_for_build=False,
            decision=(decision_action.value if decision_action is not None else "unknown"),
            status="skipped",
        )

    project_id = request.project_id or f"prj-{uuid.uuid4().hex[:8]}"
    idea = _idea_engine.generate(request.message, context=context)
    brief = run_pipeline(
        {
            "project_id": project_id,
            "idea_id": idea.idea_id,
            "name": idea.title,
            "title": idea.title,
            "hypothesis": founder_response.decision_output.why_now,
            "target_user": idea.target_user,
            "problem": idea.problem,
            "solution": idea.summary,
            "cta": "Get early access",
            "pricing_hint": idea.monetization_path,
            "mvp_scope": ["Landing page", "CV scoring API"],
            "acceptance_criteria": ["Landing page loads", "Scoring API returns deterministic output"],
            "landing_page_requirements": ["Primary CTA: Get early access"],
            "feature_flags": {"dry_run": request.dry_run, "live_factory": not request.dry_run},
        },
        repository=_portfolio,
    )
    run, tracking = _factory_client.trigger_build(build_brief=brief, dry_run=request.dry_run)
    _portfolio.save_factory_run(run)
    return IdeaExecutionResult(
        project_id=run.project_id,
        idea_id=run.idea_id,
        approved_for_build=True,
        decision="APPROVE_BUILD",
        run_id=run.run_id,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        repo_url=run.repo_url,
        deployment_url=run.deploy_url,
        workflow_dispatched=tracking.workflow_dispatched,
        workflow_run_id=tracking.workflow_run_id,
        brief_hash=brief.brief_hash(),
        brief_payload=brief.model_dump(mode="json", by_alias=True),
    )
