"""
idea_engine.py – Generative idea production for AI-DAN.

Produces structured :class:`Idea` instances using deterministic templates
and keyword extraction.  No external API calls are made.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.reasoning.models import Difficulty, Idea

# ---------------------------------------------------------------------------
# Idea templates – deterministic building blocks
# ---------------------------------------------------------------------------

_TEMPLATES: list[dict[str, Any]] = [
    {
        "title": "SaaS Dashboard for {domain}",
        "problem": "Users in the {domain} space lack a centralised analytics dashboard.",
        "target_user": "{domain} professionals and small-business owners",
        "monetization_path": "Monthly SaaS subscription ($29–$99/mo)",
        "difficulty": Difficulty.MEDIUM,
        "time_to_launch": "6 weeks",
    },
    {
        "title": "Marketplace for {domain} Services",
        "problem": "Finding quality {domain} service providers is fragmented and time-consuming.",
        "target_user": "Businesses seeking {domain} freelancers",
        "monetization_path": "Transaction fee (10–15 %) on completed jobs",
        "difficulty": Difficulty.HIGH,
        "time_to_launch": "3 months",
    },
    {
        "title": "AI-Powered {domain} Assistant",
        "problem": "Repetitive tasks in {domain} waste hours every week.",
        "target_user": "{domain} teams looking to automate workflows",
        "monetization_path": "Freemium model with premium AI features ($19/mo)",
        "difficulty": Difficulty.MEDIUM,
        "time_to_launch": "4 weeks",
    },
    {
        "title": "Open-Source {domain} Toolkit",
        "problem": "No cohesive open-source toolkit exists for common {domain} tasks.",
        "target_user": "Developers building {domain} applications",
        "monetization_path": "Paid support, hosted version, and enterprise add-ons",
        "difficulty": Difficulty.LOW,
        "time_to_launch": "2 weeks",
    },
    {
        "title": "{domain} Education Platform",
        "problem": "Accessible, hands-on {domain} education is hard to find.",
        "target_user": "Beginners and career changers entering {domain}",
        "monetization_path": "Course sales and certification fees",
        "difficulty": Difficulty.LOW,
        "time_to_launch": "3 weeks",
    },
]


class IdeaEngine:
    """Generates candidate :class:`Idea` objects using deterministic logic.

    Ideas are built by combining templates with a *domain* keyword
    extracted from the user's prompt.  No LLM calls are made.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> Idea:
        """Generate a single :class:`Idea` from *prompt* and optional *context*.

        The first matching template is selected based on prompt keywords.
        """
        domain = self._extract_domain(prompt, context)
        template = self._select_template(prompt)
        return self._build_idea(template, domain)

    def brainstorm(self, prompt: str, count: int = 5) -> list[Idea]:
        """Generate up to *count* :class:`Idea` instances for the given *prompt*."""
        count = max(1, min(count, len(_TEMPLATES)))
        domain = self._extract_domain(prompt)
        ideas: list[Idea] = []
        for template in _TEMPLATES[:count]:
            ideas.append(self._build_idea(template, domain))
        return ideas

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_domain(
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Extract a domain keyword from *prompt* or *context*.

        Falls back to ``"technology"`` when no meaningful keyword is found.
        """
        if context and "domain" in context:
            return str(context["domain"])

        # Use the longest capitalised word as a rough domain proxy.
        words = prompt.split()
        candidates = [w.strip(".,!?") for w in words if len(w) > 3]
        if candidates:
            return max(candidates, key=len).lower()
        return "technology"

    @staticmethod
    def _select_template(prompt: str) -> dict[str, Any]:
        """Pick the most relevant template for *prompt*.

        Uses a simple hash to deterministically map prompts to templates.
        """
        index = int(hashlib.sha256(prompt.encode()).hexdigest(), 16) % len(_TEMPLATES)
        return _TEMPLATES[index]

    @staticmethod
    def _build_idea(template: dict[str, Any], domain: str) -> Idea:
        """Instantiate an :class:`Idea` from a *template* and *domain*."""
        idea_id = hashlib.sha256(
            f"{template['title']}-{domain}".encode(),
        ).hexdigest()[:12]

        return Idea(
            idea_id=idea_id,
            title=str(template["title"]).format(domain=domain),
            problem=str(template["problem"]).format(domain=domain),
            target_user=str(template["target_user"]).format(domain=domain),
            monetization_path=str(template["monetization_path"]),
            difficulty=template["difficulty"],
            time_to_launch=str(template["time_to_launch"]),
            summary=f"A {template['difficulty'].value}-difficulty venture targeting "
            f"{domain} with an estimated launch in {template['time_to_launch']}.",
        )
