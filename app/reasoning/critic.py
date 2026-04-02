"""
critic.py – Adversarial critique of ideas and plans.

Challenges proposals by surfacing risks, weak assumptions, and
alternative perspectives.  All logic is deterministic.
"""

from __future__ import annotations

from app.reasoning.models import (
    CritiqueResult,
    Difficulty,
    Idea,
    Risk,
    RiskSeverity,
)


class Critic:
    """Reviews :class:`Idea` instances and produces structured critiques.

    No external API calls are made.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def critique(self, idea: Idea) -> CritiqueResult:
        """Produce a full :class:`CritiqueResult` for the given *idea*."""
        weaknesses = self._find_weaknesses(idea)
        assumptions = self._challenge_assumptions(idea)
        risks = self._identify_risks(idea)
        improvements = self._suggest_improvements(idea)
        verdict = self._render_verdict(weaknesses, risks)

        return CritiqueResult(
            weaknesses=weaknesses,
            assumptions_challenged=assumptions,
            risks=risks,
            improvements=improvements,
            verdict=verdict,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_weaknesses(idea: Idea) -> list[str]:
        """Identify potential weaknesses based on idea attributes."""
        weaknesses: list[str] = []

        if idea.difficulty == Difficulty.HIGH:
            weaknesses.append(
                "High difficulty increases the chance of delays and cost overruns.",
            )

        if "freemium" in idea.monetization_path.lower():
            weaknesses.append(
                "Freemium models often struggle with low conversion rates.",
            )

        if len(idea.problem) < 20:
            weaknesses.append(
                "The problem statement is vague — validate with real users.",
            )

        if "niche" not in idea.target_user.lower() and len(idea.target_user) < 20:
            weaknesses.append(
                "The target audience is broad — consider narrowing focus.",
            )

        return weaknesses

    @staticmethod
    def _challenge_assumptions(idea: Idea) -> list[str]:
        """Surface assumptions that may not hold."""
        assumptions: list[str] = []

        assumptions.append(
            f"Assumes the target user ({idea.target_user}) has an unmet need "
            "that they are willing to pay to solve.",
        )

        if "subscription" in idea.monetization_path.lower():
            assumptions.append(
                "Assumes recurring subscription value is high enough to "
                "justify ongoing payment from users.",
            )

        if idea.difficulty == Difficulty.LOW:
            assumptions.append(
                "Low-difficulty ideas may be easy for competitors to replicate.",
            )

        return assumptions

    @staticmethod
    def _identify_risks(idea: Idea) -> list[Risk]:
        """Identify and categorise risks."""
        risks: list[Risk] = []

        if idea.difficulty == Difficulty.HIGH:
            risks.append(
                Risk(
                    description="Technical complexity may exceed team capacity.",
                    severity=RiskSeverity.HIGH,
                    mitigation="Break the project into smaller milestones and validate early.",
                ),
            )

        if "marketplace" in idea.title.lower():
            risks.append(
                Risk(
                    description="Marketplaces face a chicken-and-egg problem (supply vs. demand).",
                    severity=RiskSeverity.HIGH,
                    mitigation="Seed one side of the marketplace manually before launch.",
                ),
            )

        if "fee" in idea.monetization_path.lower():
            risks.append(
                Risk(
                    description="Transaction-fee models depend on high volume to be profitable.",
                    severity=RiskSeverity.MEDIUM,
                    mitigation="Validate minimum viable volume before committing.",
                ),
            )

        # Generic risk present for all ideas.
        risks.append(
            Risk(
                description="Market timing may not be ideal.",
                severity=RiskSeverity.LOW,
                mitigation="Run a small demand-validation experiment before full build.",
            ),
        )

        return risks

    @staticmethod
    def _suggest_improvements(idea: Idea) -> list[str]:
        """Suggest concrete improvements to strengthen the idea."""
        improvements: list[str] = []

        improvements.append(
            "Conduct five customer-discovery interviews to validate the problem.",
        )

        if idea.difficulty != Difficulty.LOW:
            improvements.append(
                "Reduce scope to the smallest possible MVP to shorten time-to-launch.",
            )

        if "open-source" in idea.title.lower():
            improvements.append(
                "Define a clear community-engagement strategy to drive adoption.",
            )

        improvements.append(
            "Add a competitive analysis section before committing resources.",
        )

        return improvements

    @staticmethod
    def _render_verdict(weaknesses: list[str], risks: list[Risk]) -> str:
        """Produce a verdict string based on weakness and risk counts."""
        high_risks = sum(
            1 for r in risks if r.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
        )

        if high_risks >= 2 or len(weaknesses) >= 3:
            return "reject"
        if high_risks == 1 or len(weaknesses) >= 2:
            return "revise"
        return "proceed"
