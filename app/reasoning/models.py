"""
models.py – Pydantic models for the AI-DAN reasoning layer.

Defines structured, typed data models used across strategist, idea engine,
evaluator, and critic modules.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Strategy models
# ---------------------------------------------------------------------------


class IntentType(str, Enum):
    """Classified intent types that the strategist can recognise."""

    BUILD = "build"
    IMPROVE = "improve"
    EXPLORE = "explore"
    MONETISE = "monetise"
    PIVOT = "pivot"
    UNKNOWN = "unknown"


class StrategicDirection(BaseModel):
    """Output of the strategist's analysis of user intent and context."""

    intent: IntentType = Field(
        description="The classified intent behind the user's input.",
    )
    priority: str = Field(
        description="High-level priority derived from the intent (e.g. 'revenue', 'growth').",
    )
    direction: str = Field(
        description="A concise strategic direction statement.",
    )
    objectives: list[str] = Field(
        default_factory=list,
        description="Ordered list of concrete objectives to pursue.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the classification (0.0–1.0).",
    )


# ---------------------------------------------------------------------------
# Idea models
# ---------------------------------------------------------------------------


class Difficulty(str, Enum):
    """Difficulty classification for an idea."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Idea(BaseModel):
    """A structured idea produced by the idea engine."""

    idea_id: str = Field(description="Unique identifier for the idea.")
    title: str = Field(description="Short, descriptive title.")
    problem: str = Field(description="Problem the idea solves.")
    target_user: str = Field(description="Who this idea serves.")
    monetization_path: str = Field(description="How this idea generates revenue.")
    difficulty: Difficulty = Field(description="Estimated implementation difficulty.")
    time_to_launch: str = Field(
        description="Estimated time to reach an MVP (e.g. '2 weeks', '3 months').",
    )
    summary: str = Field(description="Brief summary of the idea.")


# ---------------------------------------------------------------------------
# Evaluation models
# ---------------------------------------------------------------------------


class EvaluationScores(BaseModel):
    """Numeric scores assigned to an idea across strategic criteria."""

    demand: float = Field(ge=0.0, le=1.0, description="Estimated market demand signal.")
    monetization_clarity: float = Field(
        ge=0.0,
        le=1.0,
        description="Clarity and viability of the monetization path.",
    )
    speed_to_mvp: float = Field(ge=0.0, le=1.0, description="Expected speed to MVP.")
    competition: float = Field(
        ge=0.0,
        le=1.0,
        description="Competitive advantage (higher = less competition).",
    )
    execution_simplicity: float = Field(
        ge=0.0,
        le=1.0,
        description="How simple execution is for a lean team.",
    )
    scalability: float = Field(
        ge=0.0,
        le=1.0,
        description="Potential to scale distribution and revenue.",
    )
    founder_fit: float = Field(
        ge=0.0,
        le=1.0,
        description="Estimated fit with builder constraints and capabilities.",
    )
    risk: float = Field(
        ge=0.0,
        le=1.0,
        description="Inverse risk score (higher means lower risk).",
    )
    # Legacy compatibility fields retained for existing API/tests.
    feasibility: float = Field(ge=0.0, le=1.0, description="Legacy feasibility score.")
    profitability: float = Field(ge=0.0, le=1.0, description="Legacy profitability score.")
    speed: float = Field(ge=0.0, le=1.0, description="Legacy speed score.")


class DecisionAction(str, Enum):
    """Canonical strategic action classes used across reasoning outputs."""

    APPROVE = "approve"
    REJECT = "reject"
    PARK = "park"


class EvaluationDecision(BaseModel):
    """Business-oriented decision packet derived from weighted scoring."""

    verdict: str = Field(description="High-level verdict string.")
    why_now: str = Field(description="Why this idea should be acted on now.")
    main_risk: str = Field(description="Primary risk requiring mitigation.")
    recommended_next_move: str = Field(
        description="Single most important next move.",
    )
    action: DecisionAction = Field(
        description="Action classification: approve/reject/park.",
    )


class EvaluationResult(BaseModel):
    """Full evaluation output for a single idea."""

    idea_id: str = Field(description="ID of the evaluated idea.")
    scores: EvaluationScores = Field(description="Individual criterion scores.")
    aggregate: float = Field(
        ge=0.0,
        le=1.0,
        description="Weighted aggregate score.",
    )
    recommendation: str = Field(
        description="Short recommendation based on the scores.",
    )
    decision: EvaluationDecision = Field(
        description="Structured decision packet derived from score profile.",
    )


# ---------------------------------------------------------------------------
# Critique models
# ---------------------------------------------------------------------------


class RiskSeverity(str, Enum):
    """Severity level for an identified risk."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Risk(BaseModel):
    """A single identified risk."""

    description: str = Field(description="What the risk is.")
    severity: RiskSeverity = Field(description="How severe the risk is.")
    mitigation: str = Field(description="Suggested way to mitigate the risk.")


