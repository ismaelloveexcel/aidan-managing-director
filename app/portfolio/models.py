"""
Typed models for portfolio persistence and lifecycle control.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utcnow_iso() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


class LifecycleState(str, Enum):
    """Canonical project lifecycle states."""

    IDEA = "idea"
    REVIEW = "review"
    APPROVED = "approved"
    QUEUED = "queued"
    BUILDING = "building"
    LAUNCHED = "launched"
    MONITORING = "monitoring"
    SCALED = "scaled"
    KILLED = "killed"


class PortfolioProjectRecord(BaseModel):
    """Persistent project record."""

    project_id: str
    name: str
    description: str
    status: LifecycleState
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class BuildBriefRecord(BaseModel):
    """Persistent BuildBrief record."""

    brief_id: str
    project_id: str
    schema_version: str
    brief_hash: str
    idempotency_key: str
    payload: dict[str, Any]
    validation_score: float = 0.0
    risk_flags: list[str] = Field(default_factory=list)
    monetization_model: str = ""
    deployment_plan: dict[str, Any] = Field(default_factory=dict)
    launch_gate: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class PortfolioEventRecord(BaseModel):
    """Audit event persisted for a project."""

    event_id: str
    project_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class MetricsSnapshotRecord(BaseModel):
    """Persistent metrics snapshot used by the feedback engine."""

    snapshot_id: str
    project_id: str
    visits: int
    signups: int
    revenue: float
    currency: str
    conversion_rate: float
    timestamp: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class FactoryRunRecord(BaseModel):
    """Persistent copy of a factory run output."""

    run_id: str
    project_id: str
    idea_id: str
    status: str
    idempotency_key: str
    dry_run: bool
    repo_url: str | None = None
    deploy_url: str | None = None
    error: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str
