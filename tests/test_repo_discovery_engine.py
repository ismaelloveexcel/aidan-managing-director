"""Tests for the repo discovery engine."""

from __future__ import annotations


from app.integrations.repo_discovery_engine import (
    RepoCandidate,
    SelectionMode,
    discover_repos,
    score_candidate,
    select_template,
)


class TestScoreCandidate:
    """Tests for score_candidate function."""

    def test_high_score_popular_repo(self) -> None:
        candidate = RepoCandidate(
            repo_name="awesome-saas",
            stars=1500,
            last_updated="2026-03-01T00:00:00Z",
            has_readme=True,
            is_archived=False,
            is_fork=False,
            language="Python",
            license="MIT",
        )
        scored = score_candidate(candidate)
        assert scored.score >= 70
        assert "stars" in scored.score_breakdown

    def test_low_score_archived(self) -> None:
        candidate = RepoCandidate(
            repo_name="old-repo",
            stars=0,
            last_updated="2020-01-01T00:00:00Z",
            has_readme=False,
            is_archived=True,
            is_fork=True,
            language="Perl",
            license="unknown",
        )
        scored = score_candidate(candidate)
        assert scored.score < 40
        assert scored.rejection_reason

    def test_archived_gets_zero_active_score(self) -> None:
        candidate = RepoCandidate(
            repo_name="test",
            is_archived=True,
        )
        scored = score_candidate(candidate)
        assert scored.score_breakdown.get("active") == 0.0

    def test_fork_gets_zero_original_score(self) -> None:
        candidate = RepoCandidate(
            repo_name="test",
            is_fork=True,
        )
        scored = score_candidate(candidate)
        assert scored.score_breakdown.get("original") == 0.0

    def test_score_capped_at_100(self) -> None:
        candidate = RepoCandidate(
            repo_name="super-repo",
            stars=10000,
            last_updated="2026-04-01T00:00:00Z",
            has_readme=True,
            is_archived=False,
            is_fork=False,
            language="Python",
            license="MIT",
        )
        scored = score_candidate(candidate)
        assert scored.score <= 100.0


class TestSelectTemplate:
    """Tests for select_template function."""

    def test_high_score_reuses_external(self) -> None:
        candidates = [
            RepoCandidate(repo_name="good", score=75),
        ]
        name, mode, reason = select_template(candidates)
        assert mode == SelectionMode.REUSE_EXTERNAL
        assert name == "good"

    def test_medium_score_uses_internal(self) -> None:
        candidates = [
            RepoCandidate(repo_name="mid", score=55),
        ]
        name, mode, reason = select_template(candidates)
        assert mode == SelectionMode.USE_INTERNAL
        assert "mid" in name

    def test_low_score_builds_minimal(self) -> None:
        candidates = [
            RepoCandidate(repo_name="weak", score=20),
        ]
        name, mode, reason = select_template(candidates)
        assert mode == SelectionMode.BUILD_MINIMAL

    def test_empty_candidates_builds_minimal(self) -> None:
        name, mode, reason = select_template([])
        assert mode == SelectionMode.BUILD_MINIMAL
        assert name == ""

    def test_archived_repos_filtered(self) -> None:
        candidates = [
            RepoCandidate(repo_name="archived", score=90, is_archived=True),
        ]
        name, mode, reason = select_template(candidates)
        assert mode == SelectionMode.BUILD_MINIMAL

    def test_forks_filtered_unless_high_score(self) -> None:
        candidates = [
            RepoCandidate(repo_name="fork-low", score=50, is_fork=True),
        ]
        name, mode, reason = select_template(candidates)
        assert mode == SelectionMode.BUILD_MINIMAL

    def test_high_score_fork_accepted(self) -> None:
        candidates = [
            RepoCandidate(repo_name="fork-high", score=75, is_fork=True),
        ]
        name, mode, reason = select_template(candidates)
        assert mode == SelectionMode.REUSE_EXTERNAL


class TestDiscoverRepos:
    """Tests for discover_repos function."""

    def test_discover_with_candidates(self) -> None:
        data = [
            {
                "name": "saas-template",
                "url": "https://github.com/org/saas-template",
                "description": "A SaaS starter template",
                "stars": 500,
                "updated_at": "2026-03-01T00:00:00Z",
                "archived": False,
                "fork": False,
                "language": "TypeScript",
                "license": {"spdx_id": "MIT"},
            },
        ]
        result = discover_repos(search_query="SaaS template", candidates_data=data)
        assert len(result.candidates) == 1
        assert result.candidates[0].score > 0
        assert result.search_query == "SaaS template"

    def test_discover_empty(self) -> None:
        result = discover_repos(search_query="test")
        assert len(result.candidates) == 0
        assert result.selection_mode == SelectionMode.BUILD_MINIMAL

    def test_discover_result_structure(self) -> None:
        result = discover_repos(search_query="test", candidates_data=[])
        assert result.discovered_at
        assert result.search_query == "test"
