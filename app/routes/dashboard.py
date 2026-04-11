"""
dashboard.py – Dashboard health and design token routes.

GET /api/dashboard/health  – Portfolio health summary (for dynamic theming).
GET /api/dashboard/tokens  – Design token JSON for visual consistency.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_factory_run_store, get_portfolio_repository
from app.portfolio.models import LifecycleState, utcnow_iso

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DashboardHealth(BaseModel):
    """Portfolio health summary returned by GET /api/dashboard/health."""

    total_projects: int
    approved_count: int
    revenue_total: float
    blocked_count: int
    health_status: Literal["GREEN", "AMBER", "RED"]
    summary: str


class DesignTokens(BaseModel):
    """Design tokens for consistent visual styling across Factory templates."""

    primary: str = Field(..., description="Primary accent colour (hex)")
    surface: str = Field(..., description="Card/surface background colour (hex)")
    text: str = Field(..., description="Body text colour (hex)")
    success: str = Field(..., description="Success/positive indicator (hex)")
    warning: str = Field(..., description="Warning/hold indicator (hex)")
    danger: str = Field(..., description="Danger/reject indicator (hex)")
    border: str = Field(..., description="Default border colour (hex)")
    radius: str = Field(..., description="Default border radius (CSS)")
    font_family: str = Field(..., description="Primary font stack (CSS)")
    font_sizes: dict[str, str] = Field(default_factory=dict, description="Named font sizes")


# ---------------------------------------------------------------------------
# Design token constants
# ---------------------------------------------------------------------------

_DESIGN_TOKENS = DesignTokens(
    primary="#5b6ef7",
    surface="#1a1a2e",
    text="#e0e0e0",
    success="#16a34a",
    warning="#d97706",
    danger="#dc2626",
    border="#333333",
    radius="8px",
    font_family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    font_sizes={
        "xs": "0.75rem",
        "sm": "0.85rem",
        "base": "1rem",
        "lg": "1.2rem",
        "xl": "1.5rem",
        "2xl": "1.8rem",
    },
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_APPROVED_STATES = {
    LifecycleState.APPROVED,
    LifecycleState.QUEUED,
    LifecycleState.BUILDING,
    LifecycleState.LAUNCHED,
    LifecycleState.MONITORING,
    LifecycleState.SCALED,
}
_BLOCKED_STATES = {LifecycleState.KILLED}

_MAX_RECENT_BUILDS = 20


def _compute_health(
    total: int,
    approved: int,
    revenue_total: float,
    blocked: int,
) -> tuple[Literal["GREEN", "AMBER", "RED"], str]:
    """Derive health status and human-readable summary.

    Rules:
    - GREEN: revenue > 0 OR approved >= 3
    - RED: blocked projects exist OR no projects at all
    - AMBER: projects exist but no revenue and not GREEN
    """
    if blocked > 0 or total == 0:
        status: Literal["GREEN", "AMBER", "RED"] = "RED"
        summary = (
            "No projects in portfolio — add your first idea to get started."
            if total == 0
            else f"{blocked} project(s) blocked. Address issues to unblock the pipeline."
        )
    elif revenue_total > 0 or approved >= 3:
        status = "GREEN"
        summary = (
            f"Portfolio healthy: {approved} approved project(s)"
            + (f", ${revenue_total:,.0f} total revenue." if revenue_total > 0 else ".")
        )
    else:
        status = "AMBER"
        summary = (
            f"{total} project(s) active but no revenue recorded yet. "
            "Push ideas through approval to build momentum."
        )
    return status, summary


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health", response_model=DashboardHealth)
def get_dashboard_health() -> DashboardHealth:
    """Return portfolio health summary for dynamic dashboard theming.

    Reads live portfolio data from the SQLite repository and returns a
    compact health object.  The root UI fetches this on page-load to
    select the header gradient colour.

    Returns:
        DashboardHealth with total_projects, approved_count, revenue_total,
        blocked_count, health_status (GREEN/AMBER/RED), and summary.
    """
    try:
        repo = get_portfolio_repository()
        projects = repo.list_projects()
    except Exception:
        logger.warning("dashboard: Failed to read portfolio; returning default RED health.", exc_info=True)
        health_status, summary = _compute_health(0, 0, 0.0, 0)
        return DashboardHealth(
            total_projects=0,
            approved_count=0,
            revenue_total=0.0,
            blocked_count=0,
            health_status=health_status,
            summary=summary,
        )

    total = len(projects)
    approved = sum(1 for p in projects if p.status in _APPROVED_STATES)
    blocked = sum(1 for p in projects if p.status in _BLOCKED_STATES)

    # Sum revenue from metadata if present (guard against non-numeric values).
    revenue_total = 0.0
    for project in projects:
        try:
            revenue_total += float(project.metadata.get("revenue", 0) or 0)
        except (TypeError, ValueError):
            logger.warning(
                "Non-numeric revenue metadata for project %s: %r",
                project.project_id,
                project.metadata.get("revenue"),
            )

    health_status, summary = _compute_health(total, approved, revenue_total, blocked)

    return DashboardHealth(
        total_projects=total,
        approved_count=approved,
        revenue_total=revenue_total,
        blocked_count=blocked,
        health_status=health_status,
        summary=summary,
    )


@router.get("/tokens", response_model=DesignTokens)
def get_design_tokens() -> DesignTokens:
    """Return the design token JSON for Factory-generated products.

    Factory templates can read these tokens to inherit the Managing
    Director's visual language automatically.

    Returns:
        DesignTokens with colours, spacing, fonts, and font sizes.
    """
    return _DESIGN_TOKENS


# ---------------------------------------------------------------------------
# Dashboard summary models
# ---------------------------------------------------------------------------


class ProjectSummary(BaseModel):
    """Compact project representation for the dashboard."""

    project_id: str
    name: str
    description: str
    status: str
    project_type: str = "venture"  # "venture" or "personal"
    created_at: str
    updated_at: str
    deploy_url: str | None = None
    repo_url: str | None = None
    revenue: float = 0.0


class DashboardIssue(BaseModel):
    """A flagged issue or warning for the dashboard."""

    severity: Literal["critical", "warning", "info"]
    title: str
    description: str
    affected_project: str | None = None
    recommended_action: str


class DashboardSummary(BaseModel):
    """Comprehensive dashboard payload for the premium UI."""

    projects: list[ProjectSummary]
    stats: dict[str, Any]
    health: DashboardHealth
    recent_builds: list[dict[str, Any]]
    issues: list[DashboardIssue]


class ProjectTypeUpdate(BaseModel):
    """Request to update a project's type."""

    project_type: str = Field(..., pattern="^(venture|personal)$")


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def _project_to_summary(project: Any) -> ProjectSummary:
    """Convert a PortfolioProjectRecord to a ProjectSummary."""
    meta = project.metadata or {}
    revenue = 0.0
    try:
        revenue = float(meta.get("revenue", 0) or 0)
    except (TypeError, ValueError):
        pass

    return ProjectSummary(
        project_id=project.project_id,
        name=project.name,
        description=project.description,
        status=project.status.value if hasattr(project.status, "value") else str(project.status),
        project_type=meta.get("project_type", "venture"),
        created_at=project.created_at,
        updated_at=project.updated_at,
        deploy_url=meta.get("deploy_url"),
        repo_url=meta.get("repo_url"),
        revenue=revenue,
    )


