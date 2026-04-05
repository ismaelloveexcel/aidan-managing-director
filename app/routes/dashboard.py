"""
dashboard.py – Dashboard health and design token routes.

GET /api/dashboard/health  – Portfolio health summary (for dynamic theming).
GET /api/dashboard/tokens  – Design token JSON for visual consistency.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import get_portfolio_repository
from app.portfolio.models import LifecycleState

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
            pass  # Skip projects with non-numeric revenue metadata

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
