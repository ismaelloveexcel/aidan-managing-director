"""
dependencies.py – Shared application-level dependency providers.

Centralises the creation of long-lived service clients so that every
route module shares the same instance (and the same in-memory stub
storage while the registry is still stubbed).
"""

from functools import lru_cache as _lru_cache

from app.command_center.service import CommandCenterService
from app.core.config import get_settings
from app.factory.factory_client import FactoryClient
from app.factory.orchestrator import FactoryOrchestrator, FactoryRunStore
from app.memory.auto_learner import AutoLearner
from app.memory.store import MemoryStore
from app.observability.control import ControlPlaneService
from app.portfolio.intelligence import PortfolioIntelligenceService
from app.governance.service import GovernanceService
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
def get_factory_client() -> FactoryClient:
    """Return a cached factory workflow client."""
    settings = get_settings()
    return FactoryClient(
        github_client=get_github_client(),
        orchestrator=get_factory_orchestrator(),
        factory_owner=settings.factory_owner or settings.github_factory_owner,
        factory_repo=settings.factory_repo,
        workflow_id=settings.factory_workflow_id,
    )


@_lru_cache(maxsize=1)
def get_portfolio_repository() -> PortfolioRepository:
    """Return a cached SQLite-backed portfolio repository."""
    settings = get_settings()
    return PortfolioRepository(db_path=settings.portfolio_db_path)


@_lru_cache(maxsize=1)
def get_feedback_service() -> FeedbackService:
    """Return a cached feedback service using the portfolio repository."""
    return FeedbackService(
        repository=get_portfolio_repository(),
        memory_store=get_memory_store(),
    )


@_lru_cache(maxsize=1)
def get_governance_service() -> GovernanceService:
    """Return a cached governance service."""
    return GovernanceService()


@_lru_cache(maxsize=1)
def get_memory_store() -> MemoryStore:
    """Return a cached in-memory memory/learning store."""
    settings = get_settings()
    return MemoryStore(max_events=settings.memory_max_events)


@_lru_cache(maxsize=1)
def get_auto_learner() -> AutoLearner:
    """Return a cached auto-learner bound to the shared memory store."""
    return AutoLearner(memory_store=get_memory_store())


@_lru_cache(maxsize=1)
def get_portfolio_intelligence_service() -> PortfolioIntelligenceService:
    """Return portfolio-intelligence service bound to shared repository."""
    return PortfolioIntelligenceService(repository=get_portfolio_repository())


@_lru_cache(maxsize=1)
def get_control_plane() -> ControlPlaneService:
    """Return control-plane observability service."""
    return ControlPlaneService(
        repository=get_portfolio_repository(),
        pending_approvals_provider=get_governance_service().list_pending_approvals,
    )


@_lru_cache(maxsize=1)
def get_command_center_service() -> CommandCenterService:
    """Return command-center service for operator state snapshots."""
    return CommandCenterService(
        registry=get_registry_client(),
        portfolio=get_portfolio_repository(),
        governance=get_governance_service(),
        factory_run_store=get_factory_run_store(),
    )