def _detect_issues(projects: list[Any]) -> list[DashboardIssue]:
    """Scan portfolio projects and return actionable issues."""
    issues: list[DashboardIssue] = []

    if not projects:
        issues.append(
            DashboardIssue(
                severity="info",
                title="No projects yet",
                description="Your portfolio is empty. Submit your first idea to get started.",
                recommended_action="Use the /api/ideas endpoint to submit a new idea.",
            )
        )
        return issues

    for p in projects:
        status_val = p.status.value if hasattr(p.status, "value") else str(p.status)

        if status_val == LifecycleState.KILLED.value:
            issues.append(
                DashboardIssue(
                    severity="warning",
                    title=f"Project killed: {p.name}",
                    description=f"'{p.name}' has been killed. Review whether it should be revived or archived.",
                    affected_project=p.project_id,
                    recommended_action="Review the project and decide whether to restart or permanently archive it.",
                )
            )

        if status_val in {LifecycleState.IDEA.value, LifecycleState.REVIEW.value}:
            issues.append(
                DashboardIssue(
                    severity="info",
                    title=f"Stale project: {p.name}",
                    description=f"'{p.name}' is still in '{status_val}' state. Consider advancing it.",
                    affected_project=p.project_id,
                    recommended_action="Evaluate and score the idea to move it through the pipeline.",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Dashboard summary endpoints
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary() -> DashboardSummary:
    """Return a comprehensive dashboard summary for the premium UI.

    Aggregates projects, health, recent factory builds, stats, and
    detected issues into a single payload.
    """
    try:
        repo = get_portfolio_repository()
        projects = repo.list_projects()
    except Exception:
        logger.warning("dashboard: Failed to read portfolio for summary.", exc_info=True)
        projects = []

    project_summaries = [_project_to_summary(p) for p in projects]

    # --- Health (reuse existing helper) ---
    total = len(projects)
    approved = sum(1 for p in projects if p.status in _APPROVED_STATES)
    blocked = sum(1 for p in projects if p.status in _BLOCKED_STATES)
    revenue_total = sum(ps.revenue for ps in project_summaries)
    health_status, summary = _compute_health(total, approved, revenue_total, blocked)
    health = DashboardHealth(
        total_projects=total,
        approved_count=approved,
        revenue_total=revenue_total,
        blocked_count=blocked,
        health_status=health_status,
        summary=summary,
    )

    # --- Recent builds ---
    recent_builds: list[dict[str, Any]] = []
    try:
        run_store = get_factory_run_store()
        runs = run_store.list_runs()
        for run in runs[:_MAX_RECENT_BUILDS]:
            recent_builds.append(
                {
                    "run_id": run.run_id,
                    "project_id": run.project_id,
                    "status": run.status.value if hasattr(run.status, "value") else str(run.status),
                    "deploy_url": run.deploy_url,
                    "repo_url": run.repo_url,
                    "created_at": run.created_at,
                    "updated_at": run.updated_at,
                }
            )
    except Exception:
        logger.warning("dashboard: Failed to fetch factory runs.", exc_info=True)

    # --- Stats ---
    venture_count = sum(1 for ps in project_summaries if ps.project_type == "venture")
    personal_count = sum(1 for ps in project_summaries if ps.project_type == "personal")
    stats: dict[str, Any] = {
        "total_projects": total,
        "approved_count": approved,
        "blocked_count": blocked,
        "revenue_total": revenue_total,
        "venture_count": venture_count,
        "personal_count": personal_count,
        "build_count": len(recent_builds),
    }

    # --- Issues ---
    issues = _detect_issues(projects)

    return DashboardSummary(
        projects=project_summaries,
        stats=stats,
        health=health,
        recent_builds=recent_builds,
        issues=issues,
    )


@router.patch("/projects/{project_id}/type")
def update_project_type(project_id: str, request: ProjectTypeUpdate) -> dict[str, str]:
    """Update a project's type classification (venture or personal).

    Stores the project_type in the project's metadata dict.
    """
    repo = get_portfolio_repository()
    project = repo.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = dict(project.metadata or {})
    metadata["project_type"] = request.project_type

    with repo._db.connect() as conn:
        conn.execute(
            "UPDATE projects SET metadata_json = ?, updated_at = ? WHERE project_id = ?",
            (json.dumps(metadata, sort_keys=True), utcnow_iso(), project_id),
        )

    return {"status": "ok", "project_id": project_id, "project_type": request.project_type}
