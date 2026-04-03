"""
factory.py - Routes for BuildBrief validation and factory orchestration.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.dependencies import get_factory_orchestrator, get_portfolio_repository
from app.factory.build_brief_validator import validate_build_brief
from app.factory.models import (
    BuildBrief,
    BuildBriefValidationResult,
    FactoryBuildRequest,
    FactoryRunResult,
)

router = APIRouter()

_orchestrator = get_factory_orchestrator()
_portfolio = get_portfolio_repository()


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
    run = _orchestrator.run_factory_build(request.build_brief, dry_run=dry_run)
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
