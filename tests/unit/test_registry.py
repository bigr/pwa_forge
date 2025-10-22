"""Unit tests for registry management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pwa_forge.registry import AppExistsError, AppNotFoundError, Registry, RegistryError


@pytest.fixture  # type: ignore[misc]
def temp_registry(tmp_path: Path) -> Registry:
    """Create a temporary registry for testing."""
    registry_path = tmp_path / "registry.json"
    return Registry(registry_path)


@pytest.fixture  # type: ignore[misc]
def sample_app() -> dict[str, Any]:
    """Create a sample app entry."""
    return {
        "id": "test-app",
        "name": "Test App",
        "url": "https://example.com",
        "manifest_path": "/path/to/manifest.yaml",
        "desktop_file": "/path/to/app.desktop",
        "wrapper_script": "/path/to/wrapper",
        "status": "active",
    }


@pytest.fixture  # type: ignore[misc]
def sample_handler() -> dict[str, Any]:
    """Create a sample handler entry."""
    return {
        "scheme": "ff",
        "browser": "firefox",
        "desktop_file": "/path/to/handler.desktop",
        "script": "/path/to/script",
    }


def test_registry_initialization(tmp_path: Path) -> None:
    """Test registry initialization."""
    registry_path = tmp_path / "registry.json"
    registry = Registry(registry_path)
    assert registry.registry_path == registry_path
    assert registry._lock_path == tmp_path / "registry.lock"


def test_list_apps_empty_registry(temp_registry: Registry) -> None:
    """Test listing apps from empty registry."""
    apps = temp_registry.list_apps()
    assert apps == []


def test_add_app(temp_registry: Registry, sample_app: dict[str, Any]) -> None:
    """Test adding a new app to registry."""
    temp_registry.add_app(sample_app)
    apps = temp_registry.list_apps()
    assert len(apps) == 1
    assert apps[0]["id"] == "test-app"
    assert apps[0]["name"] == "Test App"


def test_add_app_without_id(temp_registry: Registry) -> None:
    """Test adding app without ID raises ValueError."""
    with pytest.raises(ValueError, match="must include 'id' field"):
        temp_registry.add_app({"name": "Test"})


def test_add_duplicate_app(temp_registry: Registry, sample_app: dict[str, Any]) -> None:
    """Test adding duplicate app raises AppExistsError."""
    temp_registry.add_app(sample_app)
    with pytest.raises(AppExistsError, match="already exists"):
        temp_registry.add_app(sample_app)


def test_get_app(temp_registry: Registry, sample_app: dict[str, Any]) -> None:
    """Test getting a specific app."""
    temp_registry.add_app(sample_app)
    app = temp_registry.get_app("test-app")
    assert app["id"] == "test-app"
    assert app["name"] == "Test App"


def test_get_app_not_found(temp_registry: Registry) -> None:
    """Test getting non-existent app raises AppNotFoundError."""
    with pytest.raises(AppNotFoundError, match="not found"):
        temp_registry.get_app("nonexistent")


def test_update_app(temp_registry: Registry, sample_app: dict[str, Any]) -> None:
    """Test updating an existing app."""
    temp_registry.add_app(sample_app)
    temp_registry.update_app("test-app", {"name": "Updated Name", "status": "broken"})

    updated_app = temp_registry.get_app("test-app")
    assert updated_app["name"] == "Updated Name"
    assert updated_app["status"] == "broken"
    assert "modified" in updated_app


def test_update_app_not_found(temp_registry: Registry) -> None:
    """Test updating non-existent app raises AppNotFoundError."""
    with pytest.raises(AppNotFoundError, match="not found"):
        temp_registry.update_app("nonexistent", {"name": "New Name"})


def test_remove_app(temp_registry: Registry, sample_app: dict[str, Any]) -> None:
    """Test removing an app from registry."""
    temp_registry.add_app(sample_app)
    removed = temp_registry.remove_app("test-app")

    assert removed["id"] == "test-app"
    assert temp_registry.list_apps() == []


def test_remove_app_not_found(temp_registry: Registry) -> None:
    """Test removing non-existent app raises AppNotFoundError."""
    with pytest.raises(AppNotFoundError, match="not found"):
        temp_registry.remove_app("nonexistent")


def test_multiple_apps(temp_registry: Registry) -> None:
    """Test managing multiple apps."""
    apps = [
        {"id": "app1", "name": "App 1", "url": "https://app1.com"},
        {"id": "app2", "name": "App 2", "url": "https://app2.com"},
        {"id": "app3", "name": "App 3", "url": "https://app3.com"},
    ]

    for app in apps:
        temp_registry.add_app(app)

    all_apps = temp_registry.list_apps()
    assert len(all_apps) == 3

    # Remove middle app
    temp_registry.remove_app("app2")
    remaining_apps = temp_registry.list_apps()
    assert len(remaining_apps) == 2
    assert remaining_apps[0]["id"] == "app1"
    assert remaining_apps[1]["id"] == "app3"


def test_list_handlers_empty_registry(temp_registry: Registry) -> None:
    """Test listing handlers from empty registry."""
    handlers = temp_registry.list_handlers()
    assert handlers == []


def test_add_handler(temp_registry: Registry, sample_handler: dict[str, Any]) -> None:
    """Test adding a new handler to registry."""
    temp_registry.add_handler(sample_handler)
    handlers = temp_registry.list_handlers()
    assert len(handlers) == 1
    assert handlers[0]["scheme"] == "ff"


def test_add_handler_without_scheme(temp_registry: Registry) -> None:
    """Test adding handler without scheme raises ValueError."""
    with pytest.raises(ValueError, match="must include 'scheme' field"):
        temp_registry.add_handler({"browser": "firefox"})


def test_add_duplicate_handler(temp_registry: Registry, sample_handler: dict[str, Any]) -> None:
    """Test adding duplicate handler raises RegistryError."""
    temp_registry.add_handler(sample_handler)
    with pytest.raises(RegistryError, match="already exists"):
        temp_registry.add_handler(sample_handler)


def test_get_handler(temp_registry: Registry, sample_handler: dict[str, Any]) -> None:
    """Test getting a specific handler."""
    temp_registry.add_handler(sample_handler)
    handler = temp_registry.get_handler("ff")
    assert handler["scheme"] == "ff"
    assert handler["browser"] == "firefox"


def test_get_handler_not_found(temp_registry: Registry) -> None:
    """Test getting non-existent handler raises RegistryError."""
    with pytest.raises(RegistryError, match="not found"):
        temp_registry.get_handler("nonexistent")


def test_remove_handler(temp_registry: Registry, sample_handler: dict[str, Any]) -> None:
    """Test removing a handler from registry."""
    temp_registry.add_handler(sample_handler)
    removed = temp_registry.remove_handler("ff")

    assert removed["scheme"] == "ff"
    assert temp_registry.list_handlers() == []


def test_remove_handler_not_found(temp_registry: Registry) -> None:
    """Test removing non-existent handler raises RegistryError."""
    with pytest.raises(RegistryError, match="not found"):
        temp_registry.remove_handler("nonexistent")


def test_registry_persistence(tmp_path: Path, sample_app: dict[str, Any]) -> None:
    """Test that registry persists across instances."""
    registry_path = tmp_path / "registry.json"

    # Create first registry instance and add app
    registry1 = Registry(registry_path)
    registry1.add_app(sample_app)

    # Create second registry instance and verify app exists
    registry2 = Registry(registry_path)
    apps = registry2.list_apps()
    assert len(apps) == 1
    assert apps[0]["id"] == "test-app"


def test_registry_corrupted_json(tmp_path: Path) -> None:
    """Test handling of corrupted registry JSON."""
    registry_path = tmp_path / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("invalid json {")

    registry = Registry(registry_path)
    with pytest.raises(RegistryError, match="Corrupted registry"):
        registry.list_apps()


def test_registry_file_structure(temp_registry: Registry, sample_app: dict[str, Any]) -> None:
    """Test that registry file has correct structure."""
    temp_registry.add_app(sample_app)

    # Read file directly
    content = temp_registry.registry_path.read_text()
    data = json.loads(content)

    assert "version" in data
    assert data["version"] == 1
    assert "apps" in data
    assert isinstance(data["apps"], list)
    assert "handlers" in data
    assert isinstance(data["handlers"], list)


def test_mixed_apps_and_handlers(
    temp_registry: Registry,
    sample_app: dict[str, Any],
    sample_handler: dict[str, Any],
) -> None:
    """Test registry with both apps and handlers."""
    temp_registry.add_app(sample_app)
    temp_registry.add_handler(sample_handler)

    apps = temp_registry.list_apps()
    handlers = temp_registry.list_handlers()

    assert len(apps) == 1
    assert len(handlers) == 1
    assert apps[0]["id"] == "test-app"
    assert handlers[0]["scheme"] == "ff"
