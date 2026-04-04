"""
dependencies.py – Shared application-level dependency providers.

Centralises the creation of long-lived service clients so that every
route module shares the same instance (and the same in-memory stub
storage while the registry is still stubbed).
"""

from functools import lru_cache as _lru_cache

from app.core.config import get_settings
from app.factory.orchestrator import FactoryOrchestrator, FactoryRunStore
from app.integrations.github_client import GitHubClient
from app.integrations.registry_client import RegistryClient
from app.integrations.vercel_client import VercelClient
from app.feedback.service import FeedbackService
from app.portfolio.repository import PortfolioRepository


@_lru_cache(maxsize=1)
def get_registry_client() -> RegistryClient:
    """Return a cached, application-wide ``RegistryClient`` instance."""
    settings = get_settings()
    return RegistryClient(
        registry_url=settings.registry_url,
        api_key=settings.registry_api_key,
    )


@_lru_cache(maxsize=1)
def get_factory_run_store() -> FactoryRunStore:
    """Return a cached in-memory store for factory run state."""
    return FactoryRunStore()


@_lru_cache(maxsize=1)
def get_github_client() -> GitHubClient:
    """Return a cached GitHub client for factory operations."""
    settings = get_settings()
    return GitHubClient(
        token=settings.github_token,
        base_url=settings.github_api_base_url,
    )


@_lru_cache(maxsize=1)
def get_vercel_client() -> VercelClient:
    """Return a cached Vercel client for deployment operations."""
    settings = get_settings()
    return VercelClient(
        token=settings.vercel_token,
        team_id=settings.vercel_team_id or None,
    )


@_lru_cache(maxsize=1)
def get_factory_orchestrator() -> FactoryOrchestrator:
    """Return a cached factory orchestrator instance."""
    settings = get_settings()
    return FactoryOrchestrator(
        github_client=get_github_client(),
        vercel_client=get_vercel_client(),
        run_store=get_factory_run_store(),
        github_owner=settings.github_factory_owner,
        repo_template=settings.github_factory_template_repo,
    )


@_lru_cache(maxsize=1)
def get_portfolio_repository() -> PortfolioRepository:
    """Return a cached SQLite-backed portfolio repository."""
    settings = get_settings()
    return PortfolioRepository(db_path=settings.portfolio_db_path)


@_lru_cache(maxsize=1)
def get_feedback_service() -> FeedbackService:
    """Return a cached feedback service using the portfolio repository."""
    return FeedbackService(repository=get_portfolio_repository())
