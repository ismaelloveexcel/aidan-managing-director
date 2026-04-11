"""
factory.py - Routes for BuildBrief validation and factory orchestration.
"""

from __future__ import annotations

import hmac
import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import get_settings
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
    correlation_id: str | None = None
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


@router.get("/runs", response_model=list[FactoryRunResult])
async def list_factory_runs() -> list[FactoryRunResult]:
    """Return all factory runs in the in-memory run store."""
    return _run_store.list_runs()


@router.get("/runs/{run_id}/tracking", response_model=FactoryTrackingResult)
async def get_factory_run_tracking(run_id: str) -> FactoryTrackingResult:
    """Return parsed workflow/build tracking payload for a run."""
    tracking = _factory_client.get_tracking(run_id)
    if tracking is None:
        raise HTTPException(status_code=404, detail="Factory run not found")
    return tracking


class VerifyDeploymentRequest(BaseModel):
    """Request payload for verifying a deployment URL."""

    project_id: str
    deploy_url: str = ""
    repo_url: str = ""


@router.post("/verify-deployment", response_model=DeploymentVerification)
async def verify_deployment_endpoint(request: VerifyDeploymentRequest) -> DeploymentVerification:
    """Run metadata-level deployment checks (URL format, presence).

    This does **not** probe the URL over HTTP; it validates that the
    deployment metadata (URL format, repo URL, etc.) is well-formed.
    For live HTTP probes, use the async verifier at the integration layer.
    """
    return verify_deployment(
        project_id=request.project_id,
        deploy_url=request.deploy_url,
        repo_url=request.repo_url,
    )


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
        correlation_id=run.correlation_id,
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
# Factory Callback – receives build completion callbacks from ai-dan-factory
# ---------------------------------------------------------------------------


def _verify_callback_secret(request: Request) -> None:
    """Verify the factory callback secret from the request header.

    Raises:
        HTTPException: With status code 500 if the system is running in
            production (``app_env == 'production'`` or
            ``strict_prod == True``) and **no** secret is configured at all.
        HTTPException: With status code 401 if a secret is configured and
            the ``X-Factory-Secret`` request header is missing or does not
            match.

    When no secret is configured **and** the system is in development
    mode, all requests are accepted (backward-compatible dev behavior).
    """
    settings = get_settings()
    expected = settings.factory_callback_secret
    is_production = settings.is_production_mode()

    if not expected:
        if is_production:
            raise HTTPException(
                status_code=500,
                detail="FACTORY_CALLBACK_SECRET is not configured. Cannot accept callbacks in production.",
            )
        return  # No secret configured → allow (dev mode).

    provided = request.headers.get("X-Factory-Secret", "")
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing factory callback secret.")


class FactoryCallbackPayload(BaseModel):
    """Payload sent by the ai-dan-factory repo on build completion or failure."""

    project_id: str
    correlation_id: str
    run_id: str = ""
    status: Literal["succeeded", "failed", "deployed", "building"]
    deploy_url: str = ""
    repo_url: str = ""
    error: str | None = None


class FactoryCallbackAck(BaseModel):
    """Acknowledgment returned after processing a factory callback."""

    received: bool = True
    project_id: str
    correlation_id: str
    status: str


@router.post("/callback", response_model=FactoryCallbackAck, status_code=200)
async def factory_callback(payload: FactoryCallbackPayload, request: Request) -> FactoryCallbackAck:
    """Receive build completion/failure callbacks from the ai-dan-factory.

    This endpoint is idempotent and authenticated via the
    ``X-Factory-Secret`` header.  It is the **primary** mechanism for the
    factory to report results back to the MD.  The correlation_id is used
    as the join key to locate the corresponding factory run.

    Args:
        payload: Build completion payload from the factory.
        request: The incoming HTTP request (for header extraction).

    Returns:
        Acknowledgment with the recorded status.
    """
    _verify_callback_secret(request)

    logger.info(
        "Factory callback received: project=%s correlation_id=%s status=%s",
        payload.project_id,
        payload.correlation_id,
        payload.status,
    )

    status_map = {
        "succeeded": FactoryRunStatus.SUCCEEDED,
        "failed": FactoryRunStatus.FAILED,
        "deployed": FactoryRunStatus.DEPLOYED,
        "building": FactoryRunStatus.BUILDING,
    }
    new_status = status_map.get(payload.status, FactoryRunStatus.FAILED)

    # 1. Update the in-memory factory run store (lookup by correlation_id).
    existing_run = _run_store.get_by_correlation_id(payload.correlation_id)
    if existing_run is None and payload.run_id:
        existing_run = _run_store.get_by_run_id(payload.run_id)

    # Cold-start fallback: rehydrate from portfolio DB if in-memory store is empty.
    persisted_record = None
    if existing_run is None:
        persisted_record = _portfolio.get_factory_run_by_correlation_id(payload.correlation_id)
        if persisted_record is None and payload.run_id:
            persisted_record = _portfolio.get_factory_run(payload.run_id)
        if persisted_record is not None:
            logger.info(
                "Factory callback: rehydrating run from portfolio DB for correlation_id=%s",
                payload.correlation_id,
            )
            existing_run = FactoryRunResult(
                run_id=persisted_record.run_id,
                project_id=persisted_record.project_id,
                idea_id=persisted_record.idea_id,
                status=FactoryRunStatus(persisted_record.status),
                idempotency_key=persisted_record.idempotency_key,
                dry_run=persisted_record.dry_run,
                correlation_id=persisted_record.correlation_id,
                repo_url=persisted_record.repo_url,
                deploy_url=persisted_record.deploy_url,
                error=persisted_record.error,
                events=persisted_record.events,
                created_at=persisted_record.created_at,
                updated_at=persisted_record.updated_at,
            )

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
        logger.warning(
            "Factory callback: correlation_id %s not found in store or portfolio DB.",
            payload.correlation_id,
        )

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
            event_type="factory_callback",
            payload={
                "correlation_id": payload.correlation_id,
                "run_id": payload.run_id or existing_run.run_id,
                "status": payload.status,
                "deploy_url": payload.deploy_url,
                "repo_url": payload.repo_url,
                "error": payload.error,
            },
        )

    # 3. Record outcome in the auto-learner for revenue intelligence.
    outcome_label = "build_success" if payload.status in ("succeeded", "deployed") else "build_failure"
    try:
        _auto_learner.record_outcome(
            project_id=payload.project_id,
            outcome_type=outcome_label,
            score=1.0 if payload.status in ("succeeded", "deployed") else 0.0,
            metadata={
                "correlation_id": payload.correlation_id,
                "run_id": payload.run_id,
                "deploy_url": payload.deploy_url,
                "error": payload.error or "",
            },
        )
    except Exception:
        logger.exception(
            "Failed to record outcome in auto-learner for correlation_id %s.",
            payload.correlation_id,
        )

    return FactoryCallbackAck(
        received=True,
        project_id=payload.project_id,
        correlation_id=payload.correlation_id,
        status=payload.status,
    )


