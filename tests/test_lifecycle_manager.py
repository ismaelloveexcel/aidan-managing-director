"""Tests for the lifecycle manager."""

from __future__ import annotations

import pytest

from app.planning.lifecycle_manager import (
    ControlLimits,
    LifecycleManager,
    ProjectState,
    StateTransitionError,
)


class TestLifecycleManager:
    """Tests for LifecycleManager."""

    def test_register_project(self) -> None:
        mgr = LifecycleManager()
        record = mgr.register_project("proj-1", score=8.5)
        assert record.project_id == "proj-1"
        assert record.state == ProjectState.IDEA
        assert record.score == 8.5
        assert len(record.history) == 1

    def test_register_duplicate_returns_existing(self) -> None:
        mgr = LifecycleManager()
        r1 = mgr.register_project("proj-1")
        r2 = mgr.register_project("proj-1")
        assert r1.project_id == r2.project_id
        assert r1.created_at == r2.created_at

    def test_valid_transition(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        record = mgr.transition("proj-1", ProjectState.VALIDATED)
        assert record.state == ProjectState.VALIDATED
        assert len(record.history) == 2

    def test_invalid_transition_raises(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        with pytest.raises(StateTransitionError):
            mgr.transition("proj-1", ProjectState.BUILDING)

    def test_kill_from_any_state(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        record = mgr.transition("proj-1", ProjectState.KILLED)
        assert record.state == ProjectState.KILLED

    def test_killed_is_terminal(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        mgr.transition("proj-1", ProjectState.KILLED)
        with pytest.raises(StateTransitionError):
            mgr.transition("proj-1", ProjectState.IDEA)

    def test_full_lifecycle(self) -> None:
        mgr = LifecycleManager(limits=ControlLimits(max_active_projects=10))
        mgr.register_project("proj-1")
        mgr.transition("proj-1", ProjectState.VALIDATED)
        mgr.transition("proj-1", ProjectState.SCORED)
        mgr.transition("proj-1", ProjectState.APPROVED)
        mgr.transition("proj-1", ProjectState.QUEUED)
        mgr.transition("proj-1", ProjectState.BUILDING)
        mgr.transition("proj-1", ProjectState.DEPLOYED)
        mgr.transition("proj-1", ProjectState.VERIFIED)
        mgr.transition("proj-1", ProjectState.MONITORED)
        record = mgr.transition("proj-1", ProjectState.SCALED)
        assert record.state == ProjectState.SCALED
        assert len(record.history) == 10

    def test_max_parallel_builds_enforced(self) -> None:
        mgr = LifecycleManager(limits=ControlLimits(
            max_active_projects=10,
            max_parallel_builds=1,
        ))
        mgr.register_project("proj-1")
        mgr.transition("proj-1", ProjectState.VALIDATED)
        mgr.transition("proj-1", ProjectState.SCORED)
        mgr.transition("proj-1", ProjectState.APPROVED)
        mgr.transition("proj-1", ProjectState.QUEUED)
        mgr.transition("proj-1", ProjectState.BUILDING)

        mgr.register_project("proj-2")
        mgr.transition("proj-2", ProjectState.VALIDATED)
        mgr.transition("proj-2", ProjectState.SCORED)
        mgr.transition("proj-2", ProjectState.APPROVED)
        mgr.transition("proj-2", ProjectState.QUEUED)

        with pytest.raises(StateTransitionError, match="parallel builds"):
            mgr.transition("proj-2", ProjectState.BUILDING)

    def test_get_project(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        assert mgr.get_project("proj-1") is not None
        assert mgr.get_project("nonexistent") is None

    def test_list_projects_by_state(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        mgr.register_project("proj-2")
        mgr.transition("proj-2", ProjectState.VALIDATED)
        ideas = mgr.list_projects(state=ProjectState.IDEA)
        assert len(ideas) == 1
        assert ideas[0].project_id == "proj-1"

    def test_get_active_count(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        assert mgr.get_active_count() == 0  # IDEA is not active
        mgr.transition("proj-1", ProjectState.VALIDATED)
        assert mgr.get_active_count() == 1

    def test_queue_priority_sorted_by_score(self) -> None:
        mgr = LifecycleManager(limits=ControlLimits(max_active_projects=10))
        for name, score in [("a", 5.0), ("b", 9.0), ("c", 7.0)]:
            mgr.register_project(name, score=score)
            mgr.transition(name, ProjectState.VALIDATED)
            mgr.transition(name, ProjectState.SCORED)
            mgr.transition(name, ProjectState.APPROVED)
            mgr.transition(name, ProjectState.QUEUED)
        queued = mgr.get_queue_priority()
        assert [p.project_id for p in queued] == ["b", "c", "a"]

    def test_can_transition(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        assert mgr.can_transition("proj-1", ProjectState.VALIDATED) is True
        assert mgr.can_transition("proj-1", ProjectState.BUILDING) is False
        assert mgr.can_transition("nonexistent", ProjectState.VALIDATED) is False

    def test_transition_unknown_project_raises(self) -> None:
        mgr = LifecycleManager()
        with pytest.raises(KeyError, match="not found"):
            mgr.transition("unknown", ProjectState.VALIDATED)

    def test_string_state_accepted(self) -> None:
        mgr = LifecycleManager()
        mgr.register_project("proj-1")
        record = mgr.transition("proj-1", "validated")
        assert record.state == ProjectState.VALIDATED
