"""
evaluator.py – Objective scoring and evaluation of ideas and plans.

Scores candidate ideas or plans against configurable criteria such as
feasibility, strategic alignment, and estimated value.
"""

from typing import Any


class Evaluator:
    """
    Scores ideas and plans against defined evaluation criteria.

    Business logic to be implemented in a future iteration.
    """

    def score(self, item: dict[str, Any], criteria: list[str]) -> dict[str, float]:
        """
        Assign numeric scores to an item across a set of criteria.

        Args:
            item: The idea or plan to evaluate.
            criteria: List of criterion names to score against.

        Returns:
            A mapping of criterion name to score (0.0 – 1.0).
        """
        raise NotImplementedError

    def rank(self, items: list[dict[str, Any]], criteria: list[str]) -> list[dict[str, Any]]:
        """
        Rank a list of items by their aggregate evaluation scores.

        Args:
            items: Ideas or plans to rank.
            criteria: Criteria used for scoring each item.

        Returns:
            Items sorted from highest to lowest aggregate score.
        """
        raise NotImplementedError
