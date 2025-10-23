"""Integration tests for audit, sync, and edit workflow."""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from pwa_forge.commands.add import add_app
from pwa_forge.commands.audit import audit_app
from pwa_forge.commands.edit import edit_app
from pwa_forge.commands.sync import sync_app
from pwa_forge.config import Config
from pwa_forge.registry import Registry


class TestAuditSyncEditWorkflow:
    """Test audit, sync, and edit workflow integration."""

    def test_audit_detects_missing_files_and_fix_repairs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that audit detects missing files and --fix repairs them."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        config.directories.icons = tmp_path / "icons"
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)
        config.directories.icons.mkdir(parents=True)

        # Create a valid manifest
        manifest_path = config.directories.apps / "test-app" / "manifest.yaml"
        manifest_path.parent.mkdir(parents=True)
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
            "wm_class": "TestApp",
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create registry entry WITHOUT creating actual wrapper/desktop files
        wrapper_path = config.directories.wrappers / "test-app"
        desktop_path = config.directories.desktop / "pwa-forge-test-app.desktop"

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

        # Run audit - should detect missing files
        audit_result = audit_app("test-app", config, fix=False)

        assert audit_result["audited_apps"] == 1
        assert audit_result["failed"] == 1
        app_result = audit_result["results"][0]
        assert any(check["status"] == "FAIL" and "Wrapper script" in check["name"] for check in app_result["checks"])
        assert any(check["status"] == "FAIL" and "Desktop file" in check["name"] for check in app_result["checks"])

        # Verify files don't exist yet
        assert not wrapper_path.exists()
        assert not desktop_path.exists()

        # Run audit with --fix
        audit_fix_result = audit_app("test-app", config, fix=True)

        assert audit_fix_result["fixed"] == 1

        # Verify files were created
        assert wrapper_path.exists()
        assert desktop_path.exists()

        # Verify wrapper is executable
        wrapper_stat = wrapper_path.stat()
        assert wrapper_stat.st_mode & stat.S_IXUSR

        # Verify desktop file has required content
        desktop_content = desktop_path.read_text()
        assert "Test App" in desktop_content
        assert str(wrapper_path) in desktop_content

    def test_edit_and_sync_workflow(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test editing manifest and syncing artifacts."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        # Create initial manifest and artifacts
        manifest_path = config.directories.apps / "test-app" / "manifest.yaml"
        wrapper_path = config.directories.wrappers / "test-app"
        desktop_path = config.directories.desktop / "pwa-forge-test-app.desktop"

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

        # Create initial artifacts with sync
        sync_result = sync_app("test-app", config)
        assert "wrapper" in sync_result["regenerated"]
        assert "desktop" in sync_result["regenerated"]

        initial_wrapper_content = wrapper_path.read_text()
        assert "https://example.com" in initial_wrapper_content

        # Mock editor to change the URL
        def mock_run_editor(args: list[str], **kwargs: Any) -> MagicMock:  # noqa: ARG001
            # Modify the manifest
            manifest = yaml.safe_load(manifest_path.read_text())
            manifest["url"] = "https://changed.example.com"
            manifest["name"] = "Changed Test App"
            manifest_path.write_text(yaml.safe_dump(manifest))
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run_editor)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Edit with auto-sync
        edit_result = edit_app("test-app", config, auto_sync=True)

        assert edit_result["edited"] is True
        assert edit_result["synced"] is True
        assert edit_result["validation_errors"] is None

        # Verify artifacts were updated
        updated_wrapper_content = wrapper_path.read_text()
        assert "https://changed.example.com" in updated_wrapper_content
        assert "https://example.com" not in updated_wrapper_content

        updated_desktop_content = desktop_path.read_text()
        assert "Changed Test App" in updated_desktop_content

    def test_manual_sync_after_edit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test manually syncing after editing with --no-sync."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        # Create manifest and registry
        manifest_path = config.directories.apps / "test-app" / "manifest.yaml"
        wrapper_path = config.directories.wrappers / "test-app"
        desktop_path = config.directories.desktop / "pwa-forge-test-app.desktop"

        manifest_path.parent.mkdir(parents=True)
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
            "wm_class": "TestApp",
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

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

        # Initial sync
        sync_app("test-app", config)

        # Mock editor
        def mock_run_editor(args: list[str], **kwargs: Any) -> MagicMock:  # noqa: ARG001
            manifest = yaml.safe_load(manifest_path.read_text())
            manifest["url"] = "https://new-url.example.com"
            manifest_path.write_text(yaml.safe_dump(manifest))
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run_editor)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Edit without sync
        edit_result = edit_app("test-app", config, auto_sync=False)
        assert edit_result["synced"] is False

        # Verify artifacts NOT updated yet
        wrapper_content = wrapper_path.read_text()
        assert "https://example.com" in wrapper_content
        assert "https://new-url.example.com" not in wrapper_content

        # Manually sync
        sync_result = sync_app("test-app", config)
        assert "wrapper" in sync_result["regenerated"]

        # Verify artifacts NOW updated
        updated_wrapper_content = wrapper_path.read_text()
        assert "https://new-url.example.com" in updated_wrapper_content

    def test_audit_after_manual_modification(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit detects when files are manually modified."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        # Create manifest and artifacts
        manifest_path = config.directories.apps / "test-app" / "manifest.yaml"
        wrapper_path = config.directories.wrappers / "test-app"
        desktop_path = config.directories.desktop / "pwa-forge-test-app.desktop"

        manifest_path.parent.mkdir(parents=True)
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
            "wm_class": "TestApp",
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

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

        # Create initial artifacts
        sync_app("test-app", config)

        # Audit should pass
        audit_result = audit_app("test-app", config)
        assert audit_result["failed"] == 0

        # Manually break the wrapper script (remove execute permission)
        wrapper_path.chmod(0o644)

        # Audit should now fail
        audit_result = audit_app("test-app", config)
        assert audit_result["failed"] == 1
        app_result = audit_result["results"][0]
        assert any(
            check["name"] == "Wrapper script executable" and check["status"] == "FAIL" for check in app_result["checks"]
        )

        # Fix with audit --fix
        audit_fix_result = audit_app("test-app", config, fix=True)
        assert audit_fix_result["fixed"] == 1

        # Verify wrapper is executable again
        wrapper_stat = wrapper_path.stat()
        assert wrapper_stat.st_mode & stat.S_IXUSR

    def test_complete_workflow_add_audit_edit_sync(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete workflow: add, audit, edit, sync."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        config.directories.icons = tmp_path / "icons"
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        for directory in [
            config.directories.apps,
            config.directories.wrappers,
            config.directories.desktop,
            config.directories.icons,
        ]:
            directory.mkdir(parents=True)

        # Mock subprocess for xdg-utils
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=0)))

        # Step 1: Add a PWA
        add_result = add_app(
            url="https://example.com",
            config=config,
            name="Example App",
            browser="chrome",
            dry_run=False,
        )

        assert add_result["id"] == "example-app"

        # Step 2: Audit - should pass
        audit_result = audit_app("example-app", config)
        assert audit_result["audited_apps"] == 1
        # May have warnings but should not fail
        passed_checks = audit_result["results"][0]["passed"]
        assert passed_checks > 0

        # Step 3: Edit manifest (mock editor)
        def mock_run_editor(args: list[str], **kwargs: Any) -> MagicMock:  # noqa: ARG001
            manifest_path = Path(args[1])
            manifest = yaml.safe_load(manifest_path.read_text())
            manifest["name"] = "Updated Example App"
            manifest["wm_class"] = "UpdatedExampleApp"
            manifest_path.write_text(yaml.safe_dump(manifest))
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run_editor)
        monkeypatch.setenv("EDITOR", "mock-editor")

        edit_result = edit_app("example-app", config, auto_sync=False)
        assert edit_result["edited"] is True

        # Step 4: Sync after edit
        # Need to restore subprocess mock for sync
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=0)))

        sync_result = sync_app("example-app", config)
        assert "wrapper" in sync_result["regenerated"]
        assert "desktop" in sync_result["regenerated"]

        # Verify updated name appears in artifacts
        desktop_path = config.directories.desktop / "pwa-forge-example-app.desktop"

        desktop_content = desktop_path.read_text()
        assert "Updated Example App" in desktop_content

        # Step 5: Final audit - should still pass
        audit_final_result = audit_app("example-app", config)
        assert audit_final_result["failed"] == 0
