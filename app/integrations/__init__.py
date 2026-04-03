"""
integrations – External-service clients for AI-DAN.

Re-exports the three integration clients so that callers can import
directly from the package::

    from app.integrations import GitHubClient, LLMClient, RegistryClient
"""

from app.integrations.github_client import (
    GitHubClient,
    IssueBundleRequest,
    IssueSpec,
    RepoRequest,
    RepoStatus,
)
from app.integrations.llm_client import LLMClient
from app.integrations.registry_client import RegistryClient

__all__ = [
    "GitHubClient",
    "IssueBundleRequest",
    "IssueSpec",
    "LLMClient",
    "RegistryClient",
    "RepoRequest",
    "RepoStatus",
]
