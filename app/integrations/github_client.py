"""
github_client.py – GitHub API integration for the GitHub Factory.

Provides a typed client for interacting with GitHub repositories,
issues, pull requests, and workflow dispatch events.

All methods are currently **stub implementations** that return
realistic placeholder data.  Real HTTP calls (via ``httpx``) will
replace the stubs once API credentials are provisioned.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx


class GitHubClient:
    """
    Wraps the GitHub REST API for use by the command routing layer.

    Every public method returns structured data that mirrors the shape
    of the real GitHub API response so that callers can be developed
    and tested before live credentials are available.

    Use as a context manager or call :meth:`close` explicitly to
    release network resources when done.
    """

    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        """
        Initialise the GitHub client.

        Args:
            token: Personal access token or GitHub App installation token.
            base_url: Base URL for the GitHub API (override for GHES).
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        self._http_client: httpx.Client | None = None

    # -- lifecycle --------------------------------------------------------------

    def _client(self) -> httpx.Client:
        """
        Return the shared ``httpx.Client`` instance.

        The client is created lazily and reused for the lifetime of
        this ``GitHubClient``.  Call :meth:`close` when the client is
        no longer needed to release network resources.
        """
        if self._http_client is None:
            self._http_client = httpx.Client(
                base_url=self.base_url,
                headers=self._headers,
                timeout=30.0,
            )
        return self._http_client

    def close(self) -> None:
        """Close the underlying HTTP client, releasing held resources."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> GitHubClient:
        """Allow ``GitHubClient`` to be used as a context manager."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Ensure the underlying client is closed when leaving the context."""
        self.close()

    # -- helpers ----------------------------------------------------------------

    @staticmethod
    def _stub_id() -> int:
        """Return a random integer ID that mirrors real GitHub IDs."""
        return int(uuid.uuid4().int % 900_000_000) + 100_000_000

    def _html_base(self) -> str:
        """Derive the HTML base URL from the API base URL.

        For the public API (``api.github.com``) the HTML host is
        ``github.com``.  For GHES the base URL is used as-is.
        """
        if "api.github.com" in self.base_url:
            return "https://github.com"
        return self.base_url

    # -- public API -------------------------------------------------------------

    def create_repo(
        self,
        name: str,
        owner: str = "ai-dan",
        private: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new GitHub repository.

        Args:
            name: Repository name.
            owner: Repository owner or organisation.
            private: Whether the repository should be private.

        Returns:
            Repository metadata dictionary.
        """
        html_base = self._html_base()
        return {
            "id": self._stub_id(),
            "name": name,
            "full_name": f"{owner}/{name}",
            "private": private,
            "html_url": f"{html_base}/{owner}/{name}",
            "clone_url": f"{html_base}/{owner}/{name}.git",
            "stub": True,
        }

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new issue in the specified repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: Issue title.
            body: Issue body in Markdown.
            labels: Optional list of label names to apply.

        Returns:
            Issue metadata dictionary.
        """
        issue_number = int(uuid.uuid4().int % 9_999) + 1
        html_base = self._html_base()
        return {
            "id": self._stub_id(),
            "number": issue_number,
            "title": title,
            "body": body,
            "labels": labels or [],
            "state": "open",
            "html_url": f"{html_base}/{owner}/{repo}/issues/{issue_number}",
            "stub": True,
        }

    def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, Any]:
        """
        Create a pull request in the specified repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: Pull-request title.
            body: Pull-request description in Markdown.
            head: Name of the branch containing the changes.
            base: Name of the branch the changes should be pulled into.

        Returns:
            Pull-request metadata dictionary.
        """
        pr_number = int(uuid.uuid4().int % 9_999) + 1
        html_base = self._html_base()
        return {
            "id": self._stub_id(),
            "number": pr_number,
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "state": "open",
            "html_url": f"{html_base}/{owner}/{repo}/pull/{pr_number}",
            "stub": True,
        }

    def dispatch_workflow(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        inputs: dict[str, Any],
    ) -> bool:
        """
        Trigger a GitHub Actions workflow dispatch event.

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            workflow_id: Workflow file name or ID.
            inputs: Key-value inputs passed to the workflow.

        Returns:
            ``True`` if the dispatch was accepted (stub always succeeds).
        """
        return True
