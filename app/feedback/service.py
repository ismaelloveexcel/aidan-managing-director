"""
Feedback service for metrics ingestion, user feedback, and deterministic policy evaluation.
"""

from __future__ import annotations

from app.feedback.decision_policy import decide
from app.feedback.models import (
    FEEDBACK_ACTION_MAP,
    DecisionResult,
    MetricsIngestRequest,
    MetricsIngestResponse,
    UserFeedbackRequest,
    UserFeedbackResponse,
    UserFeedbackType,
)
from app.memory.store import LearningSignal, MemoryStore
from app.portfolio.repository import PortfolioRepository


class FeedbackService:
    """Thin service wrapping repository operations and deterministic policy."""

    def __init__(
        self,
        repository: PortfolioRepository,
        memory_store: MemoryStore | None = None,
    ) -> None:
        self._repository = repository
        self._memory = memory_store

    def ingest_metrics(self, payload: MetricsIngestRequest) -> MetricsIngestResponse:
        """Normalize, persist metrics snapshot, and record deterministic decision audit event."""
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
        # Evaluate and record the decision once per ingestion so that the GET
        # endpoint remains a pure read without audit side-effects.
        decision = decide(
            visits=snapshot.visits,
            conversion_rate=snapshot.conversion_rate,
            revenue=snapshot.revenue,
            payment_attempted=payload.payment_attempted,
            payment_success=payload.payment_success,
        )
        self._repository.record_decision_applied(
            project_id=payload.project_id,
            decision={**decision.model_dump(mode="json"), "snapshot_id": snapshot.snapshot_id},
        )

        # Record payment signals in memory store.
        if self._memory is not None:
            if payload.payment_attempted:
                self._memory.record_signal(
                    LearningSignal(
                        project_id=payload.project_id,
                        signal_type="payment_attempted",
                        score=0.5 if not payload.payment_success else 1.0,
                        notes=f"payment_success={payload.payment_success}",
                    ),
                )
            if payload.payment_success:
                self._memory.record_signal(
                    LearningSignal(
                        project_id=payload.project_id,
                        signal_type="payment_success",
                        score=1.0,
                        notes=f"revenue_amount={payload.revenue_amount}",
                    ),
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
            payment_attempted=payload.payment_attempted,
            payment_success=payload.payment_success,
            revenue_amount=payload.revenue_amount,
        )

    def get_project_decision(self, project_id: str) -> DecisionResult | None:
        """Load latest metrics and compute deterministic decision (read-only)."""
        snapshot = self._repository.get_latest_metrics_snapshot(project_id)
        if snapshot is None:
            return None

        result = decide(
            visits=snapshot.visits,
            conversion_rate=snapshot.conversion_rate,
            revenue=snapshot.revenue,
        )
        return result

    # ------------------------------------------------------------------
    # User rejection / objection feedback
    # ------------------------------------------------------------------

    def process_user_feedback(self, payload: UserFeedbackRequest) -> UserFeedbackResponse:
        """Map user feedback to a deterministic action and store insight."""
        mapped_action = FEEDBACK_ACTION_MAP[payload.feedback_type]

        # Persist as memory signal for auto-learning.
        if self._memory is not None:
            score_map: dict[UserFeedbackType, float] = {
                UserFeedbackType.TOO_EXPENSIVE: 0.3,
                UserFeedbackType.NOT_CLEAR: 0.4,
                UserFeedbackType.NOT_NEEDED: 0.1,
                UserFeedbackType.OTHER: 0.5,
            }
            self._memory.record_signal(
                LearningSignal(
                    project_id=payload.project_id,
                    signal_type=f"user_feedback_{payload.feedback_type.value}",
                    score=score_map[payload.feedback_type],
                    notes=payload.detail or "",
                ),
            )
            self._memory.record_event(
                {
                    "event_type": "user_feedback",
                    "project_id": payload.project_id,
                    "feedback_type": payload.feedback_type.value,
                    "mapped_action": mapped_action.value,
                    "detail": payload.detail,
                },
            )

        return UserFeedbackResponse(
            project_id=payload.project_id,
            feedback_type=payload.feedback_type,
            mapped_action=mapped_action,
            detail=payload.detail,
        )

