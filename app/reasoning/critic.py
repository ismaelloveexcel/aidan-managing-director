"""
critic.py – Adversarial critique of ideas and plans.

Challenges proposals by surfacing risks, weak assumptions, and
alternative perspectives before plans are committed.
"""

from typing import Any


class Critic:
    """
    Reviews ideas and plans and surfaces potential weaknesses or risks.

    Business logic to be implemented in a future iteration.
    """

    def critique(self, proposal: dict[str, Any]) -> list[str]:
        """
        Produce a list of critical observations about a proposal.

        Args:
            proposal: The idea or plan to critique.

        Returns:
            A list of human-readable critique points.
        """
        raise NotImplementedError

    def identify_risks(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Identify and categorise risks associated with a proposal.

        Args:
            proposal: The idea or plan to assess for risk.

        Returns:
            A list of risk dictionaries, each containing a description
            and severity level.
        """
        raise NotImplementedError
