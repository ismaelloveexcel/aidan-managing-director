"""
dashboard.py – Dynamic dashboard theming routes.

Provides portfolio health snapshots and auto-generated design tokens that
change color based on portfolio health (green = healthy, amber = warning,
red = critical).  The Factory and other consumers can poll these endpoints
to apply consistent, context-aware visual theming.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends

from app.core.dependencies import get_portfolio_repository
from app.portfolio.models import LifecycleState
from app.portfolio.repository import PortfolioRepository

router = APIRouter()

# ---------------------------------------------------------------------------
# Theme colour palettes keyed by health status
# ---------------------------------------------------------------------------
_THEMES: dict[str, dict[str, str]] = {
    "healthy": {
        "primary_color": "#22c55e",   # green-500
        "background": "#052e16",       # green-950
        "surface": "#14532d",          # green-900
        "text": "#dcfce7",             # green-50
        "accent": "#4ade80",           # green-400
        "success": "#16a34a",          # green-600
        "warning": "#facc15",          # yellow-400
        "danger": "#ef4444",           # red-500
    },
    "warning": {
        "primary_color": "#f59e0b",   # amber-500
        "background": "#1c1100",       # custom dark amber
        "surface": "#292400",          # custom dark amber surface
        "text": "#fef3c7",             # amber-100
        "accent": "#fbbf24",           # amber-400
        "success": "#22c55e",          # green-500
        "warning": "#f59e0b",          # amber-500
        "danger": "#ef4444",           # red-500
    },
    "critical": {
        "primary_color": "#ef4444",   # red-500
        "background": "#1c0505",       # custom dark red
        "surface": "#2d0a0a",          # custom dark red surface
        "text": "#fee2e2",             # red-100
        "accent": "#f87171",           # red-400
        "success": "#22c55e",          # green-500
        "warning": "#f59e0b",          # amber-500
        "danger": "#dc2626",           # red-600
    },
}

_ACTIVE_STATES: frozenset[LifecycleState] = frozenset(
    {
        LifecycleState.APPROVED,
        LifecycleState.QUEUED,
        LifecycleState.BUILDING,
        LifecycleState.LAUNCHED,
        LifecycleState.MONITORING,
        LifecycleState.SCALED,
    }
)


def _compute_health(active_projects: int) -> Literal["healthy", "warning", "critical"]:
    """Derive portfolio health status from active project count."""
    if active_projects >= 3:
        return "healthy"
    if active_projects >= 1:
        return "warning"
    return "critical"


@router.get("/health")
def get_portfolio_health(
    repo: PortfolioRepository = Depends(get_portfolio_repository),
) -> dict:
    """Return a portfolio health snapshot with auto-derived theme.

    Health levels:
    - **healthy** – 3 or more active projects
    - **warning** – 1–2 active projects
    - **critical** – no active projects
    """
    projects = repo.list_projects()
    active = [p for p in projects if p.status in _ACTIVE_STATES]
    total_revenue = sum(
        float(p.metadata.get("revenue", 0.0) or 0.0)
        for p in projects
    )

    status = _compute_health(len(active))
    theme = _THEMES[status]

    return {
        "status": status,
        "active_projects": len(active),
        "total_revenue": round(total_revenue, 2),
        "theme": theme,
    }


@router.get("/tokens")
def get_design_tokens(
    repo: PortfolioRepository = Depends(get_portfolio_repository),
) -> dict:
    """Return structured design tokens based on current portfolio health.

    The token set mirrors Tailwind-compatible colour values and can be
    injected directly into factory-generated product UIs.
    """
    projects = repo.list_projects()
    active = [p for p in projects if p.status in _ACTIVE_STATES]
    status = _compute_health(len(active))
    return _THEMES[status]
