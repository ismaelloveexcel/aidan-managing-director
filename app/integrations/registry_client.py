"""
registry_client.py – Integration with the AI-DAN service registry.

Provides a typed client for registering, discovering, and querying
services and agents within the AI-DAN ecosystem.
"""

from typing import Any


class RegistryClient:
    """
    Wraps the AI-DAN service registry API.

    Business logic to be implemented in a future iteration.
    """

    def __init__(self, registry_url: str, api_key: str) -> None:
        """
        Initialise the registry client.

        Args:
            registry_url: Base URL of the service registry.
            api_key: API key for authenticating with the registry.
        """
        self.registry_url = registry_url
        self.api_key = api_key

    def register_service(self, name: str, metadata: dict[str, Any]) -> str:
        """
        Register a new service or agent with the registry.

        Args:
            name: Unique service name.
            metadata: Descriptive metadata (capabilities, endpoints, etc.).

        Returns:
            The registry-assigned service ID.
        """
        raise NotImplementedError

    def discover(self, capability: str) -> list[dict[str, Any]]:
        """
        Discover services that expose a given capability.

        Args:
            capability: Capability tag to search for.

        Returns:
            A list of matching service records.
        """
        raise NotImplementedError

    def get_service(self, service_id: str) -> dict[str, Any]:
        """
        Retrieve the registry record for a specific service.

        Args:
            service_id: Registry-assigned identifier.

        Returns:
            Service metadata dictionary.
        """
        raise NotImplementedError
