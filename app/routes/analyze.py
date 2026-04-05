"""
Unified analyze route – single endpoint for the full idea-to-decision pipeline.

POST /api/analyze/
- Runs validation gate
- Runs revenue scoring
- Generates offer
- Generates distribution plan
- Returns complete analysis

POST /api/analyze/enhanced
- Same pipeline but uses LLM-augmented scoring for ambiguous score ranges.

This is the primary endpoint for the UI form.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import get_ai_provider
from app.feedback.analytics_tracker import AnalyticsTracker
from app.planning.distribution_engine import generate_distribution
from app.planning.offer_engine import generate_offer
from app.reasoning.llm_scoring import score_idea_with_llm
from app.reasoning.scoring_engine import RevenueScore, ScoringDecision, score_idea
from app.reasoning.validate_business_gate import GateDecision, validate_business_gate

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request body for idea analysis."""

    idea: str = Field(..., min_length=1, description="The idea to analyze")
    problem: str = ""
    target_user: str = ""
    monetization_model: str = ""
    competition_level: str = ""
    difficulty: str = ""
    time_to_revenue: str = ""
    differentiation: str = ""


class AnalyzeResponse(BaseModel):
    """Complete analysis response."""

    # Validation gate
    validation_passed: bool
    validation_reasons: list[str] = Field(default_factory=list)
    validation_blocking: list[str] = Field(default_factory=list)

    # Revenue scoring
    total_score: float = 0.0
    score_decision: str = ""
    score_decision_reason: str = ""
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    score_dimensions: list[dict[str, Any]] = Field(default_factory=list)

    # Offer
    offer: dict[str, Any] = Field(default_factory=dict)

    # Distribution
    distribution: dict[str, Any] = Field(default_factory=dict)

    # Final decision
    final_decision: str = ""
    next_step: str = ""
    pipeline_stage: str = ""


# Shared analytics tracker instance
_tracker = AnalyticsTracker()


def _extract_fields(idea_text: str) -> dict[str, str]:
    """Attempt to extract structured fields from free-form idea text."""
    lower = idea_text.lower()
    extracted: dict[str, str] = {}

    # Try to detect target user
    for marker in ("for ", "targeting ", "aimed at "):
        idx = lower.find(marker)
        if idx != -1:
            end = lower.find(".", idx)
            if end == -1:
                end = min(idx + 80, len(idea_text))
            extracted["target_user"] = idea_text[idx + len(marker):end].strip()
            break

    # Try to detect problem
    for marker in ("problem:", "solving ", "fix ", "addresses "):
        idx = lower.find(marker)
        if idx != -1:
            end = lower.find(".", idx)
            if end == -1:
                end = min(idx + 100, len(idea_text))
            extracted["problem"] = idea_text[idx + len(marker):end].strip()
            break

    return extracted


# Type alias for the scoring callable accepted by _run_pipeline.
_ScoringFn = Callable[..., RevenueScore]


