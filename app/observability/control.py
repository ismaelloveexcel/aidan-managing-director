"""
Control-plane observability snapshot service.
"""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.portfolio.models import LifecycleState
from app.portfolio.repository import PortfolioRepository


@dataclass(frozen=True)
class ControlSnapshot:
    """Aggregated operational snapshot for command-center consumption."""

    total_projects: int
    active_projects: int
    blocked_projects: int
    lifecycle_counts: dict[str, int]
    pending_approvals: int


class CircuitState(str, Enum):
    """Circuit breaker state for guarded subsystems."""

    OPEN = "open"
    CLOSED = "closed"


@dataclass
class CircuitRecord:
    """In-memory circuit breaker record."""

    circuit: str
    state: CircuitState
    reason: str


class ControlPlaneService:
    """Build deterministic portfolio-level operational snapshots."""

    def __init__(
        self,
        *,
        repository: PortfolioRepository,
        pending_approvals_provider: callable | None = None,
    ) -> None:
        self._repository = repository
        self._pending_approvals_provider = pending_approvals_provider
        self._circuits: dict[str, CircuitRecord] = {}

    def snapshot(self) -> ControlSnapshot:
        """Return a normalized control snapshot for the current system state."""
        projects = self._repository.list_projects()
        lifecycle_counts = {state.value: 0 for state in LifecycleState}
        for project in projects:
            lifecycle_counts[project.status.value] = lifecycle_counts.get(project.status.value, 0) + 1

        active_projects = (
            lifecycle_counts.get(LifecycleState.BUILDING.value, 0)
            + lifecycle_counts.get(LifecycleState.LAUNCHED.value, 0)
            + lifecycle_counts.get(LifecycleState.MONITORING.value, 0)
            + lifecycle_counts.get(LifecycleState.SCALED.value, 0)
        )
        blocked_projects = lifecycle_counts.get(LifecycleState.KILLED.value, 0)

        pending_approvals = 0
        if self._pending_approvals_provider is not None:
            pending_approvals = len(self._pending_approvals_provider())

        return ControlSnapshot(
            total_projects=len(projects),
            active_projects=active_projects,
            blocked_projects=blocked_projects,
            lifecycle_counts=lifecycle_counts,
            pending_approvals=pending_approvals,
        )

    def set_circuit(self, circuit: str, state: CircuitState, reason: str = "") -> None:
        """Set or update a named circuit breaker state."""
        key = circuit.strip().lower()
        self._circuits[key] = CircuitRecord(
            circuit=key,
            state=state,
            reason=reason.strip(),
        )

    def get_circuit(self, circuit: str) -> CircuitRecord:
        """Return circuit state (defaults to closed for unknown circuits)."""
        key = circuit.strip().lower()
        if key not in self._circuits:
            self._circuits[key] = CircuitRecord(
                circuit=key,
                state=CircuitState.CLOSED,
                reason="default",
            )
        return self._circuits[key]

    def list_circuits(self) -> list[dict[str, Any]]:
        """Return all circuit breaker records as dictionaries."""
        return [asdict(record) for record in self._circuits.values()]
