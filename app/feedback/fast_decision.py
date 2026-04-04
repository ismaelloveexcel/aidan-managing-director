"""
Fast decision engine with strict iteration limits and kill/scale rules.

Rules:
- visits >= 100 AND conversions = 0 -> KILL
- visits >= 100 AND interest only (signups > 0, revenue = 0) -> ITERATE ONCE
- revenue detected -> SCALE
- no traffic -> change distribution ONCE -> if still none -> KILL
- MAX 1 iteration per project; NO infinite loops.
"""

from __future__ import annotations

import threading
from typing import Literal

from pydantic import BaseModel, Field


class FastDecision(BaseModel):
    """Output of the fast decision engine."""

    action: Literal["KILL", "ITERATE", "SCALE", "CHANGE_DISTRIBUTION", "MONITOR"]
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    iteration_count: int = 0
    max_iterations: int = 1
    can_iterate: bool = True


# Project-level iteration tracking (in-memory; replaced by DB/SQLite in Phase 2).
# Protected by a lock for thread-safety across concurrent requests.
_iteration_tracker: dict[str, int] = {}
_tracker_lock = threading.Lock()


def reset_tracker() -> None:
    """Clear iteration tracking state (for testing)."""
    with _tracker_lock:
        _iteration_tracker.clear()


def fast_decide(
    *,
    project_id: str,
    visits: int,
    signups: int,
    revenue: float,
    has_distribution: bool = True,
    distribution_changed: bool = False,
) -> FastDecision:
    """Apply strict fast-decision rules with iteration limits.

    Args:
        project_id: Unique project identifier.
        visits: Total page visits.
        signups: Total sign-ups or leads.
        revenue: Total revenue generated.
        has_distribution: Whether any distribution channel is active.
        distribution_changed: Whether distribution was already changed once.

    Returns:
        A FastDecision with the action, reason, and iteration metadata.
    """
    with _tracker_lock:
        iterations = _iteration_tracker.get(project_id, 0)
        can_iterate = iterations < 1

        # Rule 1: Revenue detected -> SCALE immediately.
        if revenue > 0:
            return FastDecision(
                action="SCALE",
                reason="Revenue detected; scale distribution and feature expansion.",
                confidence=0.92,
                iteration_count=iterations,
                can_iterate=can_iterate,
            )

        # Rule 2: Sufficient traffic but zero conversions -> KILL.
        if visits >= 100 and signups == 0 and revenue == 0:
            return FastDecision(
                action="KILL",
                reason="100+ visits with zero conversions; project is not viable.",
                confidence=0.90,
                iteration_count=iterations,
                can_iterate=False,
            )

        # Rule 3: Traffic with interest (signups) but no revenue -> ITERATE once.
        if visits >= 100 and signups > 0 and revenue == 0:
            if can_iterate:
                _iteration_tracker[project_id] = iterations + 1
                return FastDecision(
                    action="ITERATE",
                    reason="Interest detected but no revenue; iterate messaging/CTA once.",
                    confidence=0.82,
                    iteration_count=iterations + 1,
                    can_iterate=False,
                )
            return FastDecision(
                action="KILL",
                reason="Already iterated once with no revenue; project killed.",
                confidence=0.88,
                iteration_count=iterations,
                can_iterate=False,
            )

        # Rule 4: No traffic -> change distribution once, then kill.
        # All CHANGE_DISTRIBUTION paths consume the single allowed iteration.
        if visits < 10 and not has_distribution:
            if can_iterate:
                _iteration_tracker[project_id] = iterations + 1
                return FastDecision(
                    action="CHANGE_DISTRIBUTION",
                    reason="No distribution channel active; activate one before deciding.",
                    confidence=0.75,
                    iteration_count=iterations + 1,
                    can_iterate=False,
                )
            return FastDecision(
                action="KILL",
                reason="Distribution was already changed once with no traffic; project killed.",
                confidence=0.85,
                iteration_count=iterations,
                can_iterate=False,
            )

        if visits < 10 and distribution_changed:
            return FastDecision(
                action="KILL",
                reason="Distribution changed but still no traffic; project killed.",
                confidence=0.85,
                iteration_count=iterations,
                can_iterate=False,
            )

        if visits < 10 and has_distribution:
            if can_iterate:
                _iteration_tracker[project_id] = iterations + 1
                return FastDecision(
                    action="CHANGE_DISTRIBUTION",
                    reason="No traffic despite active distribution; change channel once.",
                    confidence=0.78,
                    iteration_count=iterations + 1,
                    can_iterate=False,
                )
            return FastDecision(
                action="KILL",
                reason="Already changed distribution once with no traffic; project killed.",
                confidence=0.85,
                iteration_count=iterations,
                can_iterate=False,
            )

        # Default: continue monitoring.
        return FastDecision(
            action="MONITOR",
            reason="Insufficient signal for decisive action; continue collecting data.",
            confidence=0.60,
            iteration_count=iterations,
            can_iterate=can_iterate,
        )
