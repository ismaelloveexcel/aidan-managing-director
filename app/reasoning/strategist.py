"""
strategist.py – High-level strategic reasoning for AI-DAN.

Responsible for interpreting user intent, synthesising context into
directional strategies, and prioritising objectives.  Also orchestrates
the full founder-to-command flow by routing to the appropriate reasoning
and planning modules.
"""

from __future__ import annotations

import re
from typing import Any

from app.reasoning.models import (
    CritiqueResult,
    CommandOutput,
    DecisionOutput,
    EvaluationResult,
    FounderResponse,
    Idea,
    IntentType,
    PortfolioComparison,
    RiskSeverity,
    ScoreOutput,
    StrategicDirection,
)

# ---------------------------------------------------------------------------
# Intent keyword mapping – deterministic classification
# ---------------------------------------------------------------------------
_INTENT_KEYWORDS: dict[IntentType, list[str]] = {
    IntentType.BUILD: [
        "build", "create", "launch", "ship", "develop", "make", "start",
        "implement", "deploy", "new project", "new product", "saas",
    ],
    IntentType.IMPROVE: [
        "improve", "optimise", "optimize", "refactor", "upgrade", "fix",
        "enhance", "iterate", "polish", "better",
    ],
    IntentType.EXPLORE: [
        "explore", "research", "investigate", "analyse", "analyze",
        "discover", "study", "look into", "brainstorm", "idea", "ideas",
        "evaluate",
    ],
    IntentType.MONETISE: [
        "monetise", "monetize", "revenue", "profit", "sell", "pricing",
        "subscription", "charge", "income", "earn",
    ],
    IntentType.PIVOT: [
        "pivot", "change direction", "rethink", "reposition", "abandon",
        "switch", "restart", "new direction",
    ],
}

_INTENT_PRIORITIES: dict[IntentType, str] = {
    IntentType.BUILD: "execution",
    IntentType.IMPROVE: "quality",
    IntentType.EXPLORE: "discovery",
    IntentType.MONETISE: "revenue",
    IntentType.PIVOT: "adaptation",
    IntentType.UNKNOWN: "clarification",
}

_INTENT_DIRECTIONS: dict[IntentType, str] = {
    IntentType.BUILD: "Focus resources on building and shipping a viable product.",
    IntentType.IMPROVE: "Iterate on existing assets to raise quality and performance.",
    IntentType.EXPLORE: "Investigate opportunity spaces before committing resources.",
    IntentType.MONETISE: "Identify and activate revenue-generating strategies.",
    IntentType.PIVOT: "Re-evaluate current direction and prepare for a strategic shift.",
    IntentType.UNKNOWN: "Gather more information before deciding on a direction.",
}

_RISK_SEVERITY_RANK: dict[RiskSeverity, int] = {
    RiskSeverity.LOW: 1,
    RiskSeverity.MEDIUM: 2,
    RiskSeverity.HIGH: 3,
    RiskSeverity.CRITICAL: 4,
}


