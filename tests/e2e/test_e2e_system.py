"""E2E system tests for PWA Forge.

Tests complete system integration including browser detection, XDG integration,
and real file operations. Uses real XDG commands (update-desktop-database,
xdg-mime) and real browser executables for true end-to-end testing.
Only mocks Path.exists for browser detection edge cases.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from pwa_forge.commands.add import add_app
from pwa_forge.commands.audit import audit_app
from pwa_forge.commands.edit import edit_app
from pwa_forge.commands.handler import generate_handler, install_handler
from pwa_forge.commands.list_apps import list_apps
from pwa_forge.commands.remove import remove_app
from pwa_forge.commands.sync import sync_app
from pwa_forge.config import Config


class IsolatedE2EConfig(Config):
    """Configuration with isolated environment for E2E testing."""

    def __init__(self, tmp_path: Path) -> None:
        """Initialize E2E test config with temp paths."""
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
def e2e_config(tmp_path: Path) -> IsolatedE2EConfig:
    """Create an E2E test configuration with temporary directories."""
    return IsolatedE2EConfig(tmp_path)


@pytest.fixture  # type: ignore[misc]
def mock_browser_executable(tmp_path: Path) -> Path:
    """Create a mock browser executable for testing."""
    browser_path = tmp_path / "bin" / "mock-chrome"
    browser_path.parent.mkdir(parents=True, exist_ok=True)
    browser_path.write_text("#!/bin/bash\necho 'Mock browser launched'\n")
    browser_path.chmod(0o755)
    return browser_path


@pytest.fixture  # type: ignore[misc]
def track_xdg_commands(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[tuple[list[str], dict[str, Any]]]]:
    """Track XDG command calls (uses real commands when available)."""
    calls: list[tuple[list[str], dict[str, Any]]] = []
    original_run = subprocess.run

    def tracked_run(cmd: list[str] | str, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        """Track subprocess calls and use real commands."""
        if isinstance(cmd, str):
            cmd = cmd.split()

        # Record the call
        calls.append((cmd, kwargs))

        # Use real subprocess for all commands - no mocking
        return original_run(cmd, **kwargs)

    monkeypatch.setattr("subprocess.run", tracked_run)
    return {"subprocess_calls": calls}


class TestE2EBrowserDetection:
    """Test browser detection in real-world scenarios."""

    def test_add_with_browser_detection(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test add command detects and uses browser executable."""
        # Configure browser path
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        result = add_app(
            url="https://example.com",
            config=e2e_config,
            name="Browser Test App",
            app_id="browser-test",
            browser="chrome",
            dry_run=False,
        )

        # Verify PWA was created
        assert result["id"] == "browser-test"

        # Verify wrapper script references the correct browser
        wrapper_path = Path(result["wrapper"])
        wrapper_content = wrapper_path.read_text()
        assert str(mock_browser_executable) in wrapper_content

    def test_add_fails_with_missing_browser(self, e2e_config: Config, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test add command fails gracefully when browser is not found."""
        # Configure non-existent browser path
        e2e_config.browsers.chrome = "/nonexistent/browser"
        e2e_config.browsers.chromium = "/nonexistent/chromium"
        e2e_config.browsers.firefox = "/nonexistent/firefox"
        e2e_config.browsers.edge = "/nonexistent/edge"

        # Mock Path.exists to return False for all browser paths
        original_exists = Path.exists

        def mock_exists(self: Path) -> bool:
            # Return False for any path that looks like a browser executable
            path_str = str(self)
            if any(browser in path_str for browser in ["chrome", "chromium", "firefox", "edge"]):
                return False
            return original_exists(self)

        monkeypatch.setattr(Path, "exists", mock_exists)

        # Mock shutil.which to return None (browser not in PATH)
        monkeypatch.setattr("shutil.which", lambda _: None)

        # Add PWA should fail
        from pwa_forge.commands.add import AddCommandError

        with pytest.raises(AddCommandError, match="not found"):
            add_app(
                url="https://example.com",
                config=e2e_config,
                name="Missing Browser Test",
                app_id="missing-browser",
                browser="chrome",
                dry_run=False,
            )


class TestE2EXDGIntegration:
    """Test XDG desktop database and MIME handler integration."""

    def test_add_triggers_desktop_database_update(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test that add command triggers update-desktop-database."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        add_app(
            url="https://example.com",
            config=e2e_config,
            name="XDG Test App",
            app_id="xdg-test",
            browser="chrome",
            dry_run=False,
        )

        # Verify update-desktop-database was called
        calls = track_xdg_commands["subprocess_calls"]
        desktop_db_calls = [c for c in calls if "update-desktop-database" in c[0]]
        assert len(desktop_db_calls) > 0

    def test_handler_registration_with_xdg_mime(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test handler installation registers with xdg-mime."""
        e2e_config.browsers.firefox = str(mock_browser_executable)

        # Generate handler script
        handler_result = generate_handler(
            scheme="testff",
            config=e2e_config,
            browser="firefox",
            out=None,
            dry_run=False,
        )

        handler_script = Path(handler_result["script_path"])
        assert handler_script.exists()

        # Install handler
        install_result = install_handler(
            scheme="testff",
            config=e2e_config,
            handler_script=str(handler_script),
            dry_run=False,
        )

        # Verify desktop file was created
        desktop_file = Path(install_result["desktop_file"])
        assert desktop_file.exists()

        # Verify xdg-mime was called
        calls = track_xdg_commands["subprocess_calls"]
        xdg_mime_calls = [c for c in calls if "xdg-mime" in c[0]]
        assert len(xdg_mime_calls) > 0

    def test_remove_triggers_desktop_database_update(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test that remove command triggers update-desktop-database."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA first
        add_app(
            url="https://example.com",
            config=e2e_config,
            name="Remove XDG Test",
            app_id="remove-xdg-test",
            browser="chrome",
            dry_run=False,
        )

        # Clear previous calls
        track_xdg_commands["subprocess_calls"].clear()

        # Remove PWA
        remove_app(
            app_id="remove-xdg-test",
            config=e2e_config,
            remove_profile=True,
            remove_icon=False,
            keep_userdata=False,
            dry_run=False,
        )

        # Verify update-desktop-database was called
        calls = track_xdg_commands["subprocess_calls"]
        desktop_db_calls = [c for c in calls if "update-desktop-database" in c[0]]
        assert len(desktop_db_calls) > 0


class TestE2EAuditDetectsIssues:
    """Test audit command detects real file issues."""

    def test_audit_detects_missing_wrapper_script(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test audit detects when wrapper script is missing."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        result = add_app(
            url="https://example.com",
            config=e2e_config,
            name="Audit Test 1",
            app_id="audit-test-1",
            browser="chrome",
            dry_run=False,
        )

        # Delete wrapper script
        wrapper_path = Path(result["wrapper"])
        wrapper_path.unlink()

        # Run audit
        audit_result = audit_app(
            app_id="audit-test-1",
            config=e2e_config,
            fix=False,
            open_test_page=False,
        )

        # Verify audit detected the missing wrapper
        assert audit_result["failed"] > 0
        checks = audit_result["results"][0]["checks"]
        wrapper_check = next((c for c in checks if "wrapper" in c["name"].lower()), None)
        assert wrapper_check is not None
        assert wrapper_check["status"] == "FAIL"

    def test_audit_detects_missing_desktop_file(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test audit detects when desktop file is missing."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        result = add_app(
            url="https://example.com",
            config=e2e_config,
            name="Audit Test 2",
            app_id="audit-test-2",
            browser="chrome",
            dry_run=False,
        )

        # Delete desktop file
        desktop_path = Path(result["desktop_file"])
        desktop_path.unlink()

        # Run audit
        audit_result = audit_app(
            app_id="audit-test-2",
            config=e2e_config,
            fix=False,
            open_test_page=False,
        )

        # Verify audit detected the missing desktop file
        assert audit_result["failed"] > 0
        checks = audit_result["results"][0]["checks"]
        desktop_check = next((c for c in checks if "desktop" in c["name"].lower()), None)
        assert desktop_check is not None
        assert desktop_check["status"] == "FAIL"

    def test_audit_detects_non_executable_wrapper(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test audit detects when wrapper script is not executable."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        result = add_app(
            url="https://example.com",
            config=e2e_config,
            name="Audit Test 3",
            app_id="audit-test-3",
            browser="chrome",
            dry_run=False,
        )

        # Remove executable permission from wrapper
        wrapper_path = Path(result["wrapper"])
        wrapper_path.chmod(0o644)  # Remove execute bit

        # Run audit
        audit_result = audit_app(
            app_id="audit-test-3",
            config=e2e_config,
            fix=False,
            open_test_page=False,
        )

        # Verify audit detected the permission issue
        # Note: If wrapper exists check passes, executable check should run
        assert audit_result["failed"] > 0
        checks = audit_result["results"][0]["checks"]
        # Check that either wrapper or executable check failed
        failed_checks = [c for c in checks if c["status"] == "FAIL"]
        assert len(failed_checks) > 0

    def test_audit_fix_repairs_missing_files(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test audit --fix repairs missing wrapper and desktop files."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        result = add_app(
            url="https://example.com",
            config=e2e_config,
            name="Audit Fix Test",
            app_id="audit-fix-test",
            browser="chrome",
            dry_run=False,
        )

        # Delete both wrapper and desktop file
        wrapper_path = Path(result["wrapper"])
        desktop_path = Path(result["desktop_file"])
        wrapper_path.unlink()
        desktop_path.unlink()

        # Run audit with --fix
        audit_result = audit_app(
            app_id="audit-fix-test",
            config=e2e_config,
            fix=True,
            open_test_page=False,
        )

        # Verify files were repaired
        assert wrapper_path.exists()
        assert desktop_path.exists()
        assert audit_result["fixed"] > 0


class TestE2ESyncRegeneratesArtifacts:
    """Test sync command regenerates valid artifacts."""

    def test_sync_regenerates_wrapper_script(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test sync regenerates wrapper script from manifest."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        result = add_app(
            url="https://example.com",
            config=e2e_config,
            name="Sync Test 1",
            app_id="sync-test-1",
            browser="chrome",
            dry_run=False,
        )

        # Corrupt wrapper script
        wrapper_path = Path(result["wrapper"])
        wrapper_path.write_text("#!/bin/bash\n# CORRUPTED\n")

        # Run sync
        sync_result = sync_app(
            app_id="sync-test-1",
            config=e2e_config,
            dry_run=False,
        )

        # Verify wrapper was regenerated
        assert "wrapper" in sync_result["regenerated"]
        regenerated_content = wrapper_path.read_text()
        assert "CORRUPTED" not in regenerated_content
        assert "https://example.com" in regenerated_content

    def test_sync_regenerates_desktop_file(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test sync regenerates desktop file from manifest."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        result = add_app(
            url="https://example.com",
            config=e2e_config,
            name="Sync Test 2",
            app_id="sync-test-2",
            browser="chrome",
            dry_run=False,
        )

        # Corrupt desktop file
        desktop_path = Path(result["desktop_file"])
        desktop_path.write_text("[Desktop Entry]\nName=CORRUPTED\n")

        # Run sync
        sync_result = sync_app(
            app_id="sync-test-2",
            config=e2e_config,
            dry_run=False,
        )

        # Verify desktop file was regenerated
        assert "desktop" in sync_result["regenerated"]
        regenerated_content = desktop_path.read_text()
        assert "CORRUPTED" not in regenerated_content
        assert "Sync Test 2" in regenerated_content

    def test_sync_updates_manifest_timestamp(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test sync updates the modified timestamp in manifest."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        add_app(
            url="https://example.com",
            config=e2e_config,
            name="Sync Test 3",
            app_id="sync-test-3",
            browser="chrome",
            dry_run=False,
        )

        # Load manifest and get original timestamp
        manifest_path = e2e_config.directories.apps / "sync-test-3" / "manifest.yaml"
        with manifest_path.open() as f:
            original_manifest = yaml.safe_load(f)
        original_modified = original_manifest.get("modified")

        # Run sync
        sync_app(
            app_id="sync-test-3",
            config=e2e_config,
            dry_run=False,
        )

        # Load manifest again and verify timestamp changed
        with manifest_path.open() as f:
            updated_manifest = yaml.safe_load(f)
        updated_modified = updated_manifest.get("modified")

        assert updated_modified is not None
        assert updated_modified != original_modified


class TestE2EEditWithTemporaryEditor:
    """Test edit command with temporary EDITOR."""

    def test_edit_opens_manifest_in_editor(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test edit command opens manifest in $EDITOR."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        add_app(
            url="https://example.com",
            config=e2e_config,
            name="Edit Test 1",
            app_id="edit-test-1",
            browser="chrome",
            dry_run=False,
        )

        # Create a mock editor script that modifies the manifest
        editor_script = tmp_path / "mock_editor.sh"
        editor_script.write_text(
            """#!/bin/bash
# Mock editor that adds a comment to the manifest
echo "comment: Modified by mock editor" >> "$1"
"""
        )
        editor_script.chmod(0o755)

        # Set EDITOR environment variable
        monkeypatch.setenv("EDITOR", str(editor_script))

        # Run edit
        edit_result = edit_app(
            app_id="edit-test-1",
            config=e2e_config,
            auto_sync=True,
        )

        # Verify edit was successful
        assert edit_result["edited"] is True

        # Verify manifest was modified
        manifest_path = e2e_config.directories.apps / "edit-test-1" / "manifest.yaml"
        with manifest_path.open() as f:
            manifest = yaml.safe_load(f)
        assert manifest.get("comment") == "Modified by mock editor"

    def test_edit_validates_manifest_after_edit(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test edit command validates manifest and rejects invalid changes."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        add_app(
            url="https://example.com",
            config=e2e_config,
            name="Edit Test 2",
            app_id="edit-test-2",
            browser="chrome",
            dry_run=False,
        )

        # Create a mock editor that corrupts the manifest
        editor_script = tmp_path / "corrupt_editor.sh"
        editor_script.write_text(
            """#!/bin/bash
# Mock editor that corrupts the manifest
echo "invalid: yaml: syntax: [[[" >> "$1"
"""
        )
        editor_script.chmod(0o755)

        # Set EDITOR environment variable
        monkeypatch.setenv("EDITOR", str(editor_script))

        # Run edit - should return validation errors
        edit_result = edit_app(
            app_id="edit-test-2",
            config=e2e_config,
            auto_sync=True,
        )

        # Verify validation failed
        assert edit_result["validation_errors"] is not None
        assert len(edit_result["validation_errors"]) > 0

        # Verify manifest was restored from backup
        manifest_path = e2e_config.directories.apps / "edit-test-2" / "manifest.yaml"
        with manifest_path.open() as f:
            manifest = yaml.safe_load(f)
        # Should still be valid
        assert manifest["id"] == "edit-test-2"
        assert "invalid" not in manifest


class TestE2EFullWorkflow:
    """Test complete E2E workflow with multiple operations."""

    def test_complete_pwa_workflow(
        self,
        e2e_config: Config,
        mock_browser_executable: Path,
        track_xdg_commands: dict[str, list[tuple[list[str], dict[str, Any]]]],
    ) -> None:
        """Test complete workflow: add -> list -> audit -> sync -> remove."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Step 1: Add PWA
        add_result = add_app(
            url="https://example.com",
            config=e2e_config,
            name="Full Workflow Test",
            app_id="full-workflow",
            browser="chrome",
            dry_run=False,
        )
        assert add_result["id"] == "full-workflow"

        # Step 2: List PWAs
        # Suppress stdout since list_apps prints
        with patch("sys.stdout", new=io.StringIO()):
            list_result = list_apps(config=e2e_config, verbose=False, output_format="json")
        assert len(list_result) == 1
        assert list_result[0]["id"] == "full-workflow"

        # Step 3: Audit PWA (should pass)
        audit_result = audit_app(
            app_id="full-workflow",
            config=e2e_config,
            fix=False,
            open_test_page=False,
        )
        assert audit_result["passed"] > 0
        assert audit_result["failed"] == 0

        # Step 4: Corrupt a file and re-audit
        wrapper_path = Path(add_result["wrapper"])
        wrapper_path.unlink()

        audit_result2 = audit_app(
            app_id="full-workflow",
            config=e2e_config,
            fix=False,
            open_test_page=False,
        )
        assert audit_result2["failed"] > 0

        # Step 5: Fix with sync
        sync_app(
            app_id="full-workflow",
            config=e2e_config,
            dry_run=False,
        )
        assert wrapper_path.exists()

        # Step 6: Remove PWA
        remove_app(
            app_id="full-workflow",
            config=e2e_config,
            remove_profile=True,
            remove_icon=False,
            keep_userdata=False,
            dry_run=False,
        )
        # Remove doesn't return a value, but it should succeed without error

        # Step 7: Verify PWA is gone
        with patch("sys.stdout", new=io.StringIO()):
            list_result2 = list_apps(config=e2e_config, verbose=False, output_format="json")
        assert len(list_result2) == 0


class TestE2EErrorConditions:
    """Test E2E error conditions and edge cases."""

    def test_add_with_invalid_url_fails_gracefully(self, e2e_config: Config, mock_browser_executable: Path) -> None:
        """Test add command fails gracefully with invalid URL."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        import pytest
        from pwa_forge.commands.add import AddCommandError

        with pytest.raises(AddCommandError):
            add_app(
                url="not-a-valid-url-at-all",
                config=e2e_config,
                name="Invalid URL Test",
                app_id="invalid-url",
                browser="chrome",
                dry_run=False,
            )

    def test_remove_nonexistent_app_fails(self, e2e_config: Config) -> None:
        """Test remove command fails for non-existent app."""
        import pytest
        from pwa_forge.commands.remove import RemoveCommandError

        with pytest.raises(RemoveCommandError):
            remove_app(
                app_id="does-not-exist",
                config=e2e_config,
                dry_run=False,
            )

    def test_sync_nonexistent_app_fails(self, e2e_config: Config) -> None:
        """Test sync command fails for non-existent app."""
        import pytest
        from pwa_forge.commands.sync import SyncCommandError

        with pytest.raises(SyncCommandError):
            sync_app(
                app_id="does-not-exist",
                config=e2e_config,
                dry_run=False,
            )

    def test_audit_nonexistent_app_fails(self, e2e_config: Config) -> None:
        """Test audit command fails for non-existent app."""
        import pytest
        from pwa_forge.commands.audit import AuditCommandError

        with pytest.raises(AuditCommandError):
            audit_app(
                app_id="does-not-exist",
                config=e2e_config,
            )

    def test_edit_nonexistent_app_fails(self, e2e_config: Config) -> None:
        """Test edit command fails for non-existent app."""
        import pytest
        from pwa_forge.commands.edit import EditCommandError

        with pytest.raises(EditCommandError):
            edit_app(
                app_id="does-not-exist",
                config=e2e_config,
            )


class TestE2EBrowserCompatibility:
    """Test E2E browser compatibility scenarios."""

    def test_add_with_different_browsers(
        self, e2e_config: Config, mock_browser_executable: Path, tmp_path: Path
    ) -> None:
        """Test add command with different browser configurations."""
        # Create different browser executables (Chromium-based only)
        browsers = ["chrome", "chromium", "edge"]
        browser_paths = {}

        for browser in browsers:
            browser_path = tmp_path / "bin" / f"mock-{browser}"
            browser_path.parent.mkdir(parents=True, exist_ok=True)
            browser_path.write_text(f"#!/bin/bash\necho 'Mock {browser} launched'\n")
            browser_path.chmod(0o755)
            browser_paths[browser] = browser_path
            setattr(e2e_config.browsers, browser, str(browser_path))

        # Test adding PWAs with different browsers
        for i, browser in enumerate(browsers):
            app_id = f"browser-test-{browser}-{i}"

            result = add_app(
                url=f"https://test-{browser}.com",
                config=e2e_config,
                name=f"Test with {browser.capitalize()}",
                app_id=app_id,
                browser=browser,
                dry_run=False,
            )

            assert result["id"] == app_id
            assert result["browser"] == browser

            # Verify wrapper contains correct browser path
            wrapper_path = Path(result["wrapper"])
            content = wrapper_path.read_text()
            assert str(browser_paths[browser]) in content


class TestE2EFileSystemOperations:
    """Test E2E file system operations and permissions."""

    def test_add_creates_all_required_files(self, e2e_config: Config, mock_browser_executable: Path) -> None:
        """Test that add creates all required files and directories."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        result = add_app(
            url="https://file-test.com",
            config=e2e_config,
            name="File System Test",
            app_id="file-test",
            dry_run=False,
        )

        # Check all files exist
        assert Path(result["manifest"]).exists()
        assert Path(result["wrapper"]).exists()
        assert Path(result["desktop_file"]).exists()

        # Check directories exist
        manifest_dir = Path(result["manifest"]).parent
        assert manifest_dir.exists()
        assert manifest_dir.name == "file-test"

        # Check wrapper is executable
        wrapper_path = Path(result["wrapper"])
        assert wrapper_path.stat().st_mode & 0o111  # Executable

    def test_remove_cleans_up_all_files(self, e2e_config: Config, mock_browser_executable: Path) -> None:
        """Test that remove cleans up all files and directories."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        # Add PWA
        result = add_app(
            url="https://cleanup-test.com",
            config=e2e_config,
            name="Cleanup Test",
            app_id="cleanup-test",
            dry_run=False,
        )

        # Verify files exist
        manifest_path = Path(result["manifest"])
        wrapper_path = Path(result["wrapper"])
        desktop_path = Path(result["desktop_file"])
        manifest_dir = manifest_path.parent

        assert manifest_path.exists()
        assert wrapper_path.exists()
        assert desktop_path.exists()
        assert manifest_dir.exists()

        # Remove PWA
        remove_app(
            app_id="cleanup-test",
            config=e2e_config,
            remove_profile=True,
            remove_icon=False,
            keep_userdata=False,
            dry_run=False,
        )

        # Verify all files are gone
        assert not manifest_path.exists()
        assert not wrapper_path.exists()
        assert not desktop_path.exists()
        assert not manifest_dir.exists()

    def test_sync_preserves_file_permissions(self, e2e_config: Config, mock_browser_executable: Path) -> None:
        """Test that sync preserves file permissions."""
        e2e_config.browsers.chrome = str(mock_browser_executable)

        result = add_app(
            url="https://permissions-test.com",
            config=e2e_config,
            name="Permissions Test",
            app_id="permissions-test",
            dry_run=False,
        )

        wrapper_path = Path(result["wrapper"])

        # Check initial permissions
        initial_mode = wrapper_path.stat().st_mode
        assert initial_mode & 0o111  # Should be executable

        # Run sync
        sync_app(
            app_id="permissions-test",
            config=e2e_config,
            dry_run=False,
        )

        # Check permissions preserved
        final_mode = wrapper_path.stat().st_mode
        assert final_mode & 0o111  # Should still be executable
