"""
dependencies.py – Shared application-level dependency providers.

Centralises the creation of long-lived service clients so that every
route module shares the same instance (and the same in-memory stub
storage while the registry is still stubbed).
"""

from functools import lru_cache as _lru_cache

from app.core.config import get_settings
from app.integrations.registry_client import RegistryClient


@_lru_cache(maxsize=1)
def get_registry_client() -> RegistryClient:
    """Return a cached, application-wide ``RegistryClient`` instance."""
    settings = get_settings()
    return RegistryClient(
        registry_url=settings.registry_url,
        api_key=settings.registry_api_key,
    )
