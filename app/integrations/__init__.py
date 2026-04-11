"""
integrations – External-service clients for AI-DAN.

Re-exports the integration clients so that callers can import
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
from app.integrations.lemonsqueezy_client import LemonSqueezyClient
from app.integrations.llm_client import LLMClient
from app.integrations.registry_client import RegistryClient
from app.integrations.vercel_client import VercelClient

__all__ = [
    "GitHubClient",
    "IssueBundleRequest",
    "IssueSpec",
    "LemonSqueezyClient",
    "LLMClient",
    "RegistryClient",
    "RepoRequest",
    "RepoStatus",
    "VercelClient",
]
