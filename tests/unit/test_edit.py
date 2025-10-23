"""Unit tests for edit command."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from pwa_forge.commands.edit import EditCommandError, edit_app
from pwa_forge.config import Config
from pwa_forge.registry import Registry


class TestEditApp:
    """Test edit_app function."""

    def test_edit_app_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit fails when app not found."""
        config = Config()
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create empty registry
        registry = Registry(registry_file)
        registry._write({"version": 1, "apps": [], "handlers": []})

        with pytest.raises(EditCommandError, match="not found in registry"):
            edit_app("nonexistent", config)

    def test_edit_app_manifest_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit fails when manifest file is missing."""
        config = Config()
        registry_file = tmp_path / "registry.json"

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

        with pytest.raises(EditCommandError, match="Manifest file not found"):
            edit_app("test-app", config)

    def test_edit_app_no_editor(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit fails when no editor is available."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create manifest
        manifest_path.parent.mkdir(parents=True)
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
                    "wrapper_script": str(tmp_path / "wrappers" / "test-app"),
                    "desktop_file": str(tmp_path / "desktop" / "test-app.desktop"),
                }
            ],
            "handlers": [],
        })

        # Mock no EDITOR and no fallback editors
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setattr("shutil.which", lambda x: None)

        with pytest.raises(EditCommandError, match="No editor found"):
            edit_app("test-app", config)

    def test_edit_app_success_with_sync(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful edit with auto-sync."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"
        wrapper_path = tmp_path / "wrappers" / "test-app"
        desktop_path = tmp_path / "desktop" / "test-app.desktop"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create manifest
        manifest_path.parent.mkdir(parents=True)
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

        # Mock editor - just touch the file to simulate edit
        mock_subprocess = MagicMock()
        mock_subprocess.return_value.returncode = 0
        monkeypatch.setattr("subprocess.run", mock_subprocess)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Run edit
        result = edit_app("test-app", config, auto_sync=True)

        # Verify results
        assert result["id"] == "test-app"
        assert result["edited"] is True
        assert result["synced"] is True
        assert result["validation_errors"] is None

        # Verify editor was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0][0] == "mock-editor"
        assert str(manifest_path) in str(call_args[0][0])

    def test_edit_app_no_sync(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit without auto-sync."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create manifest
        manifest_path.parent.mkdir(parents=True)
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
                    "wrapper_script": str(tmp_path / "wrappers" / "test-app"),
                    "desktop_file": str(tmp_path / "desktop" / "test-app.desktop"),
                }
            ],
            "handlers": [],
        })

        # Mock editor
        mock_subprocess = MagicMock()
        mock_subprocess.return_value.returncode = 0
        monkeypatch.setattr("subprocess.run", mock_subprocess)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Run edit without sync
        result = edit_app("test-app", config, auto_sync=False)

        # Verify results
        assert result["id"] == "test-app"
        assert result["edited"] is True
        assert result["synced"] is False
        assert result["validation_errors"] is None

    def test_edit_app_validation_failure_restores_backup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validation failure restores backup."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create valid manifest
        manifest_path.parent.mkdir(parents=True)
        original_manifest = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
        }
        manifest_path.write_text(yaml.safe_dump(original_manifest))

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

        # Mock editor - simulate writing invalid YAML
        def mock_run_editor(args: list[str], **kwargs: Any) -> MagicMock:  # noqa: ARG001
            # Overwrite manifest with invalid YAML
            manifest_path.write_text("invalid: yaml: content: [")
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run_editor)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Run edit
        result = edit_app("test-app", config, auto_sync=True)

        # Verify validation failed
        assert result["id"] == "test-app"
        assert result["edited"] is True
        assert result["synced"] is False
        assert result["validation_errors"] is not None
        assert len(result["validation_errors"]) > 0

        # Verify manifest was restored
        restored_manifest = yaml.safe_load(manifest_path.read_text())
        assert restored_manifest == original_manifest

    def test_edit_app_missing_required_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit detects missing required fields."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create valid manifest
        manifest_path.parent.mkdir(parents=True)
        original_manifest = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
        }
        manifest_path.write_text(yaml.safe_dump(original_manifest))

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

        # Mock editor - simulate removing required fields
        def mock_run_editor(args: list[str], **kwargs: Any) -> MagicMock:  # noqa: ARG001
            # Overwrite manifest without required fields
            invalid_manifest = {"id": "test-app", "name": "Test App"}
            manifest_path.write_text(yaml.safe_dump(invalid_manifest))
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run_editor)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Run edit
        result = edit_app("test-app", config, auto_sync=True)

        # Verify validation failed
        assert result["validation_errors"] is not None
        assert any("Missing required fields" in err for err in result["validation_errors"])

        # Verify manifest was restored
        restored_manifest = yaml.safe_load(manifest_path.read_text())
        assert restored_manifest == original_manifest

    def test_edit_app_uses_fallback_editor(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit uses fallback editor when EDITOR not set."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create manifest
        manifest_path.parent.mkdir(parents=True)
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
                    "wrapper_script": str(tmp_path / "wrappers" / "test-app"),
                    "desktop_file": str(tmp_path / "desktop" / "test-app.desktop"),
                }
            ],
            "handlers": [],
        })

        # Mock no EDITOR but vi is available
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/vi" if x == "vi" else None)

        # Mock editor
        mock_subprocess = MagicMock()
        mock_subprocess.return_value.returncode = 0
        monkeypatch.setattr("subprocess.run", mock_subprocess)

        # Run edit
        result = edit_app("test-app", config, auto_sync=False)

        # Verify results
        assert result["edited"] is True

        # Verify vi was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0][0] == "vi"
