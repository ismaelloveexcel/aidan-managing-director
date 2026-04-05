"""
Repo discovery engine – discovers and scores external repos for template reuse.

Selection rules:
- score >= 70 → REUSE_EXTERNAL_TEMPLATE
- 40-69 → USE_INTERNAL_TEMPLATE
- <40 → BUILD_MINIMAL_INTERNAL

Filters:
- Reject archived repos
- Reject forks unless strong score
- Prefer: recent updates, low complexity, clear README

Output: repo_discovery.json structure with candidates and selection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SelectionMode(str, Enum):
    """Template selection modes based on discovery score."""

    REUSE_EXTERNAL = "reuse_external_template"
    USE_INTERNAL = "use_internal_template"
    BUILD_MINIMAL = "build_minimal_internal"


class RepoCandidate(BaseModel):
    """A candidate repository from discovery."""

    repo_name: str
    repo_url: str = ""
    description: str = ""
    stars: int = 0
    last_updated: str = ""
    is_archived: bool = False
    is_fork: bool = False
    has_readme: bool = True
    language: str = ""
    license: str = ""
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    rejection_reason: str = ""


class RepoDiscoveryResult(BaseModel):
    """Complete repo discovery output."""

    search_query: str
    candidates: list[RepoCandidate] = Field(default_factory=list)
    selected_repo: str = ""
    selection_mode: SelectionMode = SelectionMode.BUILD_MINIMAL
    selection_reason: str = ""
    discovered_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


def score_candidate(candidate: RepoCandidate) -> RepoCandidate:
    """Score a repo candidate on multiple factors (0-100).

    Scoring factors:
    - Stars (0-20): popularity signal
    - Recency (0-20): recent updates preferred
    - README (0-15): documentation quality
    - Not archived (0-15): must be active
    - Not fork (0-10): original work preferred
    - License (0-10): open-source friendly
    - Language match (0-10): relevant tech stack
    """
    breakdown: dict[str, float] = {}

    # Stars score (0-20)
    if candidate.stars >= 1000:
        breakdown["stars"] = 20.0
    elif candidate.stars >= 100:
        breakdown["stars"] = 15.0
    elif candidate.stars >= 10:
        breakdown["stars"] = 10.0
    elif candidate.stars >= 1:
        breakdown["stars"] = 5.0
    else:
        breakdown["stars"] = 0.0

    # Recency score (0-20)
    if candidate.last_updated:
        try:
            updated = datetime.fromisoformat(
                candidate.last_updated.replace("Z", "+00:00"),
            )
            now = datetime.now(timezone.utc)
            days_ago = (now - updated).days
            if days_ago <= 30:
                breakdown["recency"] = 20.0
            elif days_ago <= 90:
                breakdown["recency"] = 15.0
            elif days_ago <= 365:
                breakdown["recency"] = 10.0
            else:
                breakdown["recency"] = 0.0
        except (ValueError, TypeError):
            breakdown["recency"] = 5.0
    else:
        breakdown["recency"] = 5.0

    # README score (0-15)
    breakdown["readme"] = 15.0 if candidate.has_readme else 0.0

    # Archived penalty (0-15)
    if candidate.is_archived:
        breakdown["active"] = 0.0
        candidate.rejection_reason = "Repository is archived."
    else:
        breakdown["active"] = 15.0

    # Fork penalty (0-10)
    breakdown["original"] = 0.0 if candidate.is_fork else 10.0

    # License score (0-10)
    open_licenses = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "unlicense"}
    breakdown["license"] = (
        10.0 if candidate.license.lower() in open_licenses else 5.0
    )

    # Language relevance (0-10)
    relevant_langs = {"python", "typescript", "javascript", "go", "rust"}
    breakdown["language"] = (
        10.0 if candidate.language.lower() in relevant_langs else 5.0
    )

    total = sum(breakdown.values())
    candidate.score = min(total, 100.0)
    candidate.score_breakdown = breakdown

    return candidate


def select_template(
    candidates: list[RepoCandidate],
) -> tuple[str, SelectionMode, str]:
    """Select the best template based on scored candidates.

    Args:
        candidates: List of scored RepoCandidate objects.

    Returns:
        Tuple of (selected_repo_name, selection_mode, reason).
    """
    # Filter out archived repos
    valid = [c for c in candidates if not c.is_archived]

    # Filter out forks unless score >= 70
    valid = [c for c in valid if not c.is_fork or c.score >= 70]

    if not valid:
        return (
            "",
            SelectionMode.BUILD_MINIMAL,
            "No suitable external templates found. Building minimal internal.",
        )

    # Sort by score descending
    valid.sort(key=lambda c: c.score, reverse=True)
    best = valid[0]

    if best.score >= 70:
        return (
            best.repo_name,
            SelectionMode.REUSE_EXTERNAL,
            f"High-scoring template ({best.score:.0f}/100): {best.repo_name}",
        )
    if best.score >= 40:
        return (
            best.repo_name,
            SelectionMode.USE_INTERNAL,
            f"Moderate match ({best.score:.0f}/100): using internal template with reference to {best.repo_name}",
        )

    return (
        "",
        SelectionMode.BUILD_MINIMAL,
        f"Best candidate scored only {best.score:.0f}/100. Building minimal internal.",
    )


def discover_repos(
    *,
    search_query: str,
    candidates_data: list[dict[str, Any]] | None = None,
) -> RepoDiscoveryResult:
    """Run repo discovery and selection.

    Args:
        search_query: The search query used for discovery.
        candidates_data: Optional pre-fetched candidate data (list of dicts).
            If not provided, returns empty result (external search needed).

    Returns:
        RepoDiscoveryResult with scored candidates and selection.
    """
    candidates: list[RepoCandidate] = []

    if candidates_data:
        for data in candidates_data:
            candidate = RepoCandidate(
                repo_name=str(data.get("name", data.get("repo_name", ""))),
                repo_url=str(data.get("url", data.get("repo_url", ""))),
                description=str(data.get("description", "")),
                stars=int(data.get("stars", data.get("stargazers_count", 0))),
                last_updated=str(data.get("updated_at", data.get("last_updated", ""))),
                is_archived=bool(data.get("archived", data.get("is_archived", False))),
                is_fork=bool(data.get("fork", data.get("is_fork", False))),
                has_readme=bool(data.get("has_readme", True)),
                language=str(data.get("language", "")),
                license=str(
                    data.get("license", {}).get("spdx_id", "")
                    if isinstance(data.get("license"), dict)
                    else data.get("license", "")
                ),
            )
            score_candidate(candidate)
            candidates.append(candidate)

    # Sort by score
    candidates.sort(key=lambda c: c.score, reverse=True)

    # Select best template
    selected_repo, selection_mode, selection_reason = select_template(candidates)

    return RepoDiscoveryResult(
        search_query=search_query,
        candidates=candidates,
        selected_repo=selected_repo,
        selection_mode=selection_mode,
        selection_reason=selection_reason,
    )
