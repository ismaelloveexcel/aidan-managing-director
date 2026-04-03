"""
Lifecycle state machine for controlled project transitions.
"""

from __future__ import annotations

from app.portfolio.models import LifecycleState


class InvalidStateTransitionError(ValueError):
    """Raised when an invalid lifecycle transition is attempted."""


_ALLOWED_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.IDEA: {LifecycleState.REVIEW},
    LifecycleState.REVIEW: {LifecycleState.APPROVED},
    LifecycleState.APPROVED: {LifecycleState.QUEUED},
    LifecycleState.QUEUED: {LifecycleState.BUILDING},
    LifecycleState.BUILDING: {LifecycleState.LAUNCHED},
    LifecycleState.LAUNCHED: {LifecycleState.MONITORING},
    LifecycleState.MONITORING: {LifecycleState.SCALED, LifecycleState.KILLED},
    LifecycleState.SCALED: set(),
    LifecycleState.KILLED: set(),
}


def _as_state(value: LifecycleState | str) -> LifecycleState:
    """Coerce input into a LifecycleState."""
    if isinstance(value, LifecycleState):
        return value
    return LifecycleState(value)


def can_transition(current: LifecycleState | str, new: LifecycleState | str) -> bool:
    """Return True when transition from current to new is valid."""
    current_state = _as_state(current)
    new_state = _as_state(new)
    return new_state in _ALLOWED_TRANSITIONS[current_state]


def assert_transition_allowed(
    current: LifecycleState | str,
    new: LifecycleState | str,
) -> None:
    """Validate a transition or raise InvalidStateTransitionError."""
    current_state = _as_state(current)
    new_state = _as_state(new)
    if not can_transition(current_state, new_state):
        raise InvalidStateTransitionError(
            f"Invalid lifecycle transition: {current_state.value} -> {new_state.value}",
        )