def _run_pipeline(request: AnalyzeRequest, scoring_fn: _ScoringFn) -> AnalyzeResponse:
    """Execute the full idea-analysis pipeline with a caller-supplied scoring function.

    Steps:
    1. Validate business gate (demand, monetization, saturation)
    2. Score on 5 revenue dimensions using ``scoring_fn`` (0-10)
    3. Generate structured offer
    4. Generate distribution plan
    5. Return unified decision

    Args:
        request: AnalyzeRequest with idea and optional structured fields.
        scoring_fn: Callable matching ``score_idea``'s keyword signature.

    Returns:
        AnalyzeResponse with complete analysis.
    """
    idea_text = request.idea.strip()

    # Auto-extract fields from free-form text if not provided
    extracted = _extract_fields(idea_text)
    problem = request.problem or extracted.get("problem", "")
    target_user = request.target_user or extracted.get("target_user", "")

    # If still no problem, use the idea text itself as the problem statement
    if not problem:
        problem = idea_text
    # target_user left empty intentionally — the validation gate will
    # flag missing demand evidence when no explicit audience is given.

    # --- Step 1: Business Validation Gate ---
    validation = validate_business_gate(
        idea_text=idea_text,
        problem=problem,
        target_user=target_user,
        monetization_model=request.monetization_model,
        competition_level=request.competition_level,
        differentiation=request.differentiation,
    )

    if validation.decision == GateDecision.REJECT:
        return AnalyzeResponse(
            validation_passed=False,
            validation_reasons=validation.reasons,
            validation_blocking=validation.blocking_reasons,
            final_decision="REJECTED",
            next_step="Address blocking issues before resubmitting.",
            pipeline_stage="validation_failed",
        )

    # --- Step 2: Revenue Scoring (via supplied function) ---
    scoring = scoring_fn(
        idea_text=idea_text,
        problem=problem,
        target_user=target_user,
        monetization_model=request.monetization_model,
        competition_level=request.competition_level,
        difficulty=request.difficulty,
        time_to_revenue=request.time_to_revenue,
        differentiation=request.differentiation,
    )

    # --- Step 3: Generate Offer ---
    # Extract a short title from the idea
    title = idea_text.split(".")[0][:80] if idea_text else "Unnamed Idea"

    offer = generate_offer(
        title=title,
        problem=problem,
        target_user=target_user,
        monetization_model=request.monetization_model,
        solution=idea_text,
        idea_text=idea_text,
    )

    # --- Step 4: Generate Distribution ---
    distribution = generate_distribution(
        title=title,
        problem=problem,
        target_user=target_user,
        idea_text=idea_text,
    )

    # --- Step 5: Final Decision ---
    if scoring.decision == ScoringDecision.APPROVE:
        final_decision = "APPROVED"
        next_step = "Idea approved for build. Proceeding to queue."
        pipeline_stage = "approved"
    elif scoring.decision == ScoringDecision.HOLD:
        final_decision = "HOLD"
        next_step = "Score is moderate. Strengthen weak dimensions before proceeding."
        pipeline_stage = "scored_hold"
    else:
        final_decision = "REJECTED"
        next_step = "Score too low. Rethink approach or pivot."
        pipeline_stage = "scored_reject"

    return AnalyzeResponse(
        validation_passed=True,
        validation_reasons=validation.reasons,
        validation_blocking=[],
        total_score=scoring.total_score,
        score_decision=scoring.decision.value,
        score_decision_reason=scoring.decision_reason,
        score_breakdown=scoring.breakdown,
        score_dimensions=[d.model_dump() for d in scoring.dimensions],
        offer=offer.model_dump(),
        distribution=distribution.model_dump(),
        final_decision=final_decision,
        next_step=next_step,
        pipeline_stage=pipeline_stage,
    )


@router.post("/", response_model=AnalyzeResponse)
def analyze_idea(request: AnalyzeRequest) -> AnalyzeResponse:
    """Run the full idea analysis pipeline.

    Steps:
    1. Validate business gate (demand, monetization, saturation)
    2. Score on 5 revenue dimensions (0-10)
    3. Generate structured offer
    4. Generate distribution plan
    5. Return unified decision

    Args:
        request: AnalyzeRequest with idea and optional structured fields.

    Returns:
        AnalyzeResponse with complete analysis.
    """
    return _run_pipeline(request, scoring_fn=score_idea)


@router.post("/enhanced", response_model=AnalyzeResponse)
def analyze_idea_enhanced(request: AnalyzeRequest) -> AnalyzeResponse:
    """Run the full idea analysis pipeline with LLM-augmented scoring.

    Identical to ``POST /api/analyze/`` but uses ``score_idea_with_llm()``
    for the scoring step.  When the keyword score is in the ambiguous 4.0–7.0
    range and an OpenAI key is configured, the LLM re-evaluates each dimension
    for a more nuanced result.  Falls back to keyword scoring if the AI call
    fails or the provider is unconfigured.

    Args:
        request: AnalyzeRequest with idea and optional structured fields.

    Returns:
        AnalyzeResponse with complete analysis.
    """
    ai_provider = get_ai_provider()

    def _llm_scoring_fn(**kwargs: Any) -> RevenueScore:
        return score_idea_with_llm(**kwargs, ai_provider=ai_provider)

    return _run_pipeline(request, scoring_fn=_llm_scoring_fn)

