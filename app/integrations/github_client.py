"""
github_client.py – GitHub API integration for the GitHub Factory.

Provides a typed client for interacting with GitHub repositories,
issues, pull requests, and workflow dispatch events.  Also exposes
higher-level helpers for preparing structured project-creation
request payloads that downstream factory systems can consume.

All methods are currently **stub implementations** that return
realistic placeholder data.  Real HTTP calls (via ``httpx``) will
replace the stubs once API credentials are provisioned.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas for GitHub Factory request payloads
# ---------------------------------------------------------------------------


class RepoRequest(BaseModel):
    """Structured payload for requesting a new repository from the factory."""

    name: str = Field(description="Repository name.")
    owner: str = Field(description="Repository owner or organisation.")
    description: str = Field(default="", description="Short repository description.")
    private: bool = Field(default=True, description="Whether the repo is private.")
    template: str | None = Field(
        default=None,
        description="Optional template repository to clone from.",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="GitHub topics to apply to the repository.",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this request.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp when the request was created.",
    )


class IssueSpec(BaseModel):
    """Specification for a single issue within an issue bundle."""

    title: str = Field(description="Issue title.")
    body: str = Field(default="", description="Issue body in Markdown.")
    labels: list[str] = Field(
        default_factory=list,
        description="Labels to apply to the issue.",
    )


class IssueBundleRequest(BaseModel):
    """A batch of issues to create in a repository."""

    owner: str = Field(description="Repository owner.")
    repo: str = Field(description="Repository name.")
    issues: list[IssueSpec] = Field(description="Ordered list of issues to create.")
    bundle_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this bundle.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp when the bundle was created.",
    )


class RepoStatus(BaseModel):
    """Status snapshot of a repository."""

    owner: str = Field(description="Repository owner.")
    repo: str = Field(description="Repository name.")
    exists: bool = Field(description="Whether the repository exists.")
    default_branch: str | None = Field(
        default=None,
        description="Default branch name, if the repo exists.",
    )
    open_issues_count: int = Field(
        default=0,
        description="Number of open issues.",
    )
    html_url: str | None = Field(
        default=None,
        description="Browser URL for the repository.",
    )
    stub: bool = Field(
        default=True,
        description="True when the response is a stub (not from a live API).",
    )


class CommitFileResult(BaseModel):
    """Result payload for a single file commit operation."""

    commit_sha: str = Field(description="Synthetic or real commit SHA.")
    html_url: str = Field(description="Commit URL.")
    path: str = Field(description="Repository file path committed.")
    stub: bool = Field(
        default=True,
        description="True when response comes from stub behavior.",
    )


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
        """Return a random integer ID that mirrors real GitHub IDs.

        Real GitHub IDs are large positive integers typically in the
        hundreds-of-millions range.  We produce values between
        100 000 000 and 999 999 999 to stay realistic.
        """
        return int(uuid.uuid4().int % 900_000_000) + 100_000_000

    def _html_base(self) -> str:
        """Derive the HTML base URL from the API base URL.

        For the public API (``api.github.com``) the HTML host is
        ``github.com``.  For GHES the base URL is used as-is.
        """
        parsed = urlparse(self.base_url)
        if parsed.hostname == "api.github.com":
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
        ref: str = "main",
    ) -> bool:
        """
        Trigger a GitHub Actions workflow dispatch event.

        When a valid token is configured, issues a real ``POST`` to the
        GitHub API.  Falls back to a stub (always returns ``True``) when
        the token is missing or the API call fails.

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            workflow_id: Workflow file name or ID.
            inputs: Key-value inputs passed to the workflow.
            ref: Git ref (branch/tag) to run the workflow on.

        Returns:
            ``True`` if the dispatch was accepted.
        """
        if not self.token:
            logger.warning("dispatch_workflow: no token configured, returning False for local fallback.")
            return False

        try:
            response = self._client().post(
                f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
                json={"ref": ref, "inputs": {k: str(v) for k, v in inputs.items()}},
            )
            # GitHub returns 204 No Content on success.
            if response.status_code == 204:
                return True
            # Token is set but dispatch was rejected – report failure.
            logger.error(
                "dispatch_workflow: GitHub returned %d for %s/%s/%s.",
                response.status_code,
                owner,
                repo,
                workflow_id,
            )
            return False
        except Exception:
            # Network / config error with a real token – report failure.
            logger.error("dispatch_workflow: HTTP error dispatching to %s/%s.", owner, repo, exc_info=True)
            return False

    def dispatch_factory_build(
        self,
        *,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str = "main",
        project_id: str,
        correlation_id: str,
        callback_url: str,
        build_brief_json: str,
        dry_run: bool = True,
    ) -> bool:
        """Dispatch a factory build workflow with correlation and callback info.

        This is the primary integration point for MD → Factory communication.
        The workflow receives the full build brief, a correlation_id for
        end-to-end tracing, and a callback_url for result delivery.

        Args:
            owner: Factory repository owner.
            repo: Factory repository name.
            workflow_id: Workflow file name (e.g. ``factory-build.yml``).
            ref: Git ref to run the workflow on.
            project_id: Project identifier from the BuildBrief.
            correlation_id: Unique ID for end-to-end tracing.
            callback_url: URL the factory should POST results to.
            build_brief_json: JSON-serialised BuildBrief payload.
            dry_run: Whether this is a dry-run execution.

        Returns:
            ``True`` if the dispatch was accepted.
        """
        inputs = {
            "project_id": project_id,
            "correlation_id": correlation_id,
            "callback_url": callback_url,
            "build_brief_json": build_brief_json,
            "dry_run": str(dry_run).lower(),
        }
        return self.dispatch_workflow(
            owner=owner,
            repo=repo,
            workflow_id=workflow_id,
            inputs=inputs,
            ref=ref,
        )

    def create_repo_from_template(
        self,
        *,
        owner: str,
        name: str,
        template_owner: str,
        template_repo: str,
        private: bool = True,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a repository from a template repository.

        Stub implementation returns a realistic repository metadata payload.
        """
        repo_meta = self.create_repo(name=name, owner=owner, private=private)
        repo_meta["description"] = description
        repo_meta["template_used"] = f"{template_owner}/{template_repo}"
        repo_meta["stub"] = True
        return repo_meta

    def upsert_file(
        self,
        *,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Create or update a repository file.

        Stub implementation returns synthetic commit metadata.
        """
        html_base = self._html_base()
        commit_sha = uuid.uuid4().hex[:12]
        result = CommitFileResult(
            commit_sha=commit_sha,
            html_url=f"{html_base}/{owner}/{repo}/commit/{commit_sha}",
            path=path,
            stub=True,
        )
        return result.model_dump()

    # -- GitHub Factory request helpers ----------------------------------------

    def prepare_repo_request(
        self,
        name: str,
        owner: str = "ai-dan",
        *,
        description: str = "",
        private: bool = True,
        template: str | None = None,
        topics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Prepare a structured repository creation request payload.

        Builds a :class:`RepoRequest` that downstream factory systems
        can consume to provision a new repository.  No actual API call
        is made.

        Args:
            name: Repository name (e.g. ``"idea-x"``).
            owner: Repository owner or organisation.
            description: Short repository description.
            private: Whether the repository should be private.
            template: Optional template repository to clone from.
            topics: GitHub topics to apply to the repository.

        Returns:
            Serialised :class:`RepoRequest` dictionary.
        """
        request = RepoRequest(
            name=name,
            owner=owner,
            description=description,
            private=private,
            template=template,
            topics=topics or [],
        )
        return request.model_dump()

    def create_issue_bundle(
        self,
        owner: str,
        repo: str,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a bundled issue-creation request for a repository.

        Each entry in *issues* must contain at least a ``title`` key.
        Optional keys are ``body`` (Markdown string) and ``labels``
        (list of label names).

        Args:
            owner: Repository owner.
            repo: Repository name.
            issues: List of issue specifications.

        Returns:
            Serialised :class:`IssueBundleRequest` dictionary.

        Raises:
            ValueError: If *issues* is empty or any entry lacks a title.
        """
        if not issues:
            raise ValueError("Issue bundle must contain at least one issue.")

        specs: list[IssueSpec] = []
        for idx, raw in enumerate(issues):
            if not isinstance(raw, dict):
                raise ValueError(
                    f"Each issue must be a dictionary specification (index {idx}).",
                )

            title = raw.get("title")
            if not title or not isinstance(title, str):
                raise ValueError(
                    f"Each issue must have a non-empty 'title' string (index {idx}).",
                )

            body = raw.get("body", "")
            if body is None:
                body = ""
            if not isinstance(body, str):
                raise ValueError(
                    f"Each issue 'body' must be a string if provided (index {idx}).",
                )

            labels = raw.get("labels", [])
            if labels is None:
                labels = []
            if not isinstance(labels, list) or any(
                not isinstance(label, str) for label in labels
            ):
                raise ValueError(
                    f"Each issue 'labels' must be a list of strings if provided (index {idx}).",
                )

            specs.append(
                IssueSpec(
                    title=title,
                    body=body,
                    labels=labels,
                ),
            )

        bundle = IssueBundleRequest(
            owner=owner,
            repo=repo,
            issues=specs,
        )
        return bundle.model_dump()

    def get_repo_status(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """Return the current status of a repository.

        This is a **stub** that always reports the repository as
        existing.  When live credentials are available it will query
        the GitHub API.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Serialised :class:`RepoStatus` dictionary.
        """
        html_base = self._html_base()
        status = RepoStatus(
            owner=owner,
            repo=repo,
            exists=True,
            default_branch="main",
            open_issues_count=0,
            html_url=f"{html_base}/{owner}/{repo}",
            stub=True,
        )
        return status.model_dump()