# ---------------------------------------------------------------------------
# Legacy webhook endpoint – REMOVED (production hardening)
#
# The unauthenticated /webhook endpoint has been replaced by the
# authenticated /callback endpoint which uses X-Factory-Secret header
# and correlation_id for end-to-end tracing.  A tombstone route returns
# 410 Gone so that any leftover callers get a clear signal.
# ---------------------------------------------------------------------------


@router.post("/webhook", status_code=410)
async def factory_webhook_removed() -> dict[str, str]:
    """Legacy webhook endpoint – permanently removed.

    Use ``POST /factory/callback`` with the ``X-Factory-Secret`` header
    and ``correlation_id`` field instead.
    """
    return {
        "error": "gone",
        "detail": (
            "The /factory/webhook endpoint has been removed. "
            "Use POST /factory/callback with X-Factory-Secret header."
        ),
    }


# ---------------------------------------------------------------------------
# Polling fallback – GET /factory/runs/{correlation_id}/result
# ---------------------------------------------------------------------------


class CorrelationResultResponse(BaseModel):
    """Response payload for polling a factory run by correlation_id."""

    correlation_id: str
    run_id: str | None = None
    project_id: str | None = None
    status: str | None = None
    repo_url: str | None = None
    deploy_url: str | None = None
    error: str | None = None
    found: bool = True


@router.get(
    "/runs/{correlation_id}/result",
    response_model=CorrelationResultResponse,
)
async def get_factory_run_by_correlation(correlation_id: str) -> CorrelationResultResponse:
    """Poll for a factory run result by correlation_id (fallback only).

    The primary result delivery mechanism is the ``/factory/callback``
    endpoint.  This polling endpoint exists only as a fallback when
    callbacks are not available or as a debugging aid.

    Checks the in-memory store first, then falls back to the portfolio
    DB (including Turso) so results survive cold restarts.
    """

    def _to_response(source: object) -> CorrelationResultResponse:
        """Build response from either a FactoryRunResult or FactoryRunRecord."""
        status = getattr(source, "status", None)
        return CorrelationResultResponse(
            correlation_id=correlation_id,
            run_id=getattr(source, "run_id", None),
            project_id=getattr(source, "project_id", None),
            status=status.value if hasattr(status, "value") else (str(status) if status is not None else None),
            repo_url=getattr(source, "repo_url", None),
            deploy_url=getattr(source, "deploy_url", None),
            error=getattr(source, "error", None),
            found=True,
        )

    # 1. Check in-memory store first.
    run = _run_store.get_by_correlation_id(correlation_id)
    if run is not None:
        return _to_response(run)

    # 2. Cold-start fallback: check portfolio DB (including Turso).
    persisted_run = _portfolio.get_factory_run_by_correlation_id(correlation_id)
    if persisted_run is None:
        return CorrelationResultResponse(
            correlation_id=correlation_id,
            found=False,
        )

    # Rehydrate in-memory store for subsequent polling/tracking calls.
    try:
        rehydrated = FactoryRunResult(
            run_id=persisted_run.run_id,
            project_id=persisted_run.project_id,
            idea_id=persisted_run.idea_id,
            status=FactoryRunStatus(persisted_run.status),
            idempotency_key=persisted_run.idempotency_key,
            dry_run=persisted_run.dry_run,
            correlation_id=persisted_run.correlation_id,
            repo_url=persisted_run.repo_url,
            deploy_url=persisted_run.deploy_url,
            error=persisted_run.error,
            events=persisted_run.events,
            created_at=persisted_run.created_at,
            updated_at=persisted_run.updated_at,
        )
        _run_store.upsert(rehydrated)
    except Exception:
        logger.warning(
            "Failed to rehydrate factory run store from portfolio for correlation_id=%s",
            correlation_id,
            exc_info=True,
        )

    return _to_response(persisted_run)
