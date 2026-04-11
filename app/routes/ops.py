"""
ops.py – Solo-founder operational endpoints.

Provides health/readiness checks, SLO dashboard data, and dead-letter
queue visibility so a solo operator can debug fast without digging
through logs or SQL.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.dependencies import (
    get_dead_letter_queue,
    get_factory_run_store,
    get_ops_event_store,
    get_portfolio_repository,
)
from app.factory.dead_letter import DeadLetterEntry

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Readiness gate — /ops/ready
# ---------------------------------------------------------------------------


class ReadinessCheck(BaseModel):
    """Individual readiness check result."""

    name: str
    ok: bool
    detail: str = ""


class ReadinessResponse(BaseModel):
    """Aggregate readiness gate response."""

    ready: bool
    checks: list[ReadinessCheck]


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_gate() -> ReadinessResponse:
    """Validate that the system is ready for production traffic.

    Checks:
    - Required secrets are present
    - Portfolio DB is accessible
    - Factory run store is reachable
    """
    checks: list[ReadinessCheck] = []

    # 1. Secrets
    settings = get_settings()
    missing = settings.validate_production_secrets()
    checks.append(
        ReadinessCheck(
            name="secrets",
            ok=len(missing) == 0,
            detail=f"missing: {', '.join(missing)}" if missing else "all present",
        )
    )

    # 2. Portfolio DB
    try:
        repo = get_portfolio_repository()
        projects = repo.list_projects()
        checks.append(
            ReadinessCheck(
                name="portfolio_db",
                ok=True,
                detail=f"{len(projects)} projects",
            )
        )
    except Exception as exc:
        checks.append(
            ReadinessCheck(name="portfolio_db", ok=False, detail=str(exc))
        )

    # 3. Factory run store
    try:
        store = get_factory_run_store()
        runs = store.list_runs()
        checks.append(
            ReadinessCheck(
                name="factory_run_store",
                ok=True,
                detail=f"{len(runs)} runs",
            )
        )
    except Exception as exc:
        checks.append(
            ReadinessCheck(name="factory_run_store", ok=False, detail=str(exc))
        )

    # 4. Callback secret configured
    checks.append(
        ReadinessCheck(
            name="callback_secret",
            ok=bool(settings.factory_callback_secret),
            detail="configured" if settings.factory_callback_secret else "missing",
        )
    )

    # 5. Public base URL configured
    checks.append(
        ReadinessCheck(
            name="public_base_url",
            ok=bool(settings.public_base_url),
            detail=settings.public_base_url or "not set",
        )
    )

    all_ok = all(c.ok for c in checks)
    return ReadinessResponse(ready=all_ok, checks=checks)


# ---------------------------------------------------------------------------
# SLO Dashboard — /ops/slo
# ---------------------------------------------------------------------------


class SLOResponse(BaseModel):
    """SLO dashboard data for solo-founder visibility."""

    window_hours: int
    event_types: dict[str, Any] = Field(default_factory=dict)
    stuck_jobs: list[dict[str, Any]] = Field(default_factory=list)
    dead_letter_counts: dict[str, int] = Field(default_factory=dict)


@router.get("/slo", response_model=SLOResponse)
async def slo_dashboard(hours: int = 24) -> SLOResponse:
    """Return SLO metrics for the operator dashboard.

    Includes:
    - Per-event-type success rates (dispatch, callback, deployment)
    - Stuck jobs (dispatched but no callback within 30 minutes)
    - Dead-letter queue counts by status
    """
    ops = get_ops_event_store()
    dlq = get_dead_letter_queue()

    summary = ops.slo_summary(hours=hours)
    stuck = ops.stuck_jobs(max_age_minutes=30)
    dlq_counts = dlq.count_by_status()

    return SLOResponse(
        window_hours=hours,
        event_types=summary.get("event_types", {}),
        stuck_jobs=stuck,
        dead_letter_counts=dlq_counts,
    )


# ---------------------------------------------------------------------------
# Dead-letter queue — /ops/dlq
# ---------------------------------------------------------------------------


class DLQListResponse(BaseModel):
    """Response for listing dead-letter queue entries."""

    entries: list[DeadLetterEntry]
    total: int


@router.get("/dlq", response_model=DLQListResponse)
async def list_dead_letter_entries(limit: int = 50) -> DLQListResponse:
    """List dead-letter queue entries for operator review."""
    dlq = get_dead_letter_queue()
    entries = dlq.list_all(limit=limit)
    return DLQListResponse(entries=entries, total=len(entries))


@router.post("/dlq/{dlq_id}/resolve", response_model=dict[str, str])
async def resolve_dead_letter(dlq_id: str) -> dict[str, str]:
    """Mark a dead-letter entry as resolved."""
    dlq = get_dead_letter_queue()
    dlq.mark_resolved(dlq_id)
    return {"dlq_id": dlq_id, "status": "resolved"}
