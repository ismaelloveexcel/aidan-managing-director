"""
strategist.py – High-level strategic reasoning for AI-DAN.

Responsible for interpreting user intent, synthesising context into
directional strategies, and prioritising objectives.
"""

from __future__ import annotations

import re

from app.reasoning.models import IntentType, StrategicDirection

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
