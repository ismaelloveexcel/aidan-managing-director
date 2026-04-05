"""
factory.py - Routes for BuildBrief validation and factory orchestration.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.dependencies import (
    get_auto_learner,
    get_factory_client,
    get_factory_orchestrator,
    get_factory_run_store,
    get_governance_service,
    get_portfolio_intelligence_service,
    get_portfolio_repository,
)
from app.core.pipeline import run_pipeline
from app.core.supervisor import validate_market_truth
from app.factory.build_brief_validator import validate_build_brief
from app.factory.deployment_verifier import DeploymentVerification, verify_deployment
from app.factory.factory_client import FactoryTrackingResult
from app.factory.models import (
    BuildBrief,
    BuildBriefValidationResult,
    FactoryBuildRequest,
    FactoryRunResult,
    FactoryRunStatus,
)
from app.governance.models import GovernanceReviewRequest
from app.planning.planner import generate_business_package
from app.reasoning.evaluator import Evaluator
from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import DecisionAction

logger = logging.getLogger(__name__)

router = APIRouter()

_orchestrator = get_factory_orchestrator()
_factory_client = get_factory_client()
_portfolio = get_portfolio_repository()
_run_store = get_factory_run_store()
_idea_engine = IdeaEngine()
_evaluator = Evaluator()
_intelligence = get_portfolio_intelligence_service()
_governance = get_governance_service()
_auto_learner = get_auto_learner()


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
    market_truth: dict[str, Any] | None = None
    total_score: float | None = None
    score_breakdown: dict[str, float] | None = None
    business_package: dict[str, Any] | None = None
    reason: str | None = None


@router.post("/briefs/validate", response_model=BuildBriefValidationResult)
async def validate_brief(brief: BuildBrief) -> BuildBriefValidationResult:
    """Validate BuildBrief payloads before queueing a factory run."""
    return validate_build_brief(brief)


@router.get("/runs", response_model=list[FactoryRunResult])
async def list_factory_runs() -> list[FactoryRunResult]:
    """Return all factory runs from the run store."""
    return _run_store.list_runs()


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
    """Execute strict flow: validation -> scoring -> business package -> build."""
    context = dict(request.context or {})
    idea = _idea_engine.generate(request.message, context=context)
    project_id = request.project_id or f"prj-{uuid.uuid4().hex[:8]}"

    # 1) Validation Gate 0: must pass before scoring.
    market_truth_payload = {
        "title": idea.title,
        "hypothesis": f"{idea.summary} {request.message}",
        "target_user": idea.target_user,
        "problem": f"{idea.problem} {request.message}",
        "solution": f"{idea.summary} {request.message}",
        "pricing_hint": f"{idea.monetization_path} {request.message}",
        "monetization_path": idea.monetization_path,
    }
    market_truth = validate_market_truth(market_truth_payload)
    if market_truth["decision"] != "PASS":
        return IdeaExecutionResult(
            project_id=project_id,
            idea_id=idea.idea_id,
            approved_for_build=False,
            decision=DecisionAction.REJECT.value,
            status="skipped",
            market_truth=market_truth,
            total_score=0.0,
            score_breakdown={
                "market_demand": 0.0,
                "competition_saturation": 0.0,
                "monetization_potential": 0.0,
                "build_complexity": 0.0,
                "speed_to_revenue": 0.0,
            },
            reason=f"Validation Gate 0 failed: {market_truth['reason']}",
        )

    # 2) Mandatory scoring gate.
    evaluation = _evaluator.score(idea, market_truth=market_truth)
    if evaluation.decision == DecisionAction.REJECT:
        return IdeaExecutionResult(
            project_id=project_id,
            idea_id=idea.idea_id,
            approved_for_build=False,
            decision=DecisionAction.REJECT.value,
            status="skipped",
            market_truth=market_truth,
            total_score=evaluation.total_score,
            score_breakdown=evaluation.breakdown.model_dump(),
            reason=evaluation.reason,
        )
    if evaluation.decision == DecisionAction.HOLD:
        return IdeaExecutionResult(
            project_id=project_id,
            idea_id=idea.idea_id,
            approved_for_build=False,
            decision=DecisionAction.HOLD.value,
            status="queued",
            market_truth=market_truth,
            total_score=evaluation.total_score,
            score_breakdown=evaluation.breakdown.model_dump(),
            reason=evaluation.reason,
        )

    # 3) One-click business package generation (required for APPROVE path).
    business_package = generate_business_package(
        {
            "title": idea.title,
            "target_user": idea.target_user,
            "problem": idea.problem,
            "solution": idea.summary,
            "pricing_hint": idea.monetization_path,
        },
    )
    required_business_fields = ("offer", "pricing_model", "price_range", "landing_page", "gtm_strategy")
    if any(field not in business_package for field in required_business_fields):
        raise HTTPException(status_code=422, detail="Business package is incomplete; build is blocked.")

    # 4) One-operator limits: auto HOLD when overloaded.
    should_hold, hold_reason = _intelligence.should_hold_new_project()
    if should_hold:
        return IdeaExecutionResult(
            project_id=project_id,
            idea_id=idea.idea_id,
            approved_for_build=False,
            decision=DecisionAction.HOLD.value,
            status="queued",
            market_truth=market_truth,
            total_score=evaluation.total_score,
            score_breakdown=evaluation.breakdown.model_dump(),
            business_package=business_package,
            reason=f"Auto-HOLD by operator limits: {hold_reason}",
        )

    # 5) Strict pipeline continues only on APPROVE + package + capacity.
    brief = run_pipeline(
        {
            "project_id": project_id,
            "idea_id": idea.idea_id,
            "name": idea.title,
            "title": idea.title,
            "hypothesis": market_truth_payload["hypothesis"],
            "target_user": idea.target_user,
            "problem": market_truth_payload["problem"],
            "solution": market_truth_payload["solution"],
            "cta": business_package["landing_page"]["cta"],
            "pricing_hint": f"{business_package['pricing_model']} - {business_package['price_range']}",
            "mvp_scope": [
                "Landing page with explicit offer and pricing",
                "Lead capture or checkout flow",
                "Core fulfillment workflow for promised outcome",
            ],
            "acceptance_criteria": [
                "Landing page communicates offer, pricing, and CTA",
                "Primary CTA is functional and conversion-ready",
                "Deployment and health check pass",
            ],
            "landing_page_requirements": [
                f"Headline: {business_package['landing_page']['headline']}",
                f"Subheadline: {business_package['landing_page']['subheadline']}",
                f"Primary CTA: {business_package['landing_page']['cta']}",
            ],
            "command_bundle": {
                "business_package": business_package,
                "score": {
                    "total_score": evaluation.total_score,
                    "breakdown": evaluation.breakdown.model_dump(),
                },
                "market_truth": market_truth,
            },
            "feature_flags": {"dry_run": request.dry_run, "live_factory": not request.dry_run},
        },
        repository=_portfolio,
    )

    if not brief.command_bundle.get("business_package"):
        raise HTTPException(status_code=422, detail="Business package missing from brief; build is blocked.")
    governance = _governance.review(
        GovernanceReviewRequest(
            action="dispatch_factory_build",
            parameters=brief.command_bundle,
        ),
    )
    if not governance.approved:
        return IdeaExecutionResult(
            project_id=project_id,
            idea_id=idea.idea_id,
            approved_for_build=False,
            decision=DecisionAction.HOLD.value,
            status="queued",
            market_truth=market_truth,
            total_score=evaluation.total_score,
            score_breakdown=evaluation.breakdown.model_dump(),
            business_package=business_package,
            reason=f"Governance blocked build trigger: {governance.reason}",
        )

    run, tracking = _factory_client.trigger_build(build_brief=brief, dry_run=request.dry_run)
    _portfolio.save_factory_run(run)
    _portfolio.update_project_metadata(
        project_id=run.project_id,
        metadata_updates={
            "business_package": business_package,
            "evaluation": {
                "total_score": evaluation.total_score,
                "decision": evaluation.decision.value,
                "reason": evaluation.reason,
                "breakdown": evaluation.breakdown.model_dump(),
            },
            "market_truth": market_truth,
        },
    )

    return IdeaExecutionResult(
        project_id=run.project_id,
        idea_id=run.idea_id,
        approved_for_build=True,
        decision=DecisionAction.APPROVE.value,
        run_id=run.run_id,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        repo_url=run.repo_url,
        deployment_url=run.deploy_url,
        workflow_dispatched=tracking.workflow_dispatched,
        workflow_run_id=tracking.workflow_run_id,
        brief_hash=brief.brief_hash(),
        brief_payload=brief.model_dump(mode="json", by_alias=True),
        market_truth=market_truth,
        total_score=evaluation.total_score,
        score_breakdown=evaluation.breakdown.model_dump(),
        business_package=business_package,
        reason=evaluation.reason,
    )


# ---------------------------------------------------------------------------
# Factory Webhook – receives build completion callbacks from ai-dan-factory
# ---------------------------------------------------------------------------


class FactoryWebhookPayload(BaseModel):
    """Payload sent by the ai-dan-factory repo on build completion or failure."""

    project_id: str
    run_id: str
    status: Literal["succeeded", "failed"]
    deploy_url: str = ""
    repo_url: str = ""
    error: str | None = None


class FactoryWebhookAck(BaseModel):
    """Acknowledgment returned after processing a factory webhook."""

    received: bool = True
    project_id: str
    run_id: str
    status: str


@router.post("/webhook", response_model=FactoryWebhookAck, status_code=200)
async def factory_webhook(payload: FactoryWebhookPayload) -> FactoryWebhookAck:
    """Receive build completion/failure callbacks from the ai-dan-factory.

    This endpoint is called by the factory GitHub Actions workflow after a
    build succeeds or fails.  It updates the portfolio and the factory run
    store, and records the outcome in the auto-learner for revenue intelligence.

    Args:
        payload: Build completion payload from the factory.

    Returns:
        Acknowledgment with the recorded status.
    """
    logger.info(
        "Factory webhook received: project=%s run=%s status=%s",
        payload.project_id,
        payload.run_id,
        payload.status,
    )

    new_status = FactoryRunStatus.SUCCEEDED if payload.status == "succeeded" else FactoryRunStatus.FAILED

    # 1. Update the in-memory factory run store.
    existing_run = _run_store.get_by_run_id(payload.run_id)
    if existing_run is not None:
        updated_run = existing_run.model_copy(
            update={
                "status": new_status,
                "deploy_url": payload.deploy_url or existing_run.deploy_url,
                "repo_url": payload.repo_url or existing_run.repo_url,
                "error": payload.error,
            },
        )
        _run_store.upsert(updated_run)
    else:
        logger.warning("Factory webhook: run_id %s not found in store.", payload.run_id)

    # 2. Persist the factory run in the portfolio if the project exists.
    project = _portfolio.get_project(payload.project_id)
    if project is not None and existing_run is not None:
        run_to_save = existing_run.model_copy(
            update={
                "status": new_status,
                "deploy_url": payload.deploy_url or existing_run.deploy_url,
                "repo_url": payload.repo_url or existing_run.repo_url,
                "error": payload.error,
            },
        )
        _portfolio.save_factory_run(run_to_save)
        _portfolio.log_event(
            project_id=payload.project_id,
            event_type="factory_webhook",
            payload={
                "run_id": payload.run_id,
                "status": payload.status,
                "deploy_url": payload.deploy_url,
                "repo_url": payload.repo_url,
                "error": payload.error,
            },
        )

    # 3. Record outcome in the auto-learner for revenue intelligence.
    outcome_label = "build_success" if payload.status == "succeeded" else "build_failure"
    try:
        _auto_learner.record_outcome(
            project_id=payload.project_id,
            outcome_type=outcome_label,
            score=1.0 if payload.status == "succeeded" else 0.0,
            metadata={
                "run_id": payload.run_id,
                "deploy_url": payload.deploy_url,
                "error": payload.error or "",
            },
        )
    except Exception:
        logger.exception("Failed to record outcome in auto-learner for run %s.", payload.run_id)

    return FactoryWebhookAck(
        received=True,
        project_id=payload.project_id,
        run_id=payload.run_id,
        status=payload.status,
    )



# ---------------------------------------------------------------------------
# Deployment Verification
# ---------------------------------------------------------------------------


class VerifyDeploymentRequest(BaseModel):
    """Request payload for verifying a deployment URL."""

    project_id: str
    deploy_url: str = ""
    repo_url: str = ""
    expected_endpoints: list[str] | None = None


@router.post("/verify-deployment", response_model=DeploymentVerification)
async def verify_deployment_endpoint(request: VerifyDeploymentRequest) -> DeploymentVerification:
    """Verify that a deployed project URL is accessible and healthy."""
    return verify_deployment(
        project_id=request.project_id,
        deploy_url=request.deploy_url,
        repo_url=request.repo_url,
        expected_endpoints=request.expected_endpoints,
    )
