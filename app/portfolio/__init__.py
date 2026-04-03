"""
Portfolio persistence and state-management package.
"""

from app.portfolio.models import (
    LifecycleState,
    MetricsSnapshotRecord,
    PortfolioEventRecord,
    PortfolioProjectRecord,
)
from app.portfolio.repository import PortfolioRepository
from app.portfolio.state_machine import (
    InvalidStateTransitionError,
    assert_transition_allowed,
    can_transition,
)

__all__ = [
    "InvalidStateTransitionError",
    "LifecycleState",
    "MetricsSnapshotRecord",
    "PortfolioEventRecord",
    "PortfolioProjectRecord",
    "PortfolioRepository",
    "assert_transition_allowed",
    "can_transition",
]