class CritiqueResult(BaseModel):
    """Full critique output for a proposal or idea."""

    weaknesses: list[str] = Field(
        default_factory=list,
        description="Identified weaknesses in the proposal.",
    )
    assumptions_challenged: list[str] = Field(
        default_factory=list,
        description="Assumptions that may not hold.",
    )
    risks: list[Risk] = Field(
        default_factory=list,
        description="Identified risks with severity and mitigation.",
    )
    improvements: list[str] = Field(
        default_factory=list,
        description="Suggested improvements.",
    )
    verdict: str = Field(
        description="Overall verdict: proceed, revise, or reject.",
    )
    weak_monetization: bool = Field(
        default=False,
        description="True when monetization logic appears weak or underspecified.",
    )
    complexity_alert: bool = Field(
        default=False,
        description="True when execution complexity is likely too high.",
    )
    pivot_direction: str | None = Field(
        default=None,
        description="Suggested pivot direction when the current framing is weak.",
    )


# ---------------------------------------------------------------------------
# Founder response models
# ---------------------------------------------------------------------------


class ScoreOutput(BaseModel):
    """Structured evaluation scores returned in the pipeline response."""

    demand: float = Field(
        ge=0.0, le=1.0, description="Estimated market demand signal.",
    )
    monetization_clarity: float = Field(
        ge=0.0, le=1.0, description="Clarity and viability of monetization model.",
    )
    speed_to_mvp: float = Field(
        ge=0.0, le=1.0, description="Expected speed to MVP.",
    )
    competition: float = Field(
        ge=0.0, le=1.0, description="Competitive advantage (higher = less competition).",
    )
    execution_simplicity: float = Field(
        ge=0.0, le=1.0, description="Execution simplicity for a lean builder.",
    )
    scalability: float = Field(
        ge=0.0, le=1.0, description="Potential to scale distribution and revenue.",
    )
    founder_fit: float = Field(
        ge=0.0, le=1.0, description="Fit with founder/operator constraints.",
    )
    risk: float = Field(
        ge=0.0, le=1.0, description="Inverse risk score (higher is safer).",
    )
    feasibility: float = Field(
        ge=0.0, le=1.0, description="Legacy technical feasibility.",
    )
    profitability: float = Field(
        ge=0.0, le=1.0, description="Legacy revenue potential.",
    )
    speed: float = Field(
        ge=0.0, le=1.0, description="Legacy speed to market.",
    )
    aggregate: float = Field(
        ge=0.0, le=1.0, description="Weighted aggregate score.",
    )


class CommandOutput(BaseModel):
    """A structured command emitted as part of the founder response."""

    action: str = Field(description="The action to execute.")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters.",
    )
    priority: str = Field(
        default="medium",
        description="Execution priority (low, medium, high).",
    )


class DecisionOutput(BaseModel):
    """Structured business decision packet for UI-friendly display."""

    verdict: str = Field(description="Immediate strategic verdict for this idea.")
    why_now: str = Field(description="Concise reason this should be acted on now.")
    main_risk: str = Field(description="Primary risk requiring active mitigation.")
    recommended_next_move: str = Field(description="Single highest-impact next move.")
    decision: DecisionAction = Field(description="One of: approve, reject, or park.")
    action: DecisionAction | None = Field(
        default=None,
        description="Compatibility alias for `decision`.",
    )

    @model_validator(mode="after")
    def _sync_action_alias(self) -> "DecisionOutput":
        """Keep `action` in sync with canonical `decision`."""
        if self.action is None:
            self.action = self.decision
        return self


