"""
Lifecycle manager – enforces the full project lifecycle state machine.

States: idea → validated → scored → approved → queued → building →
        deployed → verified → monitored → scaled/killed

Includes control layer enforcement:
- max_active_projects
- max_parallel_builds
- max_daily_builds
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProjectState(str, Enum):
    """Full lifecycle states."""

    IDEA = "idea"
    VALIDATED = "validated"
    SCORED = "scored"
    APPROVED = "approved"
    QUEUED = "queued"
    BUILDING = "building"
    DEPLOYED = "deployed"
    VERIFIED = "verified"
    MONITORED = "monitored"
    SCALED = "scaled"
    KILLED = "killed"


class StateTransitionError(ValueError):
    """Raised for invalid state transitions."""


# Valid transitions
_TRANSITIONS: dict[ProjectState, set[ProjectState]] = {
    ProjectState.IDEA: {ProjectState.VALIDATED, ProjectState.KILLED},
    ProjectState.VALIDATED: {ProjectState.SCORED, ProjectState.KILLED},
    ProjectState.SCORED: {ProjectState.APPROVED, ProjectState.KILLED},
    ProjectState.APPROVED: {ProjectState.QUEUED, ProjectState.KILLED},
    ProjectState.QUEUED: {ProjectState.BUILDING, ProjectState.KILLED},
    ProjectState.BUILDING: {ProjectState.DEPLOYED, ProjectState.KILLED},
    ProjectState.DEPLOYED: {ProjectState.VERIFIED, ProjectState.KILLED},
    ProjectState.VERIFIED: {ProjectState.MONITORED, ProjectState.KILLED},
    ProjectState.MONITORED: {ProjectState.SCALED, ProjectState.KILLED},
    ProjectState.SCALED: {ProjectState.KILLED},
    ProjectState.KILLED: set(),
}


class ProjectRecord(BaseModel):
    """In-memory project lifecycle record."""

    project_id: str
    state: ProjectState = ProjectState.IDEA
    score: float = 0.0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    history: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlLimits(BaseModel):
    """Control layer limits."""

    max_active_projects: int = 5
    max_parallel_builds: int = 2
    max_daily_builds: int = 10


class LifecycleManager:
    """Manages project lifecycle with state machine and control layer."""

    def __init__(self, limits: ControlLimits | None = None) -> None:
        self._projects: dict[str, ProjectRecord] = {}
        self._limits = limits or ControlLimits()
        self._daily_build_count = 0
        self._daily_build_date: str = ""
        self._lock = threading.Lock()

    @property
    def limits(self) -> ControlLimits:
        """Return current control limits."""
        return self._limits

    def register_project(
        self,
        project_id: str,
        *,
        score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectRecord:
        """Register a new project in IDEA state."""
        with self._lock:
            if project_id in self._projects:
                return self._projects[project_id]

            record = ProjectRecord(
                project_id=project_id,
                score=score,
                metadata=metadata or {},
            )
            record.history.append({
                "from": "",
                "to": ProjectState.IDEA.value,
                "timestamp": record.created_at,
            })
            self._projects[project_id] = record
            return record

    def get_project(self, project_id: str) -> ProjectRecord | None:
        """Get project record by ID."""
        with self._lock:
            return self._projects.get(project_id)

    def list_projects(
        self,
        *,
        state: ProjectState | None = None,
    ) -> list[ProjectRecord]:
        """List projects, optionally filtered by state."""
        with self._lock:
            projects = list(self._projects.values())
            if state is not None:
                projects = [p for p in projects if p.state == state]
            return projects

    def transition(
        self,
        project_id: str,
        new_state: ProjectState | str,
    ) -> ProjectRecord:
        """Transition a project to a new state.

        Raises:
            StateTransitionError: If transition is invalid.
            KeyError: If project not found.
        """
        if isinstance(new_state, str):
            new_state = ProjectState(new_state)

        with self._lock:
            record = self._projects.get(project_id)
            if record is None:
                raise KeyError(f"Project not found: {project_id}")

            current = record.state
            if new_state not in _TRANSITIONS.get(current, set()):
                raise StateTransitionError(
                    f"Invalid transition: {current.value} → {new_state.value}"
                )

            # Control layer checks
            if new_state == ProjectState.BUILDING:
                self._check_build_limits()

            old_state = record.state
            record.state = new_state
            record.updated_at = datetime.now(timezone.utc).isoformat()
            record.history.append({
                "from": old_state.value,
                "to": new_state.value,
                "timestamp": record.updated_at,
            })

            if new_state == ProjectState.BUILDING:
                self._increment_daily_builds()

            return record

    def _check_build_limits(self) -> None:
        """Check control layer limits before allowing a build."""
        active = [
            p for p in self._projects.values()
            if p.state not in {ProjectState.KILLED, ProjectState.SCALED, ProjectState.IDEA}
        ]
        if len(active) >= self._limits.max_active_projects:
            raise StateTransitionError(
                f"Max active projects ({self._limits.max_active_projects}) reached."
            )

        building = [
            p for p in self._projects.values()
            if p.state == ProjectState.BUILDING
        ]
        if len(building) >= self._limits.max_parallel_builds:
            raise StateTransitionError(
                f"Max parallel builds ({self._limits.max_parallel_builds}) reached."
            )

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_build_date != today:
            self._daily_build_count = 0
            self._daily_build_date = today

        if self._daily_build_count >= self._limits.max_daily_builds:
            raise StateTransitionError(
                f"Max daily builds ({self._limits.max_daily_builds}) reached."
            )

    def _increment_daily_builds(self) -> None:
        """Increment the daily build counter."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_build_date != today:
            self._daily_build_count = 0
            self._daily_build_date = today
        self._daily_build_count += 1

    def get_active_count(self) -> int:
        """Return count of active (non-terminal) projects."""
        with self._lock:
            return sum(
                1 for p in self._projects.values()
                if p.state not in {ProjectState.KILLED, ProjectState.SCALED, ProjectState.IDEA}
            )

    def get_building_count(self) -> int:
        """Return count of currently building projects."""
        with self._lock:
            return sum(
                1 for p in self._projects.values()
                if p.state == ProjectState.BUILDING
            )

    def get_queue_priority(self) -> list[ProjectRecord]:
        """Get queued projects sorted by priority (score desc)."""
        with self._lock:
            queued = [
                p for p in self._projects.values()
                if p.state == ProjectState.QUEUED
            ]
            return sorted(queued, key=lambda p: p.score, reverse=True)

    def can_transition(
        self,
        project_id: str,
        new_state: ProjectState | str,
    ) -> bool:
        """Check if a transition is valid without performing it."""
        if isinstance(new_state, str):
            new_state = ProjectState(new_state)
        with self._lock:
            record = self._projects.get(project_id)
            if record is None:
                return False
            return new_state in _TRANSITIONS.get(record.state, set())
