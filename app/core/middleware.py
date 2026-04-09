"""middleware.py – API key authentication and rate-limiting middleware.

Provides two ASGI middlewares:
- APIKeyMiddleware: validates the ``X-API-Key`` header
  against the ``API_KEY`` environment setting.
  Returns HTTP 401 when the key is absent or wrong.
  Public read-only paths (``GET /``, ``GET /health``, ``GET /docs``,
  ``GET /openapi.json``) are always allowed through without a key.
- RateLimitMiddleware: Upstash Redis-based sliding-window limiter
  (default 100 requests per minute). Falls back to allow-all if
  Upstash is not configured. Returns HTTP 429 when the limit is
  exceeded.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Paths that are unconditionally public regardless of API key / rate limits.
_PUBLIC_PATHS: frozenset[str] = frozenset({
    "/", "/health", "/docs", "/openapi.json", "/redoc",
    "/api/dashboard/health", "/api/dashboard/tokens",
})


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests that do not carry a valid API key.

    Skips authentication when:
    - The configured ``api_key`` is empty (dev / no-auth mode).
    - The request path is one of the public paths (``_PUBLIC_PATHS``).
    - The request method is ``GET`` and the path starts with ``/docs``
      or ``/openapi.json`` (Swagger UI assets).

    The key must be supplied via the ``X-API-Key`` header.
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

        # Extract candidate key from header only (no query param — prevents
        # credential leakage via logs, Referer headers, and browser history).
        provided = request.headers.get("X-API-Key") or ""

        if not provided or provided != self._api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Upstash Redis-based sliding-window rate limiter (per client IP).

    Uses Upstash Redis for state so it works correctly on serverless
    platforms like Vercel where in-memory state is lost between cold starts.

    If UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN are not set,
    the middleware passes all requests through (graceful degradation).

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
        self._limiter = None

        redis_url = os.environ.get("UPSTASH_REDIS_REST_URL", "")
        redis_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

        if redis_url and redis_token:
            try:
                from upstash_ratelimit import Ratelimit, SlidingWindow
                from upstash_redis import Redis

                redis = Redis(url=redis_url, token=redis_token)
                self._limiter = Ratelimit(
                    redis=redis,
                    limiter=SlidingWindow(
                        max_requests=max_requests,
                        window=window_seconds,
                    ),
                    prefix="ratelimit:md",
                )
            except ImportError:
                pass  # upstash packages not installed — degrade gracefully

    def _get_client_ip(self, request: Request) -> str:
        """Extract the real client IP, respecting common proxy headers."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # No limiter configured → pass through.
        if self._limiter is None:
            return await call_next(request)

        ip = self._get_client_ip(request)

        try:
            result = self._limiter.limit(ip)
        except Exception:
            # If Upstash is unreachable, allow the request through.
            return await call_next(request)

        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
            )

        return await call_next(request)
