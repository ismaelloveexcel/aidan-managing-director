"""Tests for the GitHub project request flow."""

from __future__ import annotations

import pytest

from app.integrations.github_client import (
    GitHubClient,
    IssueBundleRequest,
    IssueSpec,
    RepoRequest,
    RepoStatus,
)
from app.planning.command_compiler import CommandCompiler
from app.planning.project_request import (
    ProjectRepoCommand,
    ProjectRequestPayload,
    build_project_request,
)


# ---------------------------------------------------------------------------
# GitHubClient – prepare_repo_request
# ---------------------------------------------------------------------------


class TestPrepareRepoRequest:
    """Tests for GitHubClient.prepare_repo_request."""

    def setup_method(self) -> None:
        self.client = GitHubClient(token="test-token")

    def test_returns_dict_with_required_fields(self) -> None:
        result = self.client.prepare_repo_request("my-project")
        assert isinstance(result, dict)
        assert result["name"] == "my-project"
        assert result["owner"] == "ai-dan"
        assert result["private"] is True
        assert "request_id" in result
        assert "created_at" in result

    def test_custom_owner_and_description(self) -> None:
        result = self.client.prepare_repo_request(
            "my-project",
            owner="custom-org",
            description="A cool project",
            private=False,
        )
        assert result["owner"] == "custom-org"
        assert result["description"] == "A cool project"
        assert result["private"] is False

    def test_template_and_topics(self) -> None:
        result = self.client.prepare_repo_request(
            "my-project",
            template="template-repo",
            topics=["python", "ai"],
        )
        assert result["template"] == "template-repo"
        assert result["topics"] == ["python", "ai"]

    def test_default_topics_is_empty(self) -> None:
        result = self.client.prepare_repo_request("my-project")
        assert result["topics"] == []

    def test_result_validates_as_repo_request(self) -> None:
        result = self.client.prepare_repo_request("my-project")
        model = RepoRequest(**result)
        assert model.name == "my-project"


# ---------------------------------------------------------------------------
# GitHubClient – create_issue_bundle
# ---------------------------------------------------------------------------


class TestCreateIssueBundle:
    """Tests for GitHubClient.create_issue_bundle."""

    def setup_method(self) -> None:
        self.client = GitHubClient(token="test-token")

    def test_returns_bundle_with_issues(self) -> None:
        issues = [
            {"title": "First issue", "body": "Do the thing"},
            {"title": "Second issue", "labels": ["bug"]},
        ]
        result = self.client.create_issue_bundle("org", "repo", issues)
        assert result["owner"] == "org"
        assert result["repo"] == "repo"
        assert len(result["issues"]) == 2
        assert result["issues"][0]["title"] == "First issue"
        assert result["issues"][1]["labels"] == ["bug"]

    def test_bundle_has_bundle_id(self) -> None:
        issues = [{"title": "Issue"}]
        result = self.client.create_issue_bundle("org", "repo", issues)
        assert "bundle_id" in result
        assert isinstance(result["bundle_id"], str)

    def test_empty_issues_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one issue"):
            self.client.create_issue_bundle("org", "repo", [])

    def test_issue_without_title_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty 'title'"):
            self.client.create_issue_bundle("org", "repo", [{"body": "no title"}])

    def test_issue_with_empty_title_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty 'title'"):
            self.client.create_issue_bundle("org", "repo", [{"title": ""}])

    def test_result_validates_as_bundle(self) -> None:
        issues = [{"title": "Setup", "body": "Init project", "labels": ["setup"]}]
        result = self.client.create_issue_bundle("org", "repo", issues)
        model = IssueBundleRequest(**result)
        assert len(model.issues) == 1
        assert isinstance(model.issues[0], IssueSpec)


# ---------------------------------------------------------------------------
# GitHubClient – get_repo_status
# ---------------------------------------------------------------------------


class TestGetRepoStatus:
    """Tests for GitHubClient.get_repo_status."""

    def setup_method(self) -> None:
        self.client = GitHubClient(token="test-token")

    def test_returns_status_dict(self) -> None:
        result = self.client.get_repo_status("org", "repo")
        assert result["owner"] == "org"
        assert result["repo"] == "repo"
        assert result["exists"] is True
        assert result["default_branch"] == "main"
        assert result["stub"] is True

    def test_contains_html_url(self) -> None:
        result = self.client.get_repo_status("org", "repo")
        assert "org/repo" in result["html_url"]

    def test_result_validates_as_repo_status(self) -> None:
        result = self.client.get_repo_status("org", "repo")
        model = RepoStatus(**result)
        assert model.exists is True


