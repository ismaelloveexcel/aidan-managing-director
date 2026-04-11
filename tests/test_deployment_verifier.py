"""Tests for the deployment verifier."""

from __future__ import annotations

import pytest

from app.factory.deployment_verifier import (
    VerificationStatus,
    async_verify_deployment,
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


class TestAsyncVerifyDeployment:
    """Tests for the async_verify_deployment function."""

    @pytest.mark.asyncio
    async def test_returns_failed_for_missing_url(self) -> None:
        """No HTTP request should be attempted when URL is absent."""
        result = await async_verify_deployment(
            project_id="proj-async-1",
            deploy_url="",
        )
        assert result.status == VerificationStatus.FAILED
        assert result.project_id == "proj-async-1"
        assert any("No deployment URL" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_returns_failed_for_invalid_url(self) -> None:
        result = await async_verify_deployment(
            project_id="proj-async-2",
            deploy_url="not-a-real-url",
        )
        assert result.status == VerificationStatus.FAILED

    @pytest.mark.asyncio
    async def test_returns_failed_for_dry_run_url(self) -> None:
        result = await async_verify_deployment(
            project_id="proj-async-3",
            deploy_url="dry-run://vercel/proj-async-3",
        )
        assert result.status == VerificationStatus.FAILED

    @pytest.mark.asyncio
    async def test_http_checks_added_to_checks_performed(self) -> None:
        """Verify that HTTP check entries appear in checks_performed."""
        import httpx
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.is_redirect = False

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.factory.deployment_verifier.httpx.AsyncClient", return_value=mock_client):
            result = await async_verify_deployment(
                project_id="proj-async-4",
                deploy_url="https://example.vercel.app",
            )

        assert "http_root_reachable" in result.checks_performed
        assert result.response_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_unhealthy_when_server_returns_500(self) -> None:
        import httpx
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.is_redirect = False
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.factory.deployment_verifier.httpx.AsyncClient", return_value=mock_client):
            result = await async_verify_deployment(
                project_id="proj-async-5",
                deploy_url="https://broken.vercel.app",
            )

        assert result.status in (VerificationStatus.FAILED, VerificationStatus.DEGRADED)
        assert result.health_check_passed is False

    @pytest.mark.asyncio
    async def test_project_id_propagated(self) -> None:
        result = await async_verify_deployment(
            project_id="proj-check-id",
            deploy_url="",
        )
        assert result.project_id == "proj-check-id"
