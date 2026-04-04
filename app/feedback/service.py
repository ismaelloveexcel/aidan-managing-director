"""
Feedback service for metrics ingestion and deterministic policy evaluation.
"""

from __future__ import annotations

from app.feedback.decision_policy import decide
from app.feedback.models import (
    DecisionResult,
    MetricsIngestRequest,
    MetricsIngestResponse,
)
from app.portfolio.repository import PortfolioRepository


class FeedbackService:
    """Thin service wrapping repository operations and deterministic policy."""

    def __init__(self, repository: PortfolioRepository) -> None:
        self._repository = repository

    def ingest_metrics(self, payload: MetricsIngestRequest) -> MetricsIngestResponse:
        """Normalize and persist metrics snapshot."""
        project = self._repository.get_project(payload.project_id)
        if project is None:
            raise LookupError(f"Project not found: {payload.project_id}")

        snapshot = self._repository.save_metrics_snapshot(
            project_id=payload.project_id,
            visits=payload.visits,
            signups=payload.signups,
            revenue=payload.revenue,
            currency=payload.currency,
            timestamp=payload.timestamp,
            raw_payload=payload.model_dump(mode="json"),
        )
        return MetricsIngestResponse(
            snapshot_id=snapshot.snapshot_id,
            project_id=snapshot.project_id,
            visits=snapshot.visits,
            signups=snapshot.signups,
            revenue=snapshot.revenue,
            currency=snapshot.currency,
            conversion_rate=snapshot.conversion_rate,
            timestamp=snapshot.timestamp,
            created_at=snapshot.created_at,
        )

    def get_project_decision(self, project_id: str) -> DecisionResult | None:
        """Load latest metrics and compute deterministic decision."""
        snapshot = self._repository.get_latest_metrics_snapshot(project_id)
        if snapshot is None:
            return None

        result = decide(
            visits=snapshot.visits,
            conversion_rate=snapshot.conversion_rate,
            revenue=snapshot.revenue,
        )
        # Record audit-only decision event (no lifecycle mutation yet).
        self._repository.record_decision_applied(
            project_id=project_id,
            decision=result.model_dump(mode="json"),
        )
        return result

