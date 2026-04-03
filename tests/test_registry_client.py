"""Tests for the RegistryClient persistence methods."""

from app.integrations.registry_client import RegistryClient


def _make_client() -> RegistryClient:
    return RegistryClient(registry_url="https://stub.test", api_key="test-key")


class TestCreateProjectRecord:
    """Tests for create_project_record."""

    def test_returns_project_id(self) -> None:
        client = _make_client()
        record = client.create_project_record("proj-a", "A project")
        assert record["project_id"].startswith("proj-")

    def test_default_status_active(self) -> None:
        client = _make_client()
        record = client.create_project_record("proj-a", "desc")
        assert record["status"] == "active"

    def test_metadata_stored(self) -> None:
        client = _make_client()
        record = client.create_project_record("proj-a", "desc", metadata={"tag": "v1"})
        assert record["metadata"]["tag"] == "v1"

    def test_persisted_in_memory(self) -> None:
        client = _make_client()
        record = client.create_project_record("proj-a", "desc")
        projects = client.list_projects()
        assert len(projects) == 1
        assert projects[0]["project_id"] == record["project_id"]


class TestListProjects:
    """Tests for list_projects."""

    def test_empty_by_default(self) -> None:
        client = _make_client()
        assert client.list_projects() == []

    def test_returns_all(self) -> None:
        client = _make_client()
        client.create_project_record("a", "desc-a")
        client.create_project_record("b", "desc-b")
        assert len(client.list_projects()) == 2


class TestGetProject:
    """Tests for get_project."""

    def test_returns_none_when_missing(self) -> None:
        client = _make_client()
        assert client.get_project("does-not-exist") is None

    def test_returns_record(self) -> None:
        client = _make_client()
        record = client.create_project_record("x", "desc")
        fetched = client.get_project(record["project_id"])
        assert fetched is not None
        assert fetched["name"] == "x"


class TestUpdateProjectStatus:
    """Tests for update_project_status."""

    def test_updates_existing(self) -> None:
        client = _make_client()
        record = client.create_project_record("proj", "desc")
        updated = client.update_project_status(record["project_id"], "paused")
        assert updated["status"] == "paused"
        assert updated["project_id"] == record["project_id"]

    def test_returns_stub_for_unknown_id(self) -> None:
        client = _make_client()
        result = client.update_project_status("unknown", "archived")
        assert result["status"] == "archived"
        assert result["stub"] is True


class TestCreateIdeaRecord:
    """Tests for create_idea_record."""

    def test_returns_record_id(self) -> None:
        client = _make_client()
        record = client.create_idea_record(idea={"title": "test"})
        assert record["record_id"].startswith("idea-")

    def test_stores_idea_payload(self) -> None:
        client = _make_client()
        idea_data = {"title": "SaaS Dashboard", "problem": "manual work"}
        record = client.create_idea_record(idea=idea_data)
        assert record["idea"]["title"] == "SaaS Dashboard"

    def test_optional_project_id(self) -> None:
        client = _make_client()
        record = client.create_idea_record(idea={}, project_id="proj-123")
        assert record["project_id"] == "proj-123"

    def test_default_project_id_none(self) -> None:
        client = _make_client()
        record = client.create_idea_record(idea={})
        assert record["project_id"] is None


class TestCreateCommandRecord:
    """Tests for create_command_record."""

    def test_returns_record_id(self) -> None:
        client = _make_client()
        record = client.create_command_record("create_repo", {"name": "myrepo"})
        assert record["record_id"].startswith("cmd-")

    def test_status_pending(self) -> None:
        client = _make_client()
        record = client.create_command_record("deploy", {})
        assert record["status"] == "pending"

    def test_parameters_stored(self) -> None:
        client = _make_client()
        params = {"owner": "org", "repo": "proj"}
        record = client.create_command_record("create_repo", params)
        assert record["parameters"]["owner"] == "org"

    def test_optional_project_id(self) -> None:
        client = _make_client()
        record = client.create_command_record("deploy", {}, project_id="proj-abc")
        assert record["project_id"] == "proj-abc"
