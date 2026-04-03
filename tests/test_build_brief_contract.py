"""Contract tests for BuildBrief and BuildBrief validator."""

from __future__ import annotations

from app.factory.build_brief_validator import (
    validate_build_brief,
    validate_build_brief_payload,
)
from app.factory.models import BuildBrief


def _valid_payload() -> dict:
    return {
        "project_id": "PRJ-001",
        "idea_id": "IDEA-001",
        "hypothesis": "Freelancers will pay to generate proposals faster.",
        "target_user": "Freelancers",
        "problem": "Proposal writing takes too long.",
        "solution": "Generate tailored proposals from a simple input form.",
        "mvp_scope": ["Landing page", "Lead capture form", "Basic AI proposal draft flow"],
        "acceptance_criteria": ["User can submit lead", "CTA works", "Deployment is live"],
        "landing_page_requirements": [
            "Headline communicates proposal speed benefit",
            "Primary CTA: Get early access",
            "Trust section with concise proof points",
        ],
        "cta": "Get early access",
        "pricing_hint": "Preorder at $19",
        "deployment_target": "vercel",
        "command_bundle": {"build": "npm run build", "start": "npm run start"},
        "feature_flags": {"dry_run": True, "live_factory": False},
    }


class TestBuildBriefContract:
    """Schema-level and semantic contract checks."""

    def test_valid_payload_parses(self) -> None:
        brief = BuildBrief(**_valid_payload())
        assert brief.project_id == "PRJ-001"
        assert brief.deployment_target == "vercel"

    def test_hash_and_idempotency_key_present(self) -> None:
        brief = BuildBrief(**_valid_payload())
        assert len(brief.brief_hash()) == 64
        assert brief.idempotency_key().startswith("PRJ-001:")

    def test_cta_must_appear_in_requirements(self) -> None:
        payload = _valid_payload()
        payload["landing_page_requirements"] = ["No matching CTA in this list"]
        try:
            BuildBrief(**payload)
            assert False, "Expected validation error for missing CTA in landing requirements."
        except Exception as exc:  # pydantic validation exception
            assert "cta must appear" in str(exc).lower()

    def test_validator_accepts_valid_brief(self) -> None:
        brief = BuildBrief(**_valid_payload())
        result = validate_build_brief(brief)
        assert result.valid is True
        assert result.brief_hash is not None
        assert result.idempotency_key is not None

    def test_validator_rejects_invalid_payload(self) -> None:
        payload = _valid_payload()
        payload["mvp_scope"] = []
        result = validate_build_brief_payload(payload)
        assert result.valid is False
        assert len(result.errors) > 0
