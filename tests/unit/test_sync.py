"""Unit tests for sync command."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
import yaml
from pwa_forge.commands.sync import SyncCommandError, sync_app
from pwa_forge.config import Config
from pwa_forge.registry import Registry


class TestSyncApp:
    """Test sync_app function."""

    def test_sync_app_not_found_in_registry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test sync fails when app not found in registry."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        registry_file = tmp_path / "registry.json"
        config.directories.apps.mkdir(parents=True)

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create empty registry
        registry = Registry(registry_file)
        registry._write({"version": 1, "apps": [], "handlers": []})

        with pytest.raises(SyncCommandError, match="not found in registry"):
            sync_app("nonexistent", config)

    def test_sync_app_manifest_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test sync fails when manifest file is missing."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        registry_file = tmp_path / "registry.json"
        config.directories.apps.mkdir(parents=True)

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create registry with app entry
        registry = Registry(registry_file)
        registry._write({
            "version": 1,
            "apps": [
                {
                    "id": "test-app",
                    "name": "Test App",
                    "manifest_path": str(tmp_path / "apps" / "test-app" / "manifest.yaml"),
                    "wrapper_script": str(tmp_path / "wrappers" / "test-app"),
                    "desktop_file": str(tmp_path / "desktop" / "test-app.desktop"),
                }
            ],
            "handlers": [],
        })

        with pytest.raises(SyncCommandError, match="Manifest file not found"):
            sync_app("test-app", config)

    def test_sync_app_invalid_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test sync fails with invalid YAML in manifest."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        config.directories.apps.mkdir(parents=True)
        manifest_path.parent.mkdir(parents=True)

        # Create manifest with invalid YAML
        manifest_path.write_text("invalid: yaml: content: [")

        # Create registry
        registry = Registry(registry_file)
        registry._write({
            "version": 1,
            "apps": [
                {
                    "id": "test-app",
                    "name": "Test App",
                    "manifest_path": str(manifest_path),
                    "wrapper_script": str(tmp_path / "wrappers" / "test-app"),
                    "desktop_file": str(tmp_path / "desktop" / "test-app.desktop"),
                }
            ],
            "handlers": [],
        })

        with pytest.raises(SyncCommandError, match="Invalid YAML"):
            sync_app("test-app", config)

    def test_sync_app_missing_required_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test sync fails when manifest is missing required fields."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        config.directories.apps.mkdir(parents=True)
        manifest_path.parent.mkdir(parents=True)

        # Create manifest missing required fields
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            # Missing 'url' and 'browser'
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create registry
        registry = Registry(registry_file)
        registry._write({
            "version": 1,
            "apps": [
                {
                    "id": "test-app",
                    "name": "Test App",
                    "manifest_path": str(manifest_path),
                    "wrapper_script": str(tmp_path / "wrappers" / "test-app"),
                    "desktop_file": str(tmp_path / "desktop" / "test-app.desktop"),
                }
            ],
            "handlers": [],
        })

        with pytest.raises(SyncCommandError, match="missing required fields"):
            sync_app("test-app", config)

    def test_sync_app_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful sync regenerates wrapper and desktop files."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"
        wrapper_path = tmp_path / "wrappers" / "test-app"
        desktop_path = tmp_path / "desktop" / "pwa-forge-test-app.desktop"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)
        manifest_path.parent.mkdir(parents=True)

        # Create manifest
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
            "profile": str(tmp_path / "apps" / "test-app" / "profile"),
            "wm_class": "TestApp",
            "icon": str(tmp_path / "icons" / "test-app.svg"),
            "comment": "Test application",
            "categories": ["Network", "WebBrowser"],
            "flags": {
                "ozone_platform": "x11",
                "enable_features": ["WebUIDarkMode"],
                "disable_features": ["IntentPickerPWALinks"],
            },
            "created": "2025-01-01T00:00:00Z",
            "modified": "2025-01-01T00:00:00Z",
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create registry
        registry = Registry(registry_file)
        registry._write({
            "version": 1,
            "apps": [
                {
                    "id": "test-app",
                    "name": "Test App",
                    "manifest_path": str(manifest_path),
                    "wrapper_script": str(wrapper_path),
                    "desktop_file": str(desktop_path),
                }
            ],
            "handlers": [],
        })

        # Run sync
        result = sync_app("test-app", config, dry_run=False)

        # Verify results
        assert result["id"] == "test-app"
        assert "wrapper" in result["regenerated"]
        assert "desktop" in result["regenerated"]

        # Verify wrapper script was created
        assert wrapper_path.exists()
        wrapper_content = wrapper_path.read_text()
        assert "Test App" in wrapper_content
        assert "https://example.com" in wrapper_content
        assert "--app=" in wrapper_content

        # Verify wrapper is executable
        wrapper_stat = wrapper_path.stat()
        assert wrapper_stat.st_mode & stat.S_IXUSR

        # Verify desktop file was created
        assert desktop_path.exists()
        desktop_content = desktop_path.read_text()
        assert "Test App" in desktop_content
        assert str(wrapper_path) in desktop_content

        # Verify manifest modified timestamp was updated
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        assert updated_manifest["modified"] != "2025-01-01T00:00:00Z"

    def test_sync_app_dry_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test dry-run mode doesn't create files."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"
        wrapper_path = tmp_path / "wrappers" / "test-app"
        desktop_path = tmp_path / "desktop" / "pwa-forge-test-app.desktop"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        config.directories.apps.mkdir(parents=True)
        manifest_path.parent.mkdir(parents=True)

        # Create manifest
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
            "wm_class": "TestApp",
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create registry
        registry = Registry(registry_file)
        registry._write({
            "version": 1,
            "apps": [
                {
                    "id": "test-app",
                    "name": "Test App",
                    "manifest_path": str(manifest_path),
                    "wrapper_script": str(wrapper_path),
                    "desktop_file": str(desktop_path),
                }
            ],
            "handlers": [],
        })

        # Run sync with dry_run
        result = sync_app("test-app", config, dry_run=True)

        # Verify results
        assert result["id"] == "test-app"
        assert result["regenerated"] == []

        # Verify files were NOT created
        assert not wrapper_path.exists()
        assert not desktop_path.exists()

    def test_sync_app_warns_about_manual_changes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test sync warns when files appear manually edited."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"
        wrapper_path = tmp_path / "wrappers" / "test-app"
        desktop_path = tmp_path / "desktop" / "pwa-forge-test-app.desktop"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)
        manifest_path.parent.mkdir(parents=True)

        # Create manifest with old modified timestamp
        old_timestamp = "2025-01-01T00:00:00Z"
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
            "wm_class": "TestApp",
            "modified": old_timestamp,
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create existing wrapper script with newer timestamp
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        wrapper_path.write_text("#!/bin/bash\necho 'manual edit'")
        # Set wrapper mtime to future
        import time

        future_time = time.time() + 3600  # 1 hour in the future
        import os

        os.utime(wrapper_path, (future_time, future_time))

        # Create registry
        registry = Registry(registry_file)
        registry._write({
            "version": 1,
            "apps": [
                {
                    "id": "test-app",
                    "name": "Test App",
                    "manifest_path": str(manifest_path),
                    "wrapper_script": str(wrapper_path),
                    "desktop_file": str(desktop_path),
                }
            ],
            "handlers": [],
        })

        # Run sync
        result = sync_app("test-app", config, dry_run=False)

        # Verify warning was generated
        assert len(result["warnings"]) > 0
        assert any("manually edited" in warning.lower() for warning in result["warnings"])

    def test_sync_app_handles_minimal_manifest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test sync works with minimal manifest (only required fields)."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"
        wrapper_path = tmp_path / "wrappers" / "test-app"
        desktop_path = tmp_path / "desktop" / "pwa-forge-test-app.desktop"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)
        manifest_path.parent.mkdir(parents=True)

        # Create minimal manifest
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create registry
        registry = Registry(registry_file)
        registry._write({
            "version": 1,
            "apps": [
                {
                    "id": "test-app",
                    "name": "Test App",
                    "manifest_path": str(manifest_path),
                    "wrapper_script": str(wrapper_path),
                    "desktop_file": str(desktop_path),
                }
            ],
            "handlers": [],
        })

        # Run sync
        result = sync_app("test-app", config, dry_run=False)

        # Verify success
        assert result["id"] == "test-app"
        assert "wrapper" in result["regenerated"]
        assert "desktop" in result["regenerated"]
        assert wrapper_path.exists()
        assert desktop_path.exists()
