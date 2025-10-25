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

    def test_audit_missing_manifest_path_in_registry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit detects missing manifest_path in registry."""
        config = Config()
        registry_file = tmp_path / "registry.json"

        # Mock the registry_file property to return our test file
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        registry = Registry(registry_file)

        # Add app with missing manifest_path
        registry.add_app({
            "id": "no-manifest-path",
            "name": "Test App",
            "url": "https://example.com",
            "desktop_file": "/tmp/test.desktop",
            "wrapper_script": "/tmp/test-wrapper",
            # manifest_path is missing
        })

        # Audit should detect missing manifest_path
        result = audit_app(app_id="no-manifest-path", config=config)

        assert result["audited_apps"] == 1
        assert result["failed"] == 1
        assert result["passed"] == 0

        # Check that the manifest path check failed
        app_result = result["results"][0]
        assert app_result["id"] == "no-manifest-path"
        manifest_check = next((c for c in app_result["checks"] if "Manifest path in registry" in c["name"]), None)
        assert manifest_check is not None
        assert manifest_check["status"] == "FAIL"
        assert "No manifest_path in registry entry" in manifest_check["message"]

    def test_audit_browser_executable_checks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit checks browser executable existence."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"

        # Mock the registry_file property to return our test file
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        # Mock subprocess for xdg-utils
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=0)))

        # Add PWA with chrome browser
        result = add_app(
            url="https://browser-test.com",
            config=config,
            name="Browser Test",
            app_id="browser-test",
            browser="chrome",
            dry_run=False,
        )

        # Set browser config to a non-existent path
        config.browsers.chrome = "/nonexistent/chrome"

        # Mock shutil.which to also return None for chrome
        import shutil

        original_which = shutil.which

        def mock_which(cmd: str) -> str | None:
            if cmd in ("google-chrome-stable", "google-chrome", "chrome"):
                return None
            return original_which(cmd)

        monkeypatch.setattr("shutil.which", mock_which)

        # Audit should detect missing browser
        result = audit_app(app_id=None, config=config)

        app_result = next(r for r in result["results"] if r["id"] == "browser-test")
        browser_check = next((c for c in app_result["checks"] if "Browser executable" in c["name"]), None)
        assert browser_check is not None
        assert browser_check["status"] == "FAIL"
        assert "Browser not found: chrome" in browser_check["message"]

    def test_audit_icon_file_checks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit checks icon file existence."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        config.directories.icons = tmp_path / "icons"
        registry_file = tmp_path / "registry.json"
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

        # Add PWA
        result = add_app(
            url="https://icon-test.com",
            config=config,
            name="Icon Test",
            app_id="icon-test",
            dry_run=False,
        )

        # Add icon field to manifest
        manifest_path = Path(result["manifest"])
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        manifest["icon"] = "/nonexistent/icon.svg"
        with open(manifest_path, "w") as f:
            yaml.safe_dump(manifest, f)

        # Audit should detect missing icon
        result = audit_app(app_id=None, config=config)

        app_result = next(r for r in result["results"] if r["id"] == "icon-test")
        icon_check = next((c for c in app_result["checks"] if "Icon file" in c["name"]), None)
        assert icon_check is not None
        assert icon_check["status"] == "WARNING"
        assert "Icon not found:" in icon_check["message"]

    def test_audit_profile_directory_checks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit checks profile directory existence."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        # Mock subprocess for xdg-utils
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=0)))

        # Add PWA
        result = add_app(
            url="https://profile-test.com",
            config=config,
            name="Profile Test",
            app_id="profile-test",
            dry_run=False,
        )

        # Modify manifest to point to non-existent profile
        manifest_path = Path(result["manifest"])
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        manifest["profile"] = "/nonexistent/profile/dir"
        with open(manifest_path, "w") as f:
            yaml.safe_dump(manifest, f)

        # Audit should detect missing profile directory
        result = audit_app(app_id=None, config=config)

        app_result = next(r for r in result["results"] if r["id"] == "profile-test")
        profile_check = next((c for c in app_result["checks"] if "Profile directory" in c["name"]), None)
        assert profile_check is not None
        assert profile_check["status"] == "WARNING"
        assert "Profile directory not found:" in profile_check["message"]

    def test_audit_desktop_file_validation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit validates desktop file format."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        # Mock subprocess for xdg-utils
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=0)))

        # Add PWA
        result = add_app(
            url="https://desktop-test.com",
            config=config,
            name="Desktop Test",
            app_id="desktop-test",
            dry_run=False,
        )

        # Corrupt the desktop file
        desktop_path = Path(result["desktop_file"])
        desktop_path.write_text("[Invalid]\nName=Test\n")  # Missing Desktop Entry section

        # Audit should detect invalid desktop file
        result = audit_app(app_id=None, config=config)

        app_result = next(r for r in result["results"] if r["id"] == "desktop-test")
        desktop_check = next((c for c in app_result["checks"] if "Desktop file valid" in c["name"]), None)
        assert desktop_check is not None
        assert desktop_check["status"] == "FAIL"
        assert "Missing [Desktop Entry] section" in desktop_check["message"]

    def test_audit_handler_registration_check(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit checks handler registration for userscripts."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        # Mock xdg-mime to simulate no handler registered
        import subprocess

        original_run = subprocess.run

        def mock_run(cmd, **kwargs):
            if "xdg-mime" in cmd and "query" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")
            return original_run(cmd, **kwargs)

        monkeypatch.setattr("subprocess.run", mock_run)

        # Mock subprocess for xdg-utils in add_app
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=0)))

        # Add PWA with userscript injection
        result = add_app(
            url="https://handler-test.com",
            config=config,
            name="Handler Test",
            app_id="handler-test",
            dry_run=False,
        )

        # Add inject config to manifest
        manifest_path = Path(result["manifest"])
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        manifest["inject"] = {"userscript_scheme": "test"}
        with open(manifest_path, "w") as f:
            yaml.safe_dump(manifest, f)

        # Restore the xdg-mime mock for audit
        monkeypatch.setattr("subprocess.run", mock_run)

        # Audit should check handler registration
        result = audit_app(app_id=None, config=config)

        app_result = next(r for r in result["results"] if r["id"] == "handler-test")
        handler_check = next((c for c in app_result["checks"] if "Handler for test://" in c["name"]), None)
        assert handler_check is not None
        assert handler_check["status"] == "WARNING"
        assert "No handler registered for test://" in handler_check["message"]

    def test_audit_fix_functionality(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit --fix repairs missing files."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        # Mock subprocess for xdg-utils
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=0)))

        # Add PWA
        result = add_app(
            url="https://fix-test.com",
            config=config,
            name="Fix Test",
            app_id="fix-test",
            dry_run=False,
        )

        # Remove wrapper script to simulate missing file
        wrapper_path = Path(result["wrapper"])
        wrapper_path.unlink()

        # Verify it's missing
        assert not wrapper_path.exists()

        # Audit with fix should regenerate wrapper
        result = audit_app(app_id=None, config=config, fix=True)

        app_result = next(r for r in result["results"] if r["id"] == "fix-test")
        assert app_result["fixed"] == 1

        # Wrapper should be regenerated
        assert wrapper_path.exists()

        # Check should be marked as FIXED
        wrapper_check = next((c for c in app_result["checks"] if "Wrapper script exists" in c["name"]), None)
        assert wrapper_check is not None
        assert wrapper_check["status"] == "FIXED"


class TestEditCommandIntegration:
    """Comprehensive integration tests for edit command."""

    def test_edit_changes_app_name_and_syncs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit changes name and syncs artifacts."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        for directory in [config.directories.apps, config.directories.wrappers, config.directories.desktop]:
            directory.mkdir(parents=True)

        # Mock subprocess for sync
        monkeypatch.setattr("subprocess.run", MagicMock(returncode=0))

        # Add initial PWA
        result = add_app(
            url="https://edit-test.com",
            config=config,
            name="Original Name",
            app_id="edit-test",
            dry_run=False,
        )

        manifest_path = Path(result["manifest"])
        wrapper_path = Path(result["wrapper"])
        desktop_path = Path(result["desktop_file"])

        # Verify initial artifacts
        assert "Original Name" in wrapper_path.read_text()
        assert "Original Name" in desktop_path.read_text()

        # Mock editor to change name
        def mock_editor(args, **kwargs):
            manifest = yaml.safe_load(manifest_path.read_text())
            manifest["name"] = "Updated Name"
            manifest_path.write_text(yaml.safe_dump(manifest))
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", mock_editor)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Edit with auto-sync
        edit_result = edit_app("edit-test", config, auto_sync=True)

        assert edit_result["edited"] is True
        assert edit_result["synced"] is True

        # Verify artifacts were updated
        assert "Updated Name" in wrapper_path.read_text()
        assert "Updated Name" in desktop_path.read_text()

    def test_edit_validation_failure_rollback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit rolls back changes when validation fails."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"

        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        for directory in [config.directories.apps, config.directories.wrappers, config.directories.desktop]:
            directory.mkdir(parents=True)

        monkeypatch.setattr("subprocess.run", MagicMock(returncode=0))

        # Add PWA
        result = add_app(
            url="https://rollback-test.com",
            config=config,
            name="Rollback Test",
            app_id="rollback-test",
            dry_run=False,
        )

        manifest_path = Path(result["manifest"])
        original_content = manifest_path.read_text()

        # Mock editor to create invalid YAML
        def mock_editor(args, **kwargs):
            manifest_path.write_text("invalid: yaml: content: [unclosed")
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", mock_editor)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Edit should fail and rollback
        edit_result = edit_app("rollback-test", config, auto_sync=False)

        # Edit occurred but validation failed, so edited=True with validation_errors
        assert edit_result["edited"] is True
        assert edit_result["synced"] is False
        assert "validation_errors" in edit_result
        assert len(edit_result["validation_errors"]) > 0

        # Manifest should be restored
        assert manifest_path.read_text() == original_content

    def test_edit_without_auto_sync(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit without auto-sync leaves artifacts unchanged."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"

        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        for directory in [config.directories.apps, config.directories.wrappers, config.directories.desktop]:
            directory.mkdir(parents=True)

        monkeypatch.setattr("subprocess.run", MagicMock(returncode=0))

        # Add PWA
        result = add_app(
            url="https://no-sync-test.com",
            config=config,
            name="No Sync Test",
            app_id="no-sync-test",
            dry_run=False,
        )

        manifest_path = Path(result["manifest"])
        wrapper_path = Path(result["wrapper"])

        # Mock editor to change URL
        def mock_editor(args, **kwargs):
            manifest = yaml.safe_load(manifest_path.read_text())
            manifest["url"] = "https://updated-url.com"
            manifest_path.write_text(yaml.safe_dump(manifest))
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", mock_editor)
        monkeypatch.setenv("EDITOR", "mock-editor")

        # Edit without auto-sync
        edit_result = edit_app("no-sync-test", config, auto_sync=False)

        assert edit_result["edited"] is True
        assert edit_result["synced"] is False

        # Wrapper should still have old URL
        wrapper_content = wrapper_path.read_text()
        assert "https://no-sync-test.com" in wrapper_content
        assert "https://updated-url.com" not in wrapper_content

    def test_edit_nonexistent_app_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit fails for non-existent app."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        import pytest
        from pwa_forge.commands.edit import EditCommandError

        with pytest.raises(EditCommandError):
            edit_app("nonexistent", config)

    def test_edit_missing_editor_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test edit fails when EDITOR is not set."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.desktop = tmp_path / "desktop"
        registry_file = tmp_path / "registry.json"

        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        config.directories.apps.mkdir(parents=True)
        config.directories.wrappers.mkdir(parents=True)
        config.directories.desktop.mkdir(parents=True)

        monkeypatch.setattr("subprocess.run", MagicMock(returncode=0))

        # Add PWA
        add_app(
            url="https://editor-test.com",
            config=config,
            name="Editor Test",
            app_id="editor-test",
            dry_run=False,
        )

        # Remove EDITOR env var and mock shutil.which to return None for fallback editors
        monkeypatch.delenv("EDITOR", raising=False)

        monkeypatch.setattr("shutil.which", lambda cmd: None)

        import pytest
        from pwa_forge.commands.edit import EditCommandError

        with pytest.raises(EditCommandError):
            edit_app("editor-test", config)
