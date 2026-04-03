"""
Typed data contracts for the GitHub Factory execution layer.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _utcnow_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class FactoryRunStatus(str, Enum):
    """Lifecycle states for a factory run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class BuildBrief(BaseModel):
    """Canonical contract passed from AI-DAN to the GitHub Factory."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    project_id: str
    idea_id: str
    hypothesis: str

    target_user: str
    problem: str
    solution: str

    mvp_scope: list[str]
    acceptance_criteria: list[str]

    landing_page_requirements: list[str]
    cta: str
    pricing_hint: str

    deployment_target: Literal["vercel"] = "vercel"
    command_bundle: dict[str, Any]
    feature_flags: dict[str, bool] = Field(
        default_factory=lambda: {
            "dry_run": True,
            "live_factory": False,
        },
    )
    validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_flags: list[str] = Field(default_factory=list)
    monetization_model: str = "unspecified"
    deployment_plan: dict[str, Any] = Field(default_factory=dict)
    launch_gate: dict[str, Any] = Field(default_factory=dict)
    brief_hash_value: str | None = Field(default=None, alias="brief_hash")
    idempotency_key_value: str | None = Field(default=None, alias="idempotency_key")

    @field_validator(
        "project_id",
        "idea_id",
        "hypothesis",
        "target_user",
        "problem",
        "solution",
        "cta",
        "pricing_hint",
    )
    @classmethod
    def _non_empty_str(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Field must be a non-empty string.")
        return value.strip()

    @field_validator("mvp_scope", "acceptance_criteria", "landing_page_requirements")
    @classmethod
    def _non_empty_list(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list) or not value:
            raise ValueError("Field must be a non-empty list.")
        normalised = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if not normalised:
            raise ValueError("Field must contain at least one non-empty string.")
        return normalised

    @field_validator("command_bundle")
    @classmethod
    def _non_empty_command_bundle(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or not value:
            raise ValueError("command_bundle must be a non-empty dictionary.")
        return value

    @field_validator("feature_flags")
    @classmethod
    def _validate_feature_flags(cls, value: dict[str, bool]) -> dict[str, bool]:
        if not isinstance(value, dict):
            raise ValueError("feature_flags must be a dictionary.")
        merged = {"dry_run": True, "live_factory": False}
        merged.update(value)
        for key, flag in merged.items():
            if not isinstance(flag, bool):
                raise ValueError(f"feature_flags['{key}'] must be boolean.")
        return merged

    @field_validator("risk_flags")
    @classmethod
    def _validate_risk_flags(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("risk_flags must be a list of strings.")
        cleaned = [flag.strip() for flag in value if isinstance(flag, str) and flag.strip()]
        return cleaned

    @field_validator("deployment_plan", "launch_gate")
    @classmethod
    def _validate_object_fields(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("Field must be a dictionary.")
        return value

    @model_validator(mode="after")
    def _validate_cta_present_in_landing_requirements(self) -> "BuildBrief":
        requirement_text = " ".join(self.landing_page_requirements).lower()
        if self.cta.lower() not in requirement_text:
            raise ValueError(
                "cta must appear in landing_page_requirements to ensure copy consistency.",
            )
        return self

    @model_validator(mode="after")
    def _sync_hash_fields(self) -> "BuildBrief":
        computed_hash = self.brief_hash()
        expected_key = f"{self.project_id}:{computed_hash}"

        if self.brief_hash_value is None:
            self.brief_hash_value = computed_hash
        elif self.brief_hash_value != computed_hash:
            raise ValueError("brief_hash does not match computed payload hash.")

        if self.idempotency_key_value is None:
            self.idempotency_key_value = expected_key
        elif self.idempotency_key_value != expected_key:
            raise ValueError("idempotency_key does not match computed project-scoped key.")
        return self

    def canonical_json(self) -> str:
        """Return canonical JSON used for hashing and idempotency."""
        payload = self.model_dump(
            mode="json",
            exclude={"brief_hash_value", "idempotency_key_value"},
        )
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

    def brief_hash(self) -> str:
        """Return SHA-256 hash of the canonical brief payload."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def idempotency_key(self) -> str:
        """Return an idempotency key scoped to this project and brief hash."""
        return f"{self.project_id}:{self.brief_hash()}"

    def to_product_brief_markdown(self) -> str:
        """Render the brief as PRODUCT_BRIEF.md content."""
        mvp_scope = "\n".join(f"- {item}" for item in self.mvp_scope)
        acceptance = "\n".join(f"- {item}" for item in self.acceptance_criteria)
        landing = "\n".join(f"- {item}" for item in self.landing_page_requirements)
        command_bundle = json.dumps(self.command_bundle, indent=2, sort_keys=True)
        feature_flags = json.dumps(self.feature_flags, indent=2, sort_keys=True)
        deployment_plan = json.dumps(self.deployment_plan, indent=2, sort_keys=True)
        launch_gate = json.dumps(self.launch_gate, indent=2, sort_keys=True)
        risk_flags = "\n".join(f"- {item}" for item in self.risk_flags) or "- none"

        return (
            f"# PRODUCT BRIEF\n\n"
            f"- Schema Version: `{self.schema_version}`\n"
            f"- Project ID: `{self.project_id}`\n"
            f"- Idea ID: `{self.idea_id}`\n"
            f"- Deployment Target: `{self.deployment_target}`\n\n"
            f"- Brief Hash: `{self.brief_hash_value or self.brief_hash()}`\n"
            f"- Idempotency Key: `{self.idempotency_key_value or self.idempotency_key()}`\n"
            f"- Validation Score: `{self.validation_score}`\n"
            f"- Monetization Model: `{self.monetization_model}`\n\n"
            f"## Hypothesis\n{self.hypothesis}\n\n"
            f"## Target User\n{self.target_user}\n\n"
            f"## Problem\n{self.problem}\n\n"
            f"## Solution\n{self.solution}\n\n"
            f"## MVP Scope\n{mvp_scope}\n\n"
            f"## Acceptance Criteria\n{acceptance}\n\n"
            f"## Landing Page Requirements\n{landing}\n\n"
            f"## Risk Flags\n{risk_flags}\n\n"
            f"## CTA\n{self.cta}\n\n"
            f"## Pricing Hint\n{self.pricing_hint}\n\n"
            f"## Command Bundle\n```json\n{command_bundle}\n```\n\n"
            f"## Deployment Plan\n```json\n{deployment_plan}\n```\n\n"
            f"## Launch Gate\n```json\n{launch_gate}\n```\n\n"
            f"## Feature Flags\n```json\n{feature_flags}\n```\n"
        )


class BuildBriefValidationResult(BaseModel):
    """Validation response payload for BuildBrief checks."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    brief_hash: str | None = None
    idempotency_key: str | None = None


class FactoryBuildRequest(BaseModel):
    """Request payload for triggering a factory build run."""

    build_brief: BuildBrief
    dry_run: bool | None = None


class FactoryRunResult(BaseModel):
    """Result of a factory orchestration run."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    idea_id: str
    status: FactoryRunStatus
    idempotency_key: str
    dry_run: bool
    repo_url: str | None = None
    deploy_url: str | None = None
    error: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    stub: bool = True
    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)

