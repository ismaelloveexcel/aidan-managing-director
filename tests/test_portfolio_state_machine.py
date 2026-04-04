"""Tests for strict portfolio lifecycle transitions."""

import pytest

from app.portfolio.models import LifecycleState
from app.portfolio.state_machine import (
    InvalidStateTransitionError,
    assert_transition_allowed,
    can_transition,
)


def test_all_required_forward_transitions_are_allowed() -> None:
    assert can_transition(LifecycleState.IDEA, LifecycleState.REVIEW)
    assert can_transition(LifecycleState.REVIEW, LifecycleState.APPROVED)
    assert can_transition(LifecycleState.APPROVED, LifecycleState.QUEUED)
    assert can_transition(LifecycleState.QUEUED, LifecycleState.BUILDING)
    assert can_transition(LifecycleState.BUILDING, LifecycleState.LAUNCHED)
    assert can_transition(LifecycleState.LAUNCHED, LifecycleState.MONITORING)
    assert can_transition(LifecycleState.MONITORING, LifecycleState.SCALED)
    assert can_transition(LifecycleState.MONITORING, LifecycleState.KILLED)


def test_invalid_transition_is_rejected() -> None:
    assert not can_transition(LifecycleState.IDEA, LifecycleState.BUILDING)
    with pytest.raises(InvalidStateTransitionError):
        assert_transition_allowed(LifecycleState.IDEA, LifecycleState.BUILDING)


def test_terminal_states_cannot_transition() -> None:
    assert not can_transition(LifecycleState.SCALED, LifecycleState.MONITORING)
    assert not can_transition(LifecycleState.KILLED, LifecycleState.MONITORING)
