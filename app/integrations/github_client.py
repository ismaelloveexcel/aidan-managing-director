"""
github_client.py – GitHub API integration for the GitHub Factory.

Provides a typed client for interacting with GitHub repositories,
issues, pull requests, and workflow dispatch events.
"""

from typing import Any


class GitHubClient:
    """
    Wraps the GitHub REST API for use by the command routing layer.

    Business logic to be implemented in a future iteration.
    """

    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        """
        Initialise the GitHub client.

        Args:
            token: Personal access token or GitHub App installation token.
            base_url: Base URL for the GitHub API (override for GHES).
        """
        self.token = token
        self.base_url = base_url

    def create_repository(self, name: str, private: bool = True) -> dict[str, Any]:
        """
        Create a new GitHub repository.

        Args:
            name: Repository name.
            private: Whether the repository should be private.

        Returns:
            Repository metadata returned by the GitHub API.
        """
        raise NotImplementedError

    def dispatch_workflow(self, owner: str, repo: str, workflow_id: str, inputs: dict[str, Any]) -> bool:
        """
        Trigger a GitHub Actions workflow dispatch event.

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            workflow_id: Workflow file name or ID.
            inputs: Key-value inputs passed to the workflow.

        Returns:
            True if the dispatch was accepted, False otherwise.
        """
        raise NotImplementedError

    def create_issue(self, owner: str, repo: str, title: str, body: str) -> dict[str, Any]:
        """
        Create a new issue in the specified repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: Issue title.
            body: Issue body in Markdown.

        Returns:
            Issue metadata returned by the GitHub API.
        """
        raise NotImplementedError
