"""Tests for scripts/factory_callback.py and scripts/factory_alert.py."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest


class TestFactoryCallback:
    """Tests for the factory_callback.py CLI script."""

    def _run_callback(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run factory_callback.py with the given args."""
        return subprocess.run(
            [sys.executable, "scripts/factory_callback.py", *args],
            capture_output=True,
            text=True,
        )

    def test_callback_no_url_skips(self) -> None:
        """When no callback_url is given, the script skips and exits 0."""
        result = self._run_callback(
            "--project-id", "test-project",
            "--correlation-id", "test-project:abc123",
            "--callback-url", "",
            "--status", "succeeded",
            "--run-id", "12345",
        )
        assert result.returncode == 0
        assert "skipping POST" in result.stdout.lower() or "no callback_url" in result.stdout.lower()

    def test_callback_builds_payload(self) -> None:
        """The script builds a correct JSON payload even when URL is missing."""
        result = self._run_callback(
            "--project-id", "my-project",
            "--correlation-id", "my-project:deadbeef",
            "--callback-url", "",
            "--status", "failed",
            "--run-id", "99",
            "--workflow-url", "https://github.com/org/repo/actions/runs/99",
            "--error-summary", "Build exploded",
        )
        assert result.returncode == 0
        # Should contain the payload in stdout
        assert "my-project" in result.stdout
        assert "my-project:deadbeef" in result.stdout
        assert "failed" in result.stdout

    def test_callback_missing_correlation_id_warns(self) -> None:
        """When correlation_id is empty, the script warns but doesn't fail."""
        result = self._run_callback(
            "--project-id", "test-project",
            "--correlation-id", "",
            "--callback-url", "",
            "--status", "succeeded",
            "--run-id", "12345",
        )
        assert result.returncode == 0

    def test_callback_payload_structure(self) -> None:
        """Verify the callback payload matches FactoryCallbackPayload schema."""
        result = self._run_callback(
            "--project-id", "proj-x",
            "--correlation-id", "proj-x:cafe1234",
            "--callback-url", "",
            "--status", "succeeded",
            "--run-id", "42",
            "--deploy-url", "https://proj-x.vercel.app",
            "--repo-url", "https://github.com/org/proj-x",
        )
        assert result.returncode == 0
        # Extract JSON payload from output
        for line in result.stdout.splitlines():
            if "Payload:" in line:
                payload_str = line.split("Payload:", 1)[1].strip()
                payload = json.loads(payload_str)
                assert payload["project_id"] == "proj-x"
                assert payload["correlation_id"] == "proj-x:cafe1234"
                assert payload["status"] == "succeeded"
                assert payload["deploy_url"] == "https://proj-x.vercel.app"
                assert payload["repo_url"] == "https://github.com/org/proj-x"
                assert payload["run_id"] == "42"
                break
        else:
            pytest.fail("Payload line not found in output")

    def test_callback_error_field_included_on_failure(self) -> None:
        """Error field is included in payload when error-summary is provided."""
        result = self._run_callback(
            "--project-id", "proj-err",
            "--correlation-id", "proj-err:dead",
            "--callback-url", "",
            "--status", "failed",
            "--run-id", "55",
            "--error-summary", "Deployment health check failed",
        )
        assert result.returncode == 0
        for line in result.stdout.splitlines():
            if "Payload:" in line:
                payload_str = line.split("Payload:", 1)[1].strip()
                payload = json.loads(payload_str)
                assert payload["error"] == "Deployment health check failed"
                break

    def test_callback_no_error_field_on_success(self) -> None:
        """Error field is absent from payload when no error is given."""
        result = self._run_callback(
            "--project-id", "proj-ok",
            "--correlation-id", "proj-ok:1234",
            "--callback-url", "",
            "--status", "succeeded",
            "--run-id", "10",
        )
        assert result.returncode == 0
        for line in result.stdout.splitlines():
            if "Payload:" in line:
                payload_str = line.split("Payload:", 1)[1].strip()
                payload = json.loads(payload_str)
                assert "error" not in payload
                break


class TestFactoryAlert:
    """Tests for the factory_alert.py CLI script."""

    def _run_alert(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run factory_alert.py with the given args."""
        return subprocess.run(
            [sys.executable, "scripts/factory_alert.py", *args],
            capture_output=True,
            text=True,
        )

    def test_alert_no_webhook_skips(self) -> None:
        """When no ALERT_WEBHOOK_URL, the script skips and exits 0."""
        result = self._run_alert(
            "--project-id", "test-project",
            "--correlation-id", "test-project:abc",
            "--run-id", "12345",
            "--workflow-url", "https://github.com/org/repo/actions/runs/12345",
        )
        assert result.returncode == 0
        assert "skipping" in result.stdout.lower() or "no alert_webhook_url" in result.stdout.lower()

    def test_alert_builds_payload(self) -> None:
        """The alert script builds a correct failure payload."""
        result = self._run_alert(
            "--project-id", "my-project",
            "--correlation-id", "my-project:beef",
            "--run-id", "99",
            "--workflow-url", "https://github.com/org/repo/actions/runs/99",
            "--failure-reason", "deploy health unhealthy",
            "--error-summary", "404 on health check",
        )
        assert result.returncode == 0
        assert "my-project" in result.stdout
        assert "factory_failure" in result.stdout

    def test_alert_payload_structure(self) -> None:
        """Verify alert payload has required fields."""
        result = self._run_alert(
            "--project-id", "proj-fail",
            "--correlation-id", "proj-fail:0000",
            "--run-id", "77",
            "--workflow-url", "https://github.com/org/repo/actions/runs/77",
            "--failure-reason", "pipeline crashed",
        )
        assert result.returncode == 0
        for line in result.stdout.splitlines():
            if "Alert payload:" in line:
                payload_str = line.split("Alert payload:", 1)[1].strip()
                payload = json.loads(payload_str)
                assert payload["project_id"] == "proj-fail"
                assert payload["correlation_id"] == "proj-fail:0000"
                assert payload["alert_type"] == "factory_failure"
                assert payload["status"] == "failed"
                assert payload["failure_reason"] == "pipeline crashed"
                break
        else:
            pytest.fail("Alert payload line not found in output")

    def test_alert_with_explicit_webhook_url_arg(self) -> None:
        """When alert-webhook-url is empty string, it skips gracefully."""
        result = self._run_alert(
            "--project-id", "proj-a",
            "--run-id", "1",
            "--workflow-url", "https://example.com",
            "--alert-webhook-url", "",
        )
        assert result.returncode == 0
        assert "skipping" in result.stdout.lower() or "no alert_webhook_url" in result.stdout.lower()
