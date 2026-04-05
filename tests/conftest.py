"""
conftest.py – Shared pytest fixtures for the test suite.

Resets per-request middleware state (rate limiter) before each test so
that in-memory counters don't bleed across unrelated test modules.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Reset the in-memory rate-limiter window before every test.

    The FastAPI application is a module-level singleton shared across all
    tests in a session.  Without this fixture the sliding-window counters
    accumulate across test modules and the 100-req/min limit is reached
    mid-session, causing unrelated tests to receive HTTP 429 responses.
    """
    from app.core.middleware import RateLimitMiddleware
    from main import app

    for middleware in app.user_middleware:
        if middleware.cls is RateLimitMiddleware:
            # Build a temporary instance just to call reset on the *live*
            # middleware that's already wrapped into the ASGI stack.
            break

    # Walk the built middleware stack looking for the live instance.
    stack = getattr(app, "middleware_stack", None)
    node = stack
    while node is not None:
        if isinstance(node, RateLimitMiddleware):
            node.reset()
            break
        node = getattr(node, "app", None)