class PortfolioComparison(BaseModel):
    """Comparison of a candidate idea against current portfolio projects."""

    compared_projects: int = Field(description="Number of projects compared.")
    closest_project_id: str | None = Field(
        default=None,
        description="Project ID with highest overlap, if any.",
    )
    closest_project_name: str | None = Field(
        default=None,
        description="Project name with highest overlap, if any.",
    )
    overlap_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Semantic-lite overlap score with closest project.",
    )
    differentiation_summary: str = Field(
        description="Human-readable summary of overlap and differentiation.",
    )
    recommendation: str = Field(
        description="Portfolio-level recommendation based on overlap.",
    )
    # Legacy compatibility fields for callers/tests created before schema upgrade.
    overlapping_projects: list[str] = Field(
        default_factory=list,
        description="Names of projects with notable overlap.",
    )
    relative_rank: str = Field(
        default="top_candidate",
        description="Legacy rank classification used by older route consumers.",
    )
    summary: str = Field(
        default="No direct overlap detected.",
        description="Legacy short summary kept for backward compatibility.",
    )


class PortfolioComparisonEntry(BaseModel):
    """Single portfolio project overlap entry used for ranking comparisons."""

    project_id: str = Field(description="Compared project identifier.")
    project_name: str = Field(description="Compared project name.")
    overlap_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Estimated overlap score between idea and project.",
    )
    overlap_reasons: list[str] = Field(
        default_factory=list,
        description="Short reasons explaining overlap score.",
    )
    # Compatibility fields for previous compare API shape.
    candidate_idea_id: str | None = None
    existing_idea_id: str | None = None
    candidate_score: float | None = None
    existing_score: float | None = None
    score_delta: float | None = None
    recommendation: str | None = None


class FounderResponse(BaseModel):
    """Full structured response for a founder-to-command flow turn.

    Includes strategic analysis, optional evaluation/critique output,
    and any commands that should be dispatched next.
    """

    summary: str = Field(
        description="High-level summary of the analysis.",
    )
    decision: str = Field(
        description="The strategic decision or recommendation.",
    )
    score: ScoreOutput | None = Field(
        default=None,
        description="Structured evaluation scores when applicable.",
    )
    risks: list[Risk] = Field(
        default_factory=list,
        description="Identified risks with severity and mitigation.",
    )
    suggested_next_action: str = Field(
        description="The single most important next step.",
    )
    commands: list[CommandOutput] = Field(
        default_factory=list,
        description="Structured commands to dispatch.",
    )
    strategy: StrategicDirection = Field(
        description="Underlying strategic direction that drove the response.",
    )
    decision_output: DecisionOutput | None = Field(
        default=None,
        description="Structured decision packet for UI and automation surfaces.",
    )
    portfolio_comparison: PortfolioComparison | None = Field(
        default=None,
        description="Candidate-vs-portfolio comparison data.",
    )


# ---------------------------------------------------------------------------
# Registry / persistence models
# ---------------------------------------------------------------------------


class ProjectStatus(str, Enum):
    """Lifecycle status of a project in the registry."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectRecord(BaseModel):
    """Persisted project record returned by the registry."""

    project_id: str = Field(description="Registry-assigned project identifier.")
    name: str = Field(description="Unique project name.")
    description: str = Field(description="Short description of the project.")
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE,
        description="Current lifecycle status.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional additional metadata (tags, owner, etc.).",
    )
    created_at: str = Field(description="ISO-8601 creation timestamp.")
    updated_at: str = Field(description="ISO-8601 last-update timestamp.")
    stub: bool = Field(
        default=True,
        description="True while the record is served from stub storage.",
    )


class IdeaRecord(BaseModel):
    """Persisted idea record returned by the registry."""

    record_id: str = Field(description="Registry-assigned record identifier.")
    idea: dict[str, Any] = Field(description="Serialised idea payload.")
    project_id: str | None = Field(
        default=None,
        description="Optional project this idea belongs to.",
    )
    created_at: str = Field(description="ISO-8601 creation timestamp.")
    stub: bool = Field(
        default=True,
        description="True while the record is served from stub storage.",
    )


class CommandRecord(BaseModel):
    """Persisted command record returned by the registry."""

    record_id: str = Field(description="Registry-assigned record identifier.")
    command_type: str = Field(description="Type of command dispatched.")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Command-specific parameters.",
    )
    project_id: str | None = Field(
        default=None,
        description="Optional project this command belongs to.",
    )
    status: str = Field(
        default="pending",
        description="Current command status (pending, running, completed, failed).",
    )
    created_at: str = Field(description="ISO-8601 creation timestamp.")
    stub: bool = Field(
        default=True,
        description="True while the record is served from stub storage.",
    )
