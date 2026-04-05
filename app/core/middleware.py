"""
middleware.py – API key authentication and rate-limiting middleware.

Provides two ASGI middlewares:
- APIKeyMiddleware: validates the ``X-API-Key`` header (or ``api_key``
  query parameter) against the ``API_KEY`` environment setting.
  Returns HTTP 401 when the key is absent or wrong.
  Public read-only paths (``GET /``, ``GET /health``, ``GET /docs``,
  ``GET /openapi.json``) are always allowed through without a key.
- RateLimitMiddleware: simple in-memory per-IP sliding-window limiter
  (default 100 requests per minute). Returns HTTP 429 when the limit is
  exceeded.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Paths that are unconditionally public regardless of API key / rate limits.
_PUBLIC_PATHS: frozenset[str] = frozenset({"/", "/health", "/docs", "/openapi.json", "/redoc"})


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests that do not carry a valid API key.

    Skips authentication when:
    - The configured ``api_key`` is empty (dev / no-auth mode).
    - The request path is one of the public paths (``_PUBLIC_PATHS``).
    - The request method is ``GET`` and the path starts with ``/docs``
      or ``/openapi.json`` (Swagger UI assets).

    The key may be supplied via the ``X-API-Key`` header **or** the
    ``api_key`` query parameter.
    """

    def __init__(self, app: object, *, api_key: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._api_key = api_key

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # No key configured → authentication is disabled.
        if not self._api_key:
            return await call_next(request)

        path = request.url.path

        # Always allow public GET endpoints.
        if request.method == "GET" and (
            path in _PUBLIC_PATHS
            or path.startswith("/docs")
            or path.startswith("/redoc")
        ):
            return await call_next(request)

        # Extract candidate key from header or query string.
        provided = request.headers.get("X-API-Key") or request.query_params.get("api_key", "")

        if not provided or provided != self._api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window in-memory rate limiter (per client IP).

    Args:
        max_requests: Maximum number of requests allowed per window.
        window_seconds: Duration of the sliding window in seconds.
    """

    def __init__(
        self,
        app: object,
        *,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        # Maps IP address → deque of request timestamps (float).
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def _get_client_ip(self, request: Request) -> str:
        """Extract the real client IP, respecting common proxy headers."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def reset(self) -> None:
        """Clear all tracked IP windows.

        This method is intended for use in tests to reset per-IP sliding-window
        state between test sessions without restarting the application.
        """
        self._windows.clear()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        ip = self._get_client_ip(request)
        now = time.monotonic()
        window = self._windows[ip]

        # Drop timestamps outside the current window.
        cutoff = now - self._window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= self._max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
            )

        window.append(now)
        return await call_next(request)