class Strategist:
    """Analyses context and user input to produce strategic directions.

    All logic is deterministic — no external API calls are made.
    """

    def __init__(self) -> None:
        from app.reasoning.critic import Critic
        from app.reasoning.evaluator import Evaluator
        from app.reasoning.idea_engine import IdeaEngine

        self._idea_engine = IdeaEngine()
        self._evaluator = Evaluator()
        self._critic = Critic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(self, context: dict[str, object]) -> StrategicDirection:
        """Analyse *context* and return a :class:`StrategicDirection`.

        The context dictionary should contain at least a ``"message"`` key
        with the raw user input.  Additional keys (e.g. ``"portfolio"``,
        ``"goals"``) are used to refine the analysis when present.
        """
        message: str = str(context.get("message", ""))
        raw_goals = context.get("goals", [])
        if isinstance(raw_goals, str):
            goals: list[str] = [raw_goals]
        elif isinstance(raw_goals, list):
            goals = [str(g) for g in raw_goals]
        elif not raw_goals:
            goals = []
        else:
            goals = [str(raw_goals)]

        intent, confidence = self._classify_intent(message)
        objectives = self._derive_objectives(intent, message, goals)

        return StrategicDirection(
            intent=intent,
            priority=_INTENT_PRIORITIES[intent],
            direction=_INTENT_DIRECTIONS[intent],
            objectives=objectives,
            confidence=confidence,
        )

    def prioritise(self, objectives: list[str]) -> list[str]:
        """Return *objectives* ordered by strategic priority.

        Heuristic: shorter, more actionable objectives are ranked higher.
        Ties are broken by original order.
        """
        if not objectives:
            return []
        return sorted(objectives, key=lambda o: len(o))

    def process_founder_input(
        self,
        message: str,
        context: dict[str, object] | None = None,
    ) -> FounderResponse:
        """Run the full founder-to-command flow for a single message.

        1. Classify intent via :meth:`analyse`.
        2. Route to the appropriate reasoning modules (idea engine,
           evaluator, critic) based on the detected intent.
        3. Build a plan and compile commands when actionable.
        4. Return a structured :class:`FounderResponse`.

        Args:
            message: The raw founder message.
            context: Optional additional context (goals, portfolio, etc.).

        Returns:
            A fully populated :class:`FounderResponse`.
        """
        ctx: dict[str, Any] = dict(context) if context else {}
        ctx["message"] = message

        direction = self.analyse(ctx)
        if direction.intent == IntentType.UNKNOWN:
            return self._build_clarification_response(direction)
        return self._run_actionable_pipeline(message, direction, ctx)

    # ------------------------------------------------------------------
    # Flow implementations (private)
    # ------------------------------------------------------------------

    def _run_actionable_pipeline(
        self,
        message: str,
        direction: StrategicDirection,
        context: dict[str, Any],
    ) -> FounderResponse:
        """Run the actionable founder flow with explicit stage orchestration."""
        from app.planning.command_compiler import compile_command_models
        from app.planning.planner import IdeaPlanInput, create_plan_model

        idea, evaluation, critique = self._run_reasoning_sequence(
            message=message,
            context=context,
        )

        plan = create_plan_model(
            IdeaPlanInput(
                name=idea.title,
                description=idea.summary,
                target_user=idea.target_user,
                monetization_path=idea.monetization_path,
                difficulty=idea.difficulty.value,
                time_to_launch=idea.time_to_launch,
            ),
        )

        command_models = compile_command_models(plan.model_dump())
        commands = [CommandOutput(**cmd.model_dump()) for cmd in command_models]

        score = ScoreOutput(
            total_score=evaluation.total_score,
            breakdown=evaluation.breakdown,
            decision=evaluation.decision,
            reason=evaluation.reason,
        )

        comparison = self._compare_against_portfolio(idea, context)

        decision_output = DecisionOutput(
            verdict=evaluation.decision.value,
            why_now=f"Deterministic AI-DAN total score: {evaluation.total_score}/10.",
            main_risk="Market/monetization risk still needs active monitoring after launch.",
            recommended_next_move=(
                "Proceed to business package generation and strict operator-capacity check."
                if evaluation.decision.value == "APPROVE"
                else "Do not build yet; improve weak scoring dimensions first."
            ),
            decision=evaluation.decision,
            action=evaluation.decision,
        )

        return FounderResponse(
            summary=self._build_summary(idea, evaluation, direction),
            decision=self._build_decision(evaluation, critique, decision_output),
            decision_output=decision_output,
            score=score,
            risks=critique.risks,
            suggested_next_action=self._build_suggested_action(
                direction=direction,
                critique=critique,
                commands=commands,
            ),
            commands=commands,
            portfolio_comparison=comparison,
            strategy=direction,
        )

    def _run_reasoning_sequence(
        self,
        *,
        message: str,
        context: dict[str, Any],
    ) -> tuple[Idea, EvaluationResult, CritiqueResult]:
        """Run reasoning modules in strict sequence: idea → evaluation → critique."""
        idea = self._idea_engine.generate(message, context=context)
        evaluation = self._evaluator.score(idea)
        critique = self._critic.critique(idea)
        return idea, evaluation, critique

    @staticmethod
    def _build_summary(
        idea: Idea,
        evaluation: EvaluationResult,
        direction: StrategicDirection,
    ) -> str:
        """Render a concise founder-friendly summary."""
        return (
            f"AI-DAN generated '{idea.title}' for {idea.target_user}. "
            f"Intent '{direction.intent.value}' scored {evaluation.total_score}/10."
        )

    @staticmethod
    def _build_decision(
        evaluation: EvaluationResult,
        critique: CritiqueResult,
        decision_output: DecisionOutput,
    ) -> str:
        """Render a clear decision statement from evaluator + critic + decision outputs."""
        if critique.verdict == "reject":
            prefix = "Do not execute yet."
        elif critique.verdict == "revise":
            prefix = "Proceed only after targeted revisions."
        else:
            prefix = "Proceed with scoped execution."
        return (
            f"{prefix} Critic verdict: {critique.verdict}. "
            f"Decision: {decision_output.verdict}. "
            f"Why now: {decision_output.why_now}"
        )

    @staticmethod
    def _build_suggested_action(
        *,
        direction: StrategicDirection,
        critique: CritiqueResult,
        commands: list[CommandOutput],
    ) -> str:
        """Pick the highest-value single next action for the founder."""
        if critique.verdict in {"reject", "revise"} and critique.risks:
            highest_risk = max(
                critique.risks,
                key=lambda risk: _RISK_SEVERITY_RANK[risk.severity],
            )
            return highest_risk.mitigation

        if direction.objectives:
            return direction.objectives[0]

        if commands:
            return f"Queue command '{commands[0].action}' for execution."

        return "Define MVP scope and run a quick demand test."

    @staticmethod
    def _build_clarification_response(direction: StrategicDirection) -> FounderResponse:
        """Return a deterministic response when intent cannot be classified."""
        return FounderResponse(
            summary="AI-DAN could not classify the request with enough confidence.",
            decision="Pause execution and request clarification.",
            suggested_next_action=(
                "Rephrase your request with a clear goal, target user, and desired outcome."
            ),
            strategy=direction,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_intent(self, message: str) -> tuple[IntentType, float]:
        """Return ``(IntentType, confidence)`` for a raw message string."""
        lower = message.lower()
        scores: dict[IntentType, int] = {}

        for intent, keywords in _INTENT_KEYWORDS.items():
            hits = 0
            for kw in keywords:
                # Multi-word phrases use substring match; single words use
                # word-boundary matching to avoid false positives (e.g.
                # "ship" should not match "membership").
                if " " in kw:
                    if kw in lower:
                        hits += 1
                else:
                    if re.search(rf"\b{re.escape(kw)}\b", lower):
                        hits += 1
            if hits:
                scores[intent] = hits

        if not scores:
            return IntentType.UNKNOWN, 0.0

        best_intent = max(scores, key=lambda k: scores[k])
        total_keywords = sum(len(v) for v in _INTENT_KEYWORDS.values())
        confidence = min(scores[best_intent] / max(total_keywords * 0.1, 1), 1.0)
        return best_intent, round(confidence, 2)

    @staticmethod
    def _derive_objectives(
        intent: IntentType,
        message: str,
        goals: list[str],
    ) -> list[str]:
        """Build a list of objectives from intent, message, and goals."""
        objectives: list[str] = []

        # Always include user-supplied goals first.
        objectives.extend(goals)

        # Add intent-specific default objectives.
        _defaults: dict[IntentType, list[str]] = {
            IntentType.BUILD: [
                "Define MVP scope",
                "Set up project repository",
                "Implement core features",
            ],
            IntentType.IMPROVE: [
                "Audit current performance",
                "Identify top improvement areas",
                "Implement targeted enhancements",
            ],
            IntentType.EXPLORE: [
                "Map opportunity landscape",
                "Shortlist promising directions",
                "Validate assumptions with data",
            ],
            IntentType.MONETISE: [
                "Identify monetisation levers",
                "Design pricing model",
                "Launch revenue experiment",
            ],
            IntentType.PIVOT: [
                "Diagnose current blockers",
                "Evaluate alternative directions",
                "Draft pivot plan",
            ],
            IntentType.UNKNOWN: [
                "Clarify user intent",
                "Gather additional context",
            ],
        }

        for obj in _defaults.get(intent, []):
            if obj not in objectives:
                objectives.append(obj)

        return objectives

    @staticmethod
    def _compare_against_portfolio(
        idea: Idea,
        context: dict[str, Any] | None,
    ) -> PortfolioComparison:
        """Compare current idea against simple portfolio context heuristics."""
        portfolio = []
        if context and isinstance(context.get("portfolio"), list):
            portfolio = [item for item in context["portfolio"] if isinstance(item, dict)]

        candidate_tokens = {
            token
            for token in f"{getattr(idea, 'title', '')} {getattr(idea, 'target_user', '')}".lower().split()
            if len(token) > 2
        }

        closest_project: dict[str, Any] | None = None
        highest_overlap = 0.0
        overlapping_projects: list[str] = []
        for project in portfolio:
            name = str(project.get("name", "")).strip()
            text = f"{project.get('name', '')} {project.get('description', '')}".lower()
            project_tokens = {token for token in text.split() if len(token) > 2}
            overlap = 0.0
            if candidate_tokens:
                overlap = round(
                    len(candidate_tokens.intersection(project_tokens)) / len(candidate_tokens),
                    2,
                )

            if overlap >= 0.35 and name:
                overlapping_projects.append(name)
            if overlap > highest_overlap:
                highest_overlap = overlap
                closest_project = project

        if highest_overlap >= 0.55:
            recommendation = "High overlap detected; prefer differentiation before build."
            relative_rank = "differentiation_required"
        elif highest_overlap >= 0.30:
            recommendation = "Moderate overlap; sharpen positioning and segment focus."
            relative_rank = "competitive_with_portfolio"
        else:
            recommendation = "Low overlap; candidate appears additive to current portfolio."
            relative_rank = "top_candidate"

        closest_name = None
        closest_id = None
        if closest_project:
            closest_name = str(closest_project.get("name", "")).strip() or None
            closest_id = str(
                closest_project.get("project_id")
                or closest_project.get("id")
                or "",
            ).strip() or None

        summary = (
            "No direct overlap detected."
            if not overlapping_projects
            else "Overlap detected with existing portfolio items; sharpen positioning."
        )

        return PortfolioComparison(
            compared_projects=len(portfolio),
            closest_project_id=closest_id,
            closest_project_name=closest_name,
            overlap_score=highest_overlap,
            differentiation_summary=summary,
            recommendation=recommendation,
            overlapping_projects=overlapping_projects,
            relative_rank=relative_rank,
            summary=summary,
        )
