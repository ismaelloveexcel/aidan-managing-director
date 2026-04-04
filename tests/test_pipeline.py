"""Tests for the Phase 2 multi-layer pipeline."""

from __future__ import annotations

import pytest

from app.core.pipeline import PipelineBlockedError, run_pipeline
from app.portfolio.repository import PortfolioRepository


def _idea_input(project_id: str = "PRJ-PIP-1") -> dict:
    return {
        "project_id": project_id,
        "idea_id": "IDEA-PIP-1",
        "title": "ProposalCopilot Lite",
        "hypothesis": "Faster proposals increase freelancer signup intent.",
        "target_user": "Freelancers with recurring outbound sales workflows",
        "problem": "Proposal writing is repetitive, manual, and time-consuming.",
        "solution": "Generate niche proposal drafts from brief prompts with workflow automation.",
        "mvp_scope": ["Landing page", "CTA endpoint"],
        "acceptance_criteria": ["Landing page loads", "CTA captures email"],
        "landing_page_requirements": ["Primary CTA: Get early access"],
        "cta": "Get early access",
        "pricing_hint": "Subscription $49/month",
    }


def test_run_pipeline_returns_build_brief() -> None:
    brief = run_pipeline(_idea_input())
    assert brief.project_id == "PRJ-PIP-1"
    assert brief.validation_score > 0
    assert brief.monetization_model in {"waitlist", "subscription", "one_time", "unspecified"}
    assert brief.command_bundle["market_truth"]["decision"] == "PASS"


def test_run_pipeline_blocks_invalid_payload() -> None:
    bad = _idea_input()
    bad["mvp_scope"] = []
    with pytest.raises(PipelineBlockedError):
        run_pipeline(bad)


def test_run_pipeline_persists_brief_when_repository_provided(tmp_path) -> None:
    repo = PortfolioRepository(db_path=str(tmp_path / "pipeline.sqlite3"))
    project = repo.create_project(name="pipe", description="pipeline test", project_id="PRJ-PIP-1")
    assert project.project_id == "PRJ-PIP-1"

    brief = run_pipeline(_idea_input(project_id="PRJ-PIP-1"), repository=repo)
    latest = repo.get_latest_build_brief("PRJ-PIP-1")

    assert latest is not None
    assert latest.brief_hash == brief.brief_hash()
