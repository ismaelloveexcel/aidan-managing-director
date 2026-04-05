"""
Analytics tracker – tracks visits, clicks, conversions, revenue.

Decides:
- no traction → KILL
- interest → ITERATE
- revenue → SCALE
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TrackerDecision(str, Enum):
    """Analytics-based decisions."""

    KILL = "kill"
    ITERATE = "iterate"
    SCALE = "scale"
    MONITOR = "monitor"


class AnalyticsSnapshot(BaseModel):
    """Point-in-time analytics snapshot."""

    project_id: str
    visits: int = 0
    clicks: int = 0
    signups: int = 0
    conversions: int = 0
    revenue: float = 0.0
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


class AnalyticsDecision(BaseModel):
    """Decision based on analytics data."""

    project_id: str
    decision: TrackerDecision
    reason: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str = ""
    confidence: float = 0.0


class AnalyticsTracker:
    """Tracks project analytics and makes data-driven decisions."""

    def __init__(self) -> None:
        self._snapshots: dict[str, list[AnalyticsSnapshot]] = {}
        self._lock = threading.Lock()

    def record_event(
        self,
        project_id: str,
        *,
        event_type: str,
        value: float = 0.0,
    ) -> AnalyticsSnapshot:
        """Record an analytics event and return updated snapshot.

        Args:
            project_id: Project identifier.
            event_type: One of visit, click, signup, conversion, revenue.
            value: Numeric value (revenue amount for revenue events).

        Returns:
            Updated AnalyticsSnapshot.
        """
        with self._lock:
            snapshots = self._snapshots.setdefault(project_id, [])

            # Get or create current snapshot
            if snapshots:
                current = snapshots[-1].model_copy()
            else:
                current = AnalyticsSnapshot(project_id=project_id)

            # Update based on event type
            event_lower = event_type.lower()
            if event_lower in {"visit", "page_view", "pageview"}:
                current.visits += 1
            elif event_lower == "click":
                current.clicks += 1
            elif event_lower == "signup":
                current.signups += 1
            elif event_lower in {"conversion", "purchase"}:
                current.conversions += 1
                current.revenue += max(value, 0.0)
            elif event_lower == "revenue":
                current.revenue += max(value, 0.0)

            current.timestamp = datetime.now(timezone.utc).isoformat()
            snapshots.append(current)
            return current

    def get_latest(self, project_id: str) -> AnalyticsSnapshot | None:
        """Get the latest analytics snapshot for a project."""
        snapshots = self._snapshots.get(project_id, [])
        return snapshots[-1] if snapshots else None

    def get_history(self, project_id: str) -> list[AnalyticsSnapshot]:
        """Get full analytics history for a project."""
        return list(self._snapshots.get(project_id, []))

    def decide(self, project_id: str) -> AnalyticsDecision:
        """Make a data-driven decision based on analytics.

        Rules:
        - revenue > 0 & conversions >= 3 → SCALE
        - visits >= 100 & conversions == 0 & revenue == 0 → KILL
        - visits >= 50 & clicks > 0 but no conversions → ITERATE
        - insufficient data → MONITOR

        Args:
            project_id: Project to evaluate.

        Returns:
            AnalyticsDecision with recommendation.
        """
        snapshot = self.get_latest(project_id)

        if snapshot is None:
            return AnalyticsDecision(
                project_id=project_id,
                decision=TrackerDecision.MONITOR,
                reason="No analytics data available.",
                recommended_action="Continue collecting metrics.",
                confidence=0.3,
            )

        metrics = {
            "visits": snapshot.visits,
            "clicks": snapshot.clicks,
            "signups": snapshot.signups,
            "conversions": snapshot.conversions,
            "revenue": snapshot.revenue,
        }

        # Rule 1: Revenue + conversions → SCALE
        if snapshot.revenue > 0 and snapshot.conversions >= 3:
            return AnalyticsDecision(
                project_id=project_id,
                decision=TrackerDecision.SCALE,
                reason=(
                    f"Revenue ${snapshot.revenue:.2f} with "
                    f"{snapshot.conversions} conversions — ready to scale."
                ),
                metrics=metrics,
                recommended_action="Increase distribution budget and expand channels.",
                confidence=0.92,
            )

        # Rule 2: Traffic but no traction → KILL
        if snapshot.visits >= 100 and snapshot.conversions == 0 and snapshot.revenue == 0:
            return AnalyticsDecision(
                project_id=project_id,
                decision=TrackerDecision.KILL,
                reason=(
                    f"{snapshot.visits} visits but zero conversions and no revenue "
                    "— product-market fit unlikely."
                ),
                metrics=metrics,
                recommended_action="Stop investment. Analyze failure and move to next idea.",
                confidence=0.88,
            )

        # Rule 3: Some interest but no conversions → ITERATE
        if snapshot.visits >= 50 and snapshot.clicks > 0 and snapshot.conversions == 0:
            return AnalyticsDecision(
                project_id=project_id,
                decision=TrackerDecision.ITERATE,
                reason=(
                    f"{snapshot.visits} visits, {snapshot.clicks} clicks but no conversions "
                    "— interest exists, offer needs iteration."
                ),
                metrics=metrics,
                recommended_action="Revise pricing, CTA, or landing page copy.",
                confidence=0.75,
            )

        # Rule 4: Early revenue signal → SCALE (even with few conversions)
        if snapshot.revenue > 0:
            return AnalyticsDecision(
                project_id=project_id,
                decision=TrackerDecision.SCALE,
                reason=f"Revenue detected (${snapshot.revenue:.2f}) — early traction signal.",
                metrics=metrics,
                recommended_action="Double down on converting channel.",
                confidence=0.80,
            )

        # Default: Not enough data
        return AnalyticsDecision(
            project_id=project_id,
            decision=TrackerDecision.MONITOR,
            reason=(
                f"Insufficient signal: {snapshot.visits} visits, "
                f"{snapshot.clicks} clicks. Need more data."
            ),
            metrics=metrics,
            recommended_action="Continue distribution and monitor.",
            confidence=0.5,
        )

    def reset(self, project_id: str) -> None:
        """Clear analytics data for a project."""
        with self._lock:
            self._snapshots.pop(project_id, None)
