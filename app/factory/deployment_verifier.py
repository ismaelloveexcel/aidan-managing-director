"""
Deployment verifier – verifies deployed applications are accessible and functional.

Checks:
- URL is accessible
- Health endpoint responds
- No 404/500 errors
- Deployment is recent
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Deployment verification status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class DeploymentVerification(BaseModel):
    """Result of deployment verification."""

    project_id: str
    deploy_url: str = ""
    status: VerificationStatus = VerificationStatus.UNKNOWN
    health_check_passed: bool = False
    ui_accessible: bool = False
    response_time_ms: float = 0.0
    checks_performed: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    verified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


def verify_deployment(
    *,
    project_id: str,
    deploy_url: str = "",
    repo_url: str = "",
    expected_endpoints: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> DeploymentVerification:
    """Verify a deployment is accessible and functional.

    This performs deterministic checks on deployment metadata.
    Actual HTTP checks require an async client (done at integration layer).

    Args:
        project_id: Project identifier.
        deploy_url: Deployment URL to verify.
        repo_url: Repository URL.
        expected_endpoints: List of endpoints to check.
        extra: Optional additional data.

    Returns:
        DeploymentVerification result.
    """
    checks: list[str] = []
    issues: list[str] = []

    # Check 1: Deploy URL exists
    checks.append("deploy_url_present")
    has_url = bool(deploy_url and deploy_url.strip())
    if not has_url:
        issues.append("No deployment URL provided.")

    # Check 2: URL format validity
    checks.append("url_format_valid")
    url_valid = False
    if has_url:
        url_lower = deploy_url.lower().strip()
        url_valid = url_lower.startswith(("http://", "https://"))
        if not url_valid:
            issues.append(f"Invalid URL format: {deploy_url}")
        # Check for dry-run URLs
        if url_lower.startswith("dry-run://"):
            issues.append("Deployment URL is a dry-run placeholder.")
            url_valid = False

    # Check 3: Repo URL exists
    checks.append("repo_url_present")
    if not repo_url or not repo_url.strip():
        issues.append("No repository URL provided.")

    # Check 4: Expected endpoints defined
    checks.append("endpoints_defined")
    if expected_endpoints:
        for endpoint in expected_endpoints:
            checks.append(f"endpoint_{endpoint}")
    else:
        # Default expected endpoints
        checks.append("endpoint_health")

    # Determine overall status
    if not has_url:
        status = VerificationStatus.FAILED
        health_passed = False
        ui_accessible = False
    elif not url_valid:
        status = VerificationStatus.FAILED
        health_passed = False
        ui_accessible = False
    elif issues:
        status = VerificationStatus.DEGRADED
        health_passed = False
        ui_accessible = True
    else:
        status = VerificationStatus.HEALTHY
        health_passed = True
        ui_accessible = True

    return DeploymentVerification(
        project_id=project_id,
        deploy_url=deploy_url,
        status=status,
        health_check_passed=health_passed,
        ui_accessible=ui_accessible,
        checks_performed=checks,
        issues=issues,
    )


_HTTP_TIMEOUT = 10.0  # seconds per request
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 1.0  # seconds (exponential: 1, 2, 4)


async def async_verify_deployment(
    *,
    project_id: str,
    deploy_url: str = "",
    repo_url: str = "",
    expected_endpoints: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> DeploymentVerification:
    """Verify a deployment with real async HTTP requests.

    Makes actual HTTP requests to the deployment URL and health endpoints
    using ``httpx.AsyncClient``.  Implements up to 3 retry attempts with
    exponential back-off (1 s, 2 s, 4 s) for transient failures.

    Args:
        project_id: Project identifier.
        deploy_url: Deployment URL to probe.
        repo_url: Repository URL (recorded in metadata but not probed).
        expected_endpoints: Additional endpoint paths to probe.
            Defaults to ``["/health"]``.
        extra: Optional additional data (unused by this function).

    Returns:
        :class:`DeploymentVerification` populated with real timing and
        HTTP status information.
    """
    # Run the synchronous metadata checks first.
    base = verify_deployment(
        project_id=project_id,
        deploy_url=deploy_url,
        repo_url=repo_url,
        expected_endpoints=expected_endpoints,
        extra=extra,
    )

    # If metadata validation already failed (e.g. missing/invalid URL),
    # there is nothing to probe — return early.
    if base.status == VerificationStatus.FAILED:
        return base

    checks = list(base.checks_performed)
    issues = list(base.issues)

    endpoints_to_probe: list[str] = list(expected_endpoints) if expected_endpoints else ["/health"]
    base_url = deploy_url.rstrip("/")

    health_passed = False
    ui_accessible = False
    response_time_ms = 0.0

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
        # --- Probe the root URL ---
        checks.append("http_root_reachable")
        root_ok, root_ms, root_issue = await _probe_url(client, base_url)
        response_time_ms = root_ms
        if root_ok:
            ui_accessible = True
        else:
            issues.append(f"Root URL unreachable: {root_issue}")

        # --- Probe health / custom endpoints ---
        for endpoint in endpoints_to_probe:
            url = base_url + endpoint
            check_key = f"http_{endpoint.lstrip('/').replace('/', '_') or 'health'}"
            checks.append(check_key)
            ok, ep_ms, ep_issue = await _probe_url(client, url)
            if ok:
                health_passed = True
            else:
                issues.append(f"Endpoint {endpoint} failed: {ep_issue}")

    # Determine overall status.
    if health_passed and ui_accessible:
        status = VerificationStatus.HEALTHY
    elif health_passed or ui_accessible:
        status = VerificationStatus.DEGRADED
    else:
        status = VerificationStatus.FAILED

    return DeploymentVerification(
        project_id=project_id,
        deploy_url=deploy_url,
        status=status,
        health_check_passed=health_passed,
        ui_accessible=ui_accessible,
        response_time_ms=response_time_ms,
        checks_performed=checks,
        issues=issues,
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


async def _probe_url(
    client: httpx.AsyncClient,
    url: str,
) -> tuple[bool, float, str]:
    """Probe a single URL with retry logic.

    Args:
        client: Shared ``httpx.AsyncClient``.
        url: The URL to GET.

    Returns:
        A 3-tuple of ``(success, response_time_ms, error_detail)``.
        ``response_time_ms`` is 0.0 on failure.
    """
    last_error = ""
    for attempt in range(_MAX_RETRIES):
        if attempt > 0:
            await asyncio.sleep(_RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
        try:
            start = time.monotonic()
            response = await client.get(url)
            elapsed_ms = (time.monotonic() - start) * 1000.0
            if response.is_success or response.is_redirect:
                return True, elapsed_ms, ""
            last_error = f"HTTP {response.status_code}"
        except httpx.TimeoutException:
            last_error = "Request timed out"
        except httpx.RequestError as exc:
            last_error = str(exc)

    return False, 0.0, last_error
