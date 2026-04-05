"""Tests for the deployment verifier."""

from __future__ import annotations

import pytest

from app.factory.deployment_verifier import (
    DeploymentVerification,
    VerificationStatus,
    verify_deployment,
)


class TestDeploymentVerifier:
    """Tests for verify_deployment function."""

    def test_healthy_deployment(self) -> None:
        result = verify_deployment(
            project_id="proj-1",
            deploy_url="https://my-app.vercel.app",
            repo_url="https://github.com/org/repo",
        )
        assert result.status == VerificationStatus.HEALTHY
        assert result.health_check_passed is True
        assert result.ui_accessible is True

    def test_no_deploy_url_fails(self) -> None:
        result = verify_deployment(
            project_id="proj-1",
            deploy_url="",
            repo_url="https://github.com/org/repo",
        )
        assert result.status == VerificationStatus.FAILED
        assert any("No deployment URL" in i for i in result.issues)

    def test_invalid_url_format_fails(self) -> None:
        result = verify_deployment(
            project_id="proj-1",
            deploy_url="not-a-url",
        )
        assert result.status == VerificationStatus.FAILED
        assert any("Invalid URL" in i for i in result.issues)

    def test_dry_run_url_fails(self) -> None:
        result = verify_deployment(
            project_id="proj-1",
            deploy_url="dry-run://vercel/proj-1",
        )
        assert result.status == VerificationStatus.FAILED
        assert any("dry-run" in i.lower() for i in result.issues)

    def test_missing_repo_url_noted(self) -> None:
        result = verify_deployment(
            project_id="proj-1",
            deploy_url="https://my-app.vercel.app",
            repo_url="",
        )
        assert any("No repository URL" in i for i in result.issues)

    def test_checks_performed_populated(self) -> None:
        result = verify_deployment(
            project_id="proj-1",
            deploy_url="https://my-app.vercel.app",
        )
        assert "deploy_url_present" in result.checks_performed
        assert "url_format_valid" in result.checks_performed

    def test_expected_endpoints_checked(self) -> None:
        result = verify_deployment(
            project_id="proj-1",
            deploy_url="https://my-app.vercel.app",
            expected_endpoints=["/health", "/api/status"],
        )
        assert "endpoint_/health" in result.checks_performed
        assert "endpoint_/api/status" in result.checks_performed

    def test_project_id_in_result(self) -> None:
        result = verify_deployment(project_id="my-project")
        assert result.project_id == "my-project"

    def test_verified_at_populated(self) -> None:
        result = verify_deployment(project_id="proj-1")
        assert result.verified_at