# ---------------------------------------------------------------------------
# CommandCompiler – create_project_repo action
# ---------------------------------------------------------------------------


class TestCreateProjectRepoAction:
    """Tests for create_project_repo in the command compiler."""

    def setup_method(self) -> None:
        self.compiler = CommandCompiler()

    def test_validate_accepts_create_project_repo(self) -> None:
        command = {
            "action": "create_project_repo",
            "parameters": {"project_name": "idea-x"},
        }
        assert self.compiler.validate(command) is True

    def test_compile_create_project_repo_step(self) -> None:
        step = {"action": "create_project_repo", "description": "Create repo for idea"}
        result = self.compiler.compile(step)
        assert result["action"] == "create_project_repo"
        assert "command_id" in result

    def test_compile_batch_with_create_project_repo(self) -> None:
        steps = [
            {"action": "create_project_repo", "description": "Create repo"},
            {"action": "setup_project", "description": "Scaffold project"},
        ]
        results = self.compiler.compile_batch(steps)
        assert len(results) == 2
        assert results[0]["action"] == "create_project_repo"


# ---------------------------------------------------------------------------
# build_project_request – end-to-end flow
# ---------------------------------------------------------------------------


class TestBuildProjectRequest:
    """Tests for the project request flow entry point."""

    def _valid_idea(self) -> dict:
        return {
            "name": "Smart Widget",
            "description": "A widget that learns user habits",
            "target_user": "developers",
            "monetization_path": "SaaS subscription",
            "difficulty": "medium",
            "time_to_launch": "4 weeks",
        }

    def test_returns_full_payload(self) -> None:
        result = build_project_request(self._valid_idea())
        assert result["project_name"] == "Smart Widget"
        assert "repo_request" in result
        assert "issue_bundle" in result
        assert "command" in result
        assert "created_at" in result

    def test_repo_name_is_slugified(self) -> None:
        result = build_project_request(self._valid_idea())
        repo_name = result["repo_request"]["name"]
        assert repo_name == "smart-widget"
        assert " " not in repo_name

    def test_issue_bundle_has_starter_issues(self) -> None:
        result = build_project_request(self._valid_idea())
        issues = result["issue_bundle"]["issues"]
        assert len(issues) >= 3
        titles = [i["title"] for i in issues]
        assert any("scaffold" in t.lower() for t in titles)

    def test_command_is_create_project_repo(self) -> None:
        result = build_project_request(self._valid_idea())
        cmd = result["command"]
        assert cmd["action"] == "create_project_repo"
        assert cmd["parameters"]["project_name"] == "Smart Widget"
        assert cmd["parameters"]["repo_name"] == "smart-widget"

    def test_custom_owner(self) -> None:
        result = build_project_request(self._valid_idea(), owner="my-org")
        assert result["repo_request"]["owner"] == "my-org"
        assert result["issue_bundle"]["owner"] == "my-org"
        assert result["command"]["parameters"]["owner"] == "my-org"

    def test_topics_include_target_user(self) -> None:
        result = build_project_request(self._valid_idea())
        topics = result["repo_request"]["topics"]
        assert "developers" in topics

    def test_topics_include_monetised_flag(self) -> None:
        result = build_project_request(self._valid_idea())
        topics = result["repo_request"]["topics"]
        assert "monetised" in topics

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValueError, match="'name'"):
            build_project_request({"description": "no name"})

    def test_missing_description_raises(self) -> None:
        with pytest.raises(ValueError, match="'description'"):
            build_project_request({"name": "thing"})

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="'name'"):
            build_project_request({"name": "", "description": "x"})

    def test_payload_validates_as_model(self) -> None:
        result = build_project_request(self._valid_idea())
        model = ProjectRequestPayload(**result)
        assert model.project_name == "Smart Widget"

    def test_accepts_custom_github_client(self) -> None:
        custom = GitHubClient(token="custom-token", base_url="https://ghes.example.com/api/v3")
        result = build_project_request(self._valid_idea(), github_client=custom)
        assert result["project_name"] == "Smart Widget"

    def test_public_repo(self) -> None:
        result = build_project_request(self._valid_idea(), private=False)
        assert result["repo_request"]["private"] is False
        assert result["command"]["parameters"]["private"] is False

    def test_idea_without_optional_fields(self) -> None:
        idea = {"name": "Simple Idea", "description": "A simple idea"}
        result = build_project_request(idea)
        assert result["repo_request"]["topics"] == []
        assert result["project_name"] == "Simple Idea"
