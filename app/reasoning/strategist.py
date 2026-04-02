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
    CommandOutput,
    FounderResponse,
    IntentType,
    Risk,
    RiskSeverity,
    StrategicDirection,
)

# ---------------------------------------------------------------------------
# Intent keyword mapping – deterministic classification
# ---------------------------------------------------------------------------
_INTENT_KEYWORDS: dict[IntentType, list[str]] = {
    IntentType.BUILD: [
        "build", "create", "launch", "ship", "develop", "make", "start",
        "implement", "deploy", "new project", "new product",
    ],
    IntentType.IMPROVE: [
        "improve", "optimise", "optimize", "refactor", "upgrade", "fix",
        "enhance", "iterate", "polish", "better",
    ],
    IntentType.EXPLORE: [
        "explore", "research", "investigate", "analyse", "analyze",
        "discover", "study", "look into", "brainstorm", "idea",
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


class Strategist:
    """Analyses context and user input to produce strategic directions.

    All logic is deterministic — no external API calls are made.
    """

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
        from app.planning.command_compiler import compile_commands
        from app.planning.planner import create_plan
        from app.reasoning.critic import Critic
        from app.reasoning.evaluator import Evaluator
        from app.reasoning.idea_engine import IdeaEngine

        ctx: dict[str, Any] = dict(context) if context else {}
        ctx.setdefault("message", message)

        direction = self.analyse(ctx)

        # Route to the correct reasoning pipeline based on intent.
        if direction.intent in (IntentType.BUILD, IntentType.EXPLORE):
            return self._flow_generate(
                message, direction, IdeaEngine(), Evaluator(), Critic(),
                create_plan, compile_commands,
            )

        if direction.intent == IntentType.IMPROVE:
            return self._flow_improve(message, direction)

        if direction.intent == IntentType.MONETISE:
            return self._flow_monetise(message, direction)

        if direction.intent == IntentType.PIVOT:
            return self._flow_pivot(message, direction)

        # UNKNOWN – ask for clarification.
        return FounderResponse(
            summary="Unable to determine intent from the provided message.",
            decision="Request clarification before proceeding.",
            suggested_next_action="Rephrase your request with more detail.",
            strategy=direction,
        )

    # ------------------------------------------------------------------
    # Flow implementations (private)
    # ------------------------------------------------------------------

    @staticmethod
    def _flow_generate(
        message: str,
        direction: StrategicDirection,
        idea_engine: Any,
        evaluator: Any,
        critic: Any,
        create_plan: Any,
        compile_commands: Any,
    ) -> FounderResponse:
        """Generate an idea, evaluate, critique, plan, and compile commands."""
        idea = idea_engine.generate(message)
        evaluation = evaluator.score(idea)
        critique = critic.critique(idea)

        plan = create_plan({
            "name": idea.title,
            "description": idea.summary,
            "target_user": idea.target_user,
            "monetization_path": idea.monetization_path,
            "difficulty": idea.difficulty.value,
            "time_to_launch": idea.time_to_launch,
        })

        raw_commands = compile_commands(plan)
        commands = [
            CommandOutput(
                action=cmd["action"],
                parameters=cmd.get("parameters", {}),
                priority=cmd.get("priority", "medium"),
            )
            for cmd in raw_commands
        ]

        decision = (
            f"Idea '{idea.title}' scored {evaluation.aggregate:.2f}. "
            f"Critic verdict: {critique.verdict}. "
            f"Recommendation: {evaluation.recommendation}"
        )

        suggested = (
            direction.objectives[0]
            if direction.objectives
            else "Define MVP scope"
        )

        return FounderResponse(
            summary=(
                f"Generated and evaluated idea: {idea.title}. "
                f"Difficulty: {idea.difficulty.value}, "
                f"time to launch: {idea.time_to_launch}."
            ),
            decision=decision,
            score=evaluation.aggregate,
            risks=critique.risks,
            suggested_next_action=suggested,
            commands=commands,
            strategy=direction,
        )

    @staticmethod
    def _flow_improve(
        message: str,
        direction: StrategicDirection,
    ) -> FounderResponse:
        """Handle improvement-oriented requests."""
        suggested = (
            direction.objectives[0]
            if direction.objectives
            else "Audit current performance"
        )

        return FounderResponse(
            summary="Analysed improvement request and identified key areas.",
            decision=(
                "Focus on targeted enhancements to existing assets. "
                "Prioritise quality and performance gains."
            ),
            risks=[
                Risk(
                    description="Scope creep during improvement cycles.",
                    severity=RiskSeverity.MEDIUM,
                    mitigation="Define clear acceptance criteria before starting.",
                ),
            ],
            suggested_next_action=suggested,
            commands=[
                CommandOutput(
                    action="setup_project",
                    parameters={"description": "Audit and improve existing project"},
                    priority="high",
                ),
            ],
            strategy=direction,
        )

    @staticmethod
    def _flow_monetise(
        message: str,
        direction: StrategicDirection,
    ) -> FounderResponse:
        """Handle monetisation-oriented requests."""
        suggested = (
            direction.objectives[0]
            if direction.objectives
            else "Identify monetisation levers"
        )

        return FounderResponse(
            summary="Analysed monetisation request and identified revenue opportunities.",
            decision=(
                "Activate revenue-generating strategies. "
                "Prioritise quick wins with proven models."
            ),
            risks=[
                Risk(
                    description="Premature monetisation may alienate early users.",
                    severity=RiskSeverity.MEDIUM,
                    mitigation="Validate willingness-to-pay before hard paywalls.",
                ),
            ],
            suggested_next_action=suggested,
            commands=[
                CommandOutput(
                    action="setup_monetization",
                    parameters={"description": "Integrate revenue model"},
                    priority="high",
                ),
            ],
            strategy=direction,
        )

    @staticmethod
    def _flow_pivot(
        message: str,
        direction: StrategicDirection,
    ) -> FounderResponse:
        """Handle pivot-oriented requests."""
        suggested = (
            direction.objectives[0]
            if direction.objectives
            else "Diagnose current blockers"
        )

        return FounderResponse(
            summary="Analysed pivot request and evaluated strategic alternatives.",
            decision=(
                "Prepare for a strategic direction change. "
                "Evaluate alternatives before committing resources."
            ),
            risks=[
                Risk(
                    description="Pivoting too aggressively may waste prior investment.",
                    severity=RiskSeverity.HIGH,
                    mitigation="Conduct a structured pivot analysis before acting.",
                ),
            ],
            suggested_next_action=suggested,
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
