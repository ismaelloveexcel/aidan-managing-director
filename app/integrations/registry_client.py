"""
registry_client.py – Integration with the AI-DAN service registry.

Provides a typed client for registering, discovering, and querying
services and projects within the AI-DAN ecosystem.

All methods are currently **stub implementations** that return
realistic placeholder data.  Real HTTP calls (via ``httpx``) will
replace the stubs once registry credentials are provisioned.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx


class RegistryClient:
    """
    Wraps the AI-DAN service registry API.

    Every public method returns structured placeholder data so that
    callers can be developed and tested before the registry is live.
    """

    def __init__(self, registry_url: str, api_key: str) -> None:
        """
        Initialise the registry client.

        Args:
            registry_url: Base URL of the service registry.
            api_key: API key for authenticating with the registry.
        """
        self.registry_url = registry_url.rstrip("/")
        self.api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._http_client: httpx.Client | None = None

        # In-memory stub storage – replaced by real DB once wired.
        self._projects: dict[str, dict[str, Any]] = {}
        self._ideas: dict[str, dict[str, Any]] = {}
        self._commands: dict[str, dict[str, Any]] = {}

    # -- lifecycle --------------------------------------------------------------

    def _client(self) -> httpx.Client:
        """
        Return the shared ``httpx.Client`` instance.

        The client is created lazily and reused for the lifetime of
        this ``RegistryClient``.  Call :meth:`close` when the client is
        no longer needed to release network resources.
        """
        if self._http_client is None:
            self._http_client = httpx.Client(
                base_url=self.registry_url,
                headers=self._headers,
                timeout=30.0,
            )
        return self._http_client

    def close(self) -> None:
        """Close the underlying HTTP client, releasing held resources."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> RegistryClient:
        """Allow ``RegistryClient`` to be used as a context manager."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Ensure the underlying client is closed when leaving the context."""
        self.close()

    # -- public API -------------------------------------------------------------

    def create_project_record(
        self,
        name: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new project record in the registry.

        Args:
            name: Unique project name.
            description: Short description of the project.
            metadata: Optional additional metadata (tags, owner, etc.).

        Returns:
            The newly created project record.
        """
        project_id = f"proj-{uuid.uuid4().hex[:8]}"
        now = datetime.now(tz=timezone.utc).isoformat()
        record = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "status": "active",
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
            "stub": True,
        }
        self._projects[project_id] = record
        return record

    def update_project_status(
        self,
        project_id: str,
        status: str,
    ) -> dict[str, Any] | None:
        """
        Update the status of an existing project in the registry.

        Args:
            project_id: Registry-assigned project identifier.
            status: New status value (e.g. ``"active"``, ``"paused"``,
                ``"completed"``, ``"archived"``).

        Returns:
            The updated project record, or ``None`` if not found.
        """
        now = datetime.now(tz=timezone.utc).isoformat()
        if project_id not in self._projects:
            return None
        self._projects[project_id]["status"] = status
        self._projects[project_id]["updated_at"] = now
        return self._projects[project_id]

    def reset(self) -> None:
        """Clear all in-memory stub storage.  Useful for test isolation."""
        self._projects.clear()
        self._ideas.clear()
        self._commands.clear()

    def list_projects(self) -> list[dict[str, Any]]:
        """
        Return all project records currently held in the registry.

        Returns:
            A list of project record dictionaries.
        """
        return list(self._projects.values())

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """
        Retrieve a single project record by its ID.

        Args:
            project_id: Registry-assigned project identifier.

        Returns:
            The project record, or ``None`` if not found.
        """
        return self._projects.get(project_id)

    def create_idea_record(
        self,
        idea: dict[str, Any],
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Persist an idea in the registry.

        Args:
            idea: Serialised idea payload (matches ``Idea`` schema).
            project_id: Optional project to associate the idea with.

        Returns:
            The persisted idea record.
        """
        record_id = f"idea-{uuid.uuid4().hex[:8]}"
        now = datetime.now(tz=timezone.utc).isoformat()
        record = {
            "record_id": record_id,
            "idea": idea,
            "project_id": project_id,
            "created_at": now,
            "stub": True,
        }
        self._ideas[record_id] = record
        return record

    def create_command_record(
        self,
        command_type: str,
        parameters: dict[str, Any],
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Persist a dispatched command in the registry.

        Args:
            command_type: Type of command being dispatched.
            parameters: Command-specific parameters.
            project_id: Optional project to associate the command with.

        Returns:
            The persisted command record.
        """
        record_id = f"cmd-{uuid.uuid4().hex[:8]}"
        now = datetime.now(tz=timezone.utc).isoformat()
        record = {
            "record_id": record_id,
            "command_type": command_type,
            "parameters": parameters,
            "project_id": project_id,
            "status": "pending",
            "created_at": now,
            "stub": True,
        }
        self._commands[record_id] = record
        return record

    def get_command_record(self, record_id: str) -> dict[str, Any] | None:
        """Retrieve a persisted command record by ID."""
        return self._commands.get(record_id)

    def update_command_status(
        self,
        *,
        record_id: str,
        status: str,
        message: str | None = None,
    ) -> dict[str, Any] | None:
        """Update status metadata for an existing command record."""
        record = self._commands.get(record_id)
        if record is None:
            return None
        record["status"] = status
        if message is not None:
            record["message"] = message
        record["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        return record

    def register_service(self, name: str, metadata: dict[str, Any]) -> str:
        """
        Register a new service or agent with the registry.

        Args:
            name: Unique service name.
            metadata: Descriptive metadata (capabilities, endpoints, etc.).

        Returns:
            The registry-assigned service ID.
        """
        return f"svc-{uuid.uuid4().hex[:8]}"

    def discover(self, capability: str) -> list[dict[str, Any]]:
        """
        Discover services that expose a given capability.

        Args:
            capability: Capability tag to search for.

        Returns:
            A list of matching service records (empty in stub mode).
        """
        return []

    def get_service(self, service_id: str) -> dict[str, Any]:
        """
        Retrieve the registry record for a specific service.

        Args:
            service_id: Registry-assigned identifier.

        Returns:
            Service metadata dictionary.
        """
        return {
            "service_id": service_id,
            "name": "stub-service",
            "status": "active",
            "metadata": {},
            "stub": True,
        }
