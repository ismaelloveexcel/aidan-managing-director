"""
Portfolio intelligence heuristics for cross-project decision support.
"""

from __future__ import annotations

from dataclasses import dataclass

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


class PortfolioIntelligenceService:
    """Deterministic portfolio-level ranking and recommendation service."""

    def __init__(self, repository: PortfolioRepository) -> None:
        self._repository = repository

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
