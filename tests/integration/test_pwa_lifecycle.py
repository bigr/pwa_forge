"""Integration tests for PWA lifecycle (add, list, remove)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pwa_forge.commands.add import add_app
from pwa_forge.commands.list_apps import list_apps
from pwa_forge.commands.remove import remove_app
from pwa_forge.config import Config
from pwa_forge.registry import Registry


class IsolatedConfig(Config):
    """Configuration with isolated registry for testing."""

    def __init__(self, tmp_path: Path) -> None:
        """Initialize test config with temp paths."""
        super().__init__()
        self._tmp_path = tmp_path
        # Override directories
        self.directories.desktop = tmp_path / "applications"
        self.directories.icons = tmp_path / "icons"
        self.directories.wrappers = tmp_path / "wrappers"
        self.directories.apps = tmp_path / "apps"
        self.directories.userscripts = tmp_path / "userscripts"

        # Create directories
        for directory in [
            self.directories.desktop,
            self.directories.icons,
            self.directories.wrappers,
            self.directories.apps,
            self.directories.userscripts,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def registry_file(self) -> Path:
        """Get test registry file path."""
        registry_dir = self._tmp_path / "data"
        registry_dir.mkdir(parents=True, exist_ok=True)
        return registry_dir / "registry.json"


@pytest.fixture  # type: ignore[misc]
def test_config(tmp_path: Path) -> IsolatedConfig:
    """Create a test configuration with temporary directories."""
    return IsolatedConfig(tmp_path)


class TestPWALifecycle:
    """Test complete PWA lifecycle."""

    def test_add_creates_all_artifacts(self, test_config: Config) -> None:
        """Test that add command creates all necessary files."""
        # Add a PWA
        result = add_app(
            url="https://example.com",
            config=test_config,
            name="Example App",
            app_id="example-app",
            browser="chrome",
            dry_run=False,
        )

        # Verify return value
        assert result["id"] == "example-app"
        assert result["name"] == "Example App"
        assert result["url"] == "https://example.com"

        # Verify profile directory was created
        profile_path = Path(result["profile"])
        assert profile_path.exists()
        assert profile_path.is_dir()

        # Verify wrapper script was created
        wrapper_path = Path(result["wrapper"])
        assert wrapper_path.exists()
        assert wrapper_path.is_file()
        # Check it's executable
        assert wrapper_path.stat().st_mode & 0o111

        # Verify wrapper script content
        wrapper_content = wrapper_path.read_text()
        assert "#!/bin/bash" in wrapper_content
        assert "example-app" in wrapper_content
        assert "https://example.com" in wrapper_content

        # Verify desktop file was created
        desktop_path = Path(result["desktop_file"])
        assert desktop_path.exists()
        assert desktop_path.is_file()

        # Verify desktop file content
        desktop_content = desktop_path.read_text()
        assert "[Desktop Entry]" in desktop_content
        assert "Name=Example App" in desktop_content
        assert "Exec=" in desktop_content
        assert "Icon=" in desktop_content

        # Verify manifest was created
        manifest_path = Path(result["manifest"])
        assert manifest_path.exists()
        assert manifest_path.is_file()

        # Verify manifest content
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        assert manifest["id"] == "example-app"
        assert manifest["name"] == "Example App"
        assert manifest["url"] == "https://example.com"
        assert manifest["browser"] == "chrome"
        assert "created" in manifest
        assert "modified" in manifest

        # Verify registry entry
        registry = Registry(test_config.registry_file)
        app = registry.get_app("example-app")
        assert app["id"] == "example-app"
        assert app["name"] == "Example App"
        assert app["status"] == "active"

    def test_add_with_icon(self, test_config: Config, tmp_path: Path) -> None:
        """Test adding PWA with custom icon."""
        # Create a dummy icon file
        icon_source = tmp_path / "test-icon.png"
        icon_source.write_text("fake icon data")

        # Add PWA with icon
        add_app(
            url="https://test.com",
            config=test_config,
            name="Test App",
            app_id="test-app",
            icon=str(icon_source),
            dry_run=False,
        )

        # Verify icon was copied
        icon_dir = test_config.icons_dir
        copied_icon = icon_dir / "test-app.png"
        assert copied_icon.exists()
        assert copied_icon.read_text() == "fake icon data"

    def test_list_shows_added_apps(self, test_config: Config) -> None:
        """Test that list command shows added apps."""
        # Add multiple PWAs
        add_app(
            url="https://app1.com",
            config=test_config,
            name="App One",
            app_id="app1",
            dry_run=False,
        )
        add_app(
            url="https://app2.com",
            config=test_config,
            name="App Two",
            app_id="app2",
            dry_run=False,
        )

        # List apps
        apps = list_apps(test_config, verbose=False, output_format="json")

        # Verify both apps are listed
        assert len(apps) == 2
        app_ids = [app["id"] for app in apps]
        assert "app1" in app_ids
        assert "app2" in app_ids

    def test_remove_cleans_up_files(self, test_config: Config) -> None:
        """Test that remove command cleans up all files."""
        # Add a PWA
        result = add_app(
            url="https://remove-test.com",
            config=test_config,
            name="Remove Test",
            app_id="remove-test",
            dry_run=False,
        )

        # Store paths for verification
        profile_path = Path(result["profile"])
        wrapper_path = Path(result["wrapper"])
        desktop_path = Path(result["desktop_file"])
        manifest_path = Path(result["manifest"])

        # Verify files exist
        assert profile_path.exists()
        assert wrapper_path.exists()
        assert desktop_path.exists()
        assert manifest_path.exists()

        # Remove the PWA (without removing profile)
        remove_app(
            app_id="remove-test",
            config=test_config,
            remove_profile=False,
            dry_run=False,
        )

        # Verify files were removed
        assert not wrapper_path.exists()
        assert not desktop_path.exists()
        assert not manifest_path.exists()

        # Profile should still exist
        assert profile_path.exists()

        # Verify registry entry was removed
        registry = Registry(test_config.registry_file)
        apps = registry.list_apps()
        assert not any(app["id"] == "remove-test" for app in apps)

    def test_remove_with_profile_deletion(self, test_config: Config) -> None:
        """Test that remove command can delete profile directory."""
        # Add a PWA
        result = add_app(
            url="https://profile-test.com",
            config=test_config,
            name="Profile Test",
            app_id="profile-test",
            dry_run=False,
        )

        profile_path = Path(result["profile"])
        assert profile_path.exists()

        # Remove with profile deletion
        remove_app(
            app_id="profile-test",
            config=test_config,
            remove_profile=True,
            dry_run=False,
        )

        # Profile should be deleted
        assert not profile_path.exists()

    def test_add_list_remove_workflow(self, test_config: Config) -> None:
        """Test complete workflow: add → list → remove."""
        # Start with empty registry
        apps = list_apps(test_config, verbose=False, output_format="json")
        assert len(apps) == 0

        # Add PWA
        add_app(
            url="https://workflow.com",
            config=test_config,
            name="Workflow Test",
            app_id="workflow",
            dry_run=False,
        )

        # Verify it appears in list
        apps = list_apps(test_config, verbose=False, output_format="json")
        assert len(apps) == 1
        assert apps[0]["id"] == "workflow"

        # Remove it
        remove_app(
            app_id="workflow",
            config=test_config,
            remove_profile=True,
            dry_run=False,
        )

        # Verify it's gone
        apps = list_apps(test_config, verbose=False, output_format="json")
        assert len(apps) == 0

    def test_registry_persistence(self, test_config: Config) -> None:
        """Test that registry persists across operations."""
        # Add PWA
        add_app(
            url="https://persist.com",
            config=test_config,
            name="Persist Test",
            app_id="persist",
            dry_run=False,
        )

        # Create new registry instance (simulating restart)
        registry = Registry(test_config.registry_file)
        app = registry.get_app("persist")

        assert app["id"] == "persist"
        assert app["name"] == "Persist Test"
        assert app["url"] == "https://persist.com"

    def test_dry_run_creates_no_files(self, test_config: Config) -> None:
        """Test that dry-run mode creates no actual files."""
        # Run add in dry-run mode
        result = add_app(
            url="https://dryrun.com",
            config=test_config,
            name="Dry Run Test",
            app_id="dryrun",
            dry_run=True,
        )

        # Paths are returned but files should not exist
        assert not Path(result["profile"]).exists()
        assert not Path(result["wrapper"]).exists()
        assert not Path(result["desktop_file"]).exists()
        assert not Path(result["manifest"]).exists()

        # Registry should not have the entry
        registry = Registry(test_config.registry_file)
        apps = registry.list_apps()
        assert not any(app["id"] == "dryrun" for app in apps)

    def test_duplicate_id_error(self, test_config: Config) -> None:
        """Test that adding duplicate ID raises error."""
        from pwa_forge.commands.add import AddCommandError

        # Add first PWA
        add_app(
            url="https://dup1.com",
            config=test_config,
            name="Duplicate Test",
            app_id="duplicate",
            dry_run=False,
        )

        # Try to add another with same ID
        with pytest.raises(AddCommandError, match="already exists"):
            add_app(
                url="https://dup2.com",
                config=test_config,
                name="Another App",
                app_id="duplicate",
                dry_run=False,
            )

    def test_remove_nonexistent_error(self, test_config: Config) -> None:
        """Test that removing non-existent app raises error."""
        from pwa_forge.commands.remove import RemoveCommandError

        with pytest.raises(RemoveCommandError, match="not found"):
            remove_app(
                app_id="nonexistent",
                config=test_config,
                dry_run=False,
            )

    def test_manifest_yaml_format(self, test_config: Config) -> None:
        """Test that manifest is valid YAML with expected structure."""
        # Add PWA
        result = add_app(
            url="https://yaml-test.com",
            config=test_config,
            name="YAML Test",
            app_id="yaml-test",
            browser="chromium",
            out_of_scope="same-browser-window",
            dry_run=False,
        )

        # Load and validate manifest
        manifest_path = Path(result["manifest"])
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        # Check required fields
        assert manifest["id"] == "yaml-test"
        assert manifest["name"] == "YAML Test"
        assert manifest["url"] == "https://yaml-test.com"
        assert manifest["browser"] == "chromium"
        assert manifest["out_of_scope"] == "same-browser-window"
        assert manifest["version"] == 1

        # Check computed fields
        assert "profile" in manifest
        assert "wm_class" in manifest
        assert "created" in manifest
        assert "modified" in manifest

    def test_registry_json_format(self, test_config: Config) -> None:
        """Test that registry is valid JSON with expected structure."""
        # Add PWA
        add_app(
            url="https://json-test.com",
            config=test_config,
            name="JSON Test",
            app_id="json-test",
            dry_run=False,
        )

        # Load and validate registry
        registry_path = test_config.registry_file
        with open(registry_path) as f:
            registry_data = json.load(f)

        # Check structure
        assert "version" in registry_data
        assert registry_data["version"] == 1
        assert "apps" in registry_data
        assert isinstance(registry_data["apps"], list)
        assert len(registry_data["apps"]) > 0

        # Find our app entry
        app = next((a for a in registry_data["apps"] if a["id"] == "json-test"), None)
        assert app is not None
        assert app["name"] == "JSON Test"
        assert app["url"] == "https://json-test.com"
        assert app["status"] == "active"
        assert "manifest_path" in app
        assert "desktop_file" in app
        assert "wrapper_script" in app
