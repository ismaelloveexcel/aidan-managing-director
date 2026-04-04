"""
Command Center service for operator-oriented command summaries and controls.
"""

from __future__ import annotations

from app.command_center.models import (
    CommandCenterState,
    CommandCenterEntry,
    CommandCenterSummary,
    CommandStatusUpdateRequest,
)
from app.factory.orchestrator import FactoryRunStore
from app.governance.service import GovernanceService
from app.integrations.registry_client import RegistryClient
from app.portfolio.models import LifecycleState
from app.portfolio.repository import PortfolioRepository


class CommandCenterService:
    """Builds operator-focused command summaries from registry records."""

    def __init__(
        self,
        *,
        registry: RegistryClient,
        portfolio: PortfolioRepository,
        governance: GovernanceService,
        factory_run_store: FactoryRunStore,
    ) -> None:
        self._registry = registry
        self._portfolio = portfolio
        self._governance = governance
        self._factory_run_store = factory_run_store

    def summarize(self) -> CommandCenterSummary:
        """Return queue summary + latest commands."""
        commands = self._registry.list_command_records()
        if not commands:
            return CommandCenterSummary(total_commands=0, pending=0, running=0, failed=0, latest=[])

        entries = [
            CommandCenterEntry(
                command_id=item["record_id"],
                command_type=item["command_type"],
                status=item.get("status", "pending"),
                project_id=item.get("project_id"),
                created_at=item.get("created_at", ""),
                updated_at=item.get("updated_at"),
            )
            for item in commands
        ]

        latest = sorted(entries, key=lambda e: e.created_at, reverse=True)[:10]
        return CommandCenterSummary(
            total_commands=len(entries),
            pending=sum(1 for e in entries if e.status == "pending"),
            running=sum(1 for e in entries if e.status == "running"),
            failed=sum(1 for e in entries if e.status == "failed"),
            latest=latest,
        )

    def get_state(self) -> CommandCenterState:
        """Return compact command-center state for control UIs."""
        summary = self.summarize()
        active_states = {
            LifecycleState.BUILDING,
            LifecycleState.LAUNCHED,
            LifecycleState.MONITORING,
            LifecycleState.SCALED,
        }
        projects_active = sum(
            1 for project in self._portfolio.list_projects() if project.status in active_states
        )
        factory_runs = self._factory_run_store.list_runs()
        factory_runs_running = sum(1 for run in factory_runs if run.status.value == "running")
        factory_runs_failed = sum(1 for run in factory_runs if run.status.value == "failed")
        return CommandCenterState(
            approvals_pending=len(self._governance.list_pending_approvals()),
            projects_active=projects_active,
            commands_pending=summary.pending,
            commands_running=summary.running,
            commands_failed=summary.failed,
            factory_runs_running=factory_runs_running,
            factory_runs_failed=factory_runs_failed,
        )

    def update_status(self, request: CommandStatusUpdateRequest) -> CommandCenterEntry | None:
        """Update command status via registry and return typed entry."""
        updated = self._registry.update_command_status(
            record_id=request.command_id,
            status=request.status,
            message=request.message,
        )
        if updated is None:
            return None
        return CommandCenterEntry(
            command_id=updated["record_id"],
            command_type=updated["command_type"],
            status=updated["status"],
            project_id=updated.get("project_id"),
            created_at=updated["created_at"],
            updated_at=updated.get("updated_at"),
        )
