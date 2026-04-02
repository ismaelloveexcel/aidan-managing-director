"""
models.py – Pydantic models for the AI-DAN reasoning layer.

Defines structured, typed data models used across strategist, idea engine,
evaluator, and critic modules.
"""

from enum import Enum

from pydantic import BaseModel, Field


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
    """Numeric scores assigned to an idea across standard criteria."""

    feasibility: float = Field(ge=0.0, le=1.0, description="Technical feasibility.")
    profitability: float = Field(ge=0.0, le=1.0, description="Revenue potential.")
    speed: float = Field(ge=0.0, le=1.0, description="Speed to market.")
    competition: float = Field(
        ge=0.0,
        le=1.0,
        description="Competitive advantage (higher = less competition).",
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
