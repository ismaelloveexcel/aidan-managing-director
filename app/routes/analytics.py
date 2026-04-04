"""
analytics.py – Routes for analytics tracking (visits, clicks, conversions, revenue).

Provides a lightweight event-based analytics layer that feeds into the
feedback and auto-learning systems.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import (
    get_memory_store,
    get_portfolio_repository,
)

router = APIRouter()

_memory = get_memory_store()
_portfolio = get_portfolio_repository()


class AnalyticsEvent(BaseModel):
    """Single analytics event payload."""

    project_id: str
    event_type: str = Field(
        description="One of: page_view, click, signup, purchase, custom",
    )
    value: float = Field(default=0.0, description="Monetary value if applicable")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsEventResponse(BaseModel):
    """Response after recording an analytics event."""

    status: str = "ok"
    project_id: str
    event_type: str


class AnalyticsSummary(BaseModel):
    """Aggregated analytics summary for a project."""

    project_id: str
    total_page_views: int = 0
    total_clicks: int = 0
    total_signups: int = 0
    total_purchases: int = 0
    total_revenue: float = 0.0
    events_recorded: int = 0


@router.post("/events", response_model=AnalyticsEventResponse)
async def record_analytics_event(event: AnalyticsEvent) -> AnalyticsEventResponse:
    """Record a single analytics event for a project."""
    allowed_types = {"page_view", "click", "signup", "purchase", "custom"}
    if event.event_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(sorted(allowed_types))}",
        )

    _memory.record_event(
        {
            "event_type": "analytics",
            "analytics_event_type": event.event_type,
            "project_id": event.project_id,
            "value": event.value,
            "metadata": event.metadata,
        },
    )
    return AnalyticsEventResponse(
        project_id=event.project_id,
        event_type=event.event_type,
    )


@router.get("/projects/{project_id}/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(project_id: str) -> AnalyticsSummary:
    """Return aggregated analytics for a project from memory events."""
    events = _memory.recent_events(limit=2000)
    analytics_events = [
        e for e in events
        if e.get("event_type") == "analytics" and e.get("project_id") == project_id
    ]

    page_views = 0
    clicks = 0
    signups = 0
    purchases = 0
    revenue = 0.0

    for event in analytics_events:
        atype = event.get("analytics_event_type", "")
        val = float(event.get("value", 0.0))
        if atype == "page_view":
            page_views += 1
        elif atype == "click":
            clicks += 1
        elif atype == "signup":
            signups += 1
        elif atype == "purchase":
            purchases += 1
            revenue += val

    return AnalyticsSummary(
        project_id=project_id,
        total_page_views=page_views,
        total_clicks=clicks,
        total_signups=signups,
        total_purchases=purchases,
        total_revenue=round(revenue, 2),
        events_recorded=len(analytics_events),
    )
