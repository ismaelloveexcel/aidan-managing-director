"""
Portfolio intelligence heuristics for cross-project decision support.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.portfolio.models import LifecycleState
from app.portfolio.repository import PortfolioRepository


@dataclass
class PortfolioProjectHealth:
    """Simple health signal for a single portfolio project."""

    project_id: str
    name: str
    status: str
    conversion_rate: float | None
    revenue: float | None
    health_score: float
    recommendation: str


@dataclass(frozen=True)
class OperatorLimits:
    """Hard sustainability limits for one non-technical operator."""

    max_active_projects: int = 3
    max_builds_in_parallel: int = 2
    max_launches_per_week: int = 2


@dataclass
class OperatorCapacityStatus:
    """Snapshot of operator capacity and whether new work should be held."""

    active_projects: int
    builds_in_parallel: int
    launches_this_week: int
    limits: OperatorLimits
    should_hold_new_projects: bool
    reason: str


class PortfolioIntelligenceService:
    """Deterministic portfolio-level ranking and recommendation service."""

    def __init__(self, repository: PortfolioRepository) -> None:
        self._repository = repository
        self._limits = OperatorLimits()

    @property
    def limits(self) -> OperatorLimits:
        """Return operator limits used for overload protection."""
        return self._limits

    def project_health(self, project_id: str) -> PortfolioProjectHealth | None:
        """Return a deterministic health projection for a project."""
        project = self._repository.get_project(project_id)
        if project is None:
            return None
        metrics = self._repository.get_latest_metrics_snapshot(project_id)
        conversion = metrics.conversion_rate if metrics is not None else None
        revenue = metrics.revenue if metrics is not None else None
        health_score = self._compute_health_score(
            status=project.status,
            conversion_rate=conversion,
            revenue=revenue,
        )
        return PortfolioProjectHealth(
            project_id=project.project_id,
            name=project.name,
            status=project.status.value,
            conversion_rate=conversion,
            revenue=revenue,
            health_score=health_score,
            recommendation=self._recommend(health_score),
        )

    def ranked_projects(self) -> list[PortfolioProjectHealth]:
        """Return all projects sorted from strongest to weakest signal."""
        ranked: list[PortfolioProjectHealth] = []
        for project in self._repository.list_projects():
            health = self.project_health(project.project_id)
            if health is not None:
                ranked.append(health)
        ranked.sort(key=lambda item: item.health_score, reverse=True)
        return ranked

    def operator_capacity(self) -> OperatorCapacityStatus:
        """Return deterministic operator capacity status and hold recommendation."""
        active_states = {
            LifecycleState.APPROVED,
            LifecycleState.QUEUED,
            LifecycleState.BUILDING,
            LifecycleState.LAUNCHED,
            LifecycleState.MONITORING,
            LifecycleState.SCALED,
        }
        active_projects = self._repository.count_projects_by_state(active_states)
        builds_in_parallel = self._repository.count_factory_runs_by_status({"pending", "running"})
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        launches_this_week = self._repository.count_events_since(event_type="deployed", since_iso=since)

        if active_projects >= self._limits.max_active_projects:
            return OperatorCapacityStatus(
                active_projects=active_projects,
                builds_in_parallel=builds_in_parallel,
                launches_this_week=launches_this_week,
                limits=self._limits,
                should_hold_new_projects=True,
                reason="Max active projects reached.",
            )
        if builds_in_parallel >= self._limits.max_builds_in_parallel:
            return OperatorCapacityStatus(
                active_projects=active_projects,
                builds_in_parallel=builds_in_parallel,
                launches_this_week=launches_this_week,
                limits=self._limits,
                should_hold_new_projects=True,
                reason="Max parallel builds reached.",
            )
        if launches_this_week >= self._limits.max_launches_per_week:
            return OperatorCapacityStatus(
                active_projects=active_projects,
                builds_in_parallel=builds_in_parallel,
                launches_this_week=launches_this_week,
                limits=self._limits,
                should_hold_new_projects=True,
                reason="Max weekly launches reached.",
            )
        return OperatorCapacityStatus(
            active_projects=active_projects,
            builds_in_parallel=builds_in_parallel,
            launches_this_week=launches_this_week,
            limits=self._limits,
            should_hold_new_projects=False,
            reason="Capacity available.",
        )

    def should_hold_new_project(self) -> tuple[bool, str]:
        """Return whether new project intake should be held."""
        status = self.operator_capacity()
        return status.should_hold_new_projects, status.reason

    def generate_daily_digest(self) -> list[str]:
        """Return top-3 prioritized actions for one-operator execution."""
        actions: list[str] = []
        capacity = self.operator_capacity()
        if capacity.should_hold_new_projects:
            actions.append(f"1) HOLD new projects: {capacity.reason}")
        else:
            actions.append("1) Approve one highest-scoring queued idea for execution.")

        ranked = self.ranked_projects()
        if ranked:
            strongest = ranked[0]
            actions.append(
                f"2) Focus {strongest.project_id} ({strongest.name}) - recommendation: {strongest.recommendation}.",
            )
        else:
            actions.append("2) Validate one new idea and keep intake below active-project limits.")

        if capacity.builds_in_parallel > 0:
            actions.append("3) Unblock running builds before adding new workload.")
        else:
            actions.append("3) Prepare one launch campaign on exactly two channels.")

        return actions[:3]

    @staticmethod
    def _compute_health_score(
        *,
        status: LifecycleState,
        conversion_rate: float | None,
        revenue: float | None,
    ) -> float:
        """Compute a deterministic health score in [0, 1]."""
        status_weight = {
            LifecycleState.IDEA: 0.15,
            LifecycleState.REVIEW: 0.25,
            LifecycleState.APPROVED: 0.4,
            LifecycleState.QUEUED: 0.45,
            LifecycleState.BUILDING: 0.5,
            LifecycleState.LAUNCHED: 0.6,
            LifecycleState.MONITORING: 0.65,
            LifecycleState.SCALED: 0.9,
            LifecycleState.KILLED: 0.05,
        }[status]

        conversion_component = 0.0 if conversion_rate is None else min(conversion_rate * 10.0, 0.3)
        revenue_component = 0.0 if revenue is None else min(revenue / 10000.0, 0.3)
        score = round(min(status_weight + conversion_component + revenue_component, 1.0), 2)
        return score

    @staticmethod
    def _recommend(health_score: float) -> str:
        if health_score >= 0.8:
            return "scale"
        if health_score >= 0.55:
            return "monitor"
        if health_score >= 0.35:
            return "revise"
        return "kill"
