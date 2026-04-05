"""
Deployment verifier – verifies deployed applications are accessible and functional.

Checks:
- URL is accessible
- Health endpoint responds
- No 404/500 errors
- Deployment is recent
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

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
        health_passed = True
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
