"""Unit tests for audit command."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
import yaml
from pwa_forge.commands.audit import AuditCommandError, audit_app
from pwa_forge.config import Config
from pwa_forge.registry import Registry


class TestAuditApp:
    """Test audit_app function."""

    def test_audit_app_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit fails when app not found."""
        config = Config()
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create empty registry
        registry = Registry(registry_file)
        registry._write({"version": 1, "apps": [], "handlers": []})

        with pytest.raises(AuditCommandError, match="not found in registry"):
            audit_app("nonexistent", config)

    def test_audit_all_apps_empty_registry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit all apps with empty registry."""
        config = Config()
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create empty registry
        registry = Registry(registry_file)
        registry._write({"version": 1, "apps": [], "handlers": []})

        result = audit_app(None, config)

        assert result["audited_apps"] == 0
        assert result["passed"] == 0
        assert result["failed"] == 0

    def test_audit_app_manifest_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit detects missing manifest."""
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

        result = audit_app("test-app", config)

        assert result["audited_apps"] == 1
        assert result["failed"] == 1
        assert any(
            check["status"] == "FAIL" and "Manifest" in check["name"] for check in result["results"][0]["checks"]
        )

    def test_audit_app_all_checks_pass(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit with all checks passing."""
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

        # Create directories
        manifest_path.parent.mkdir(parents=True)
        wrapper_path.parent.mkdir(parents=True)
        desktop_path.parent.mkdir(parents=True)

        # Create valid manifest
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
            "profile": str(tmp_path / "apps" / "test-app" / "profile"),
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create profile directory
        profile_path = tmp_path / "apps" / "test-app" / "profile"
        profile_path.mkdir(parents=True)

        # Create valid wrapper script
        wrapper_path.write_text("#!/bin/bash\necho 'test'")
        wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR)

        # Create valid desktop file
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=Test App
Exec={wrapper_path}
"""
        desktop_path.write_text(desktop_content)

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

        # Mock browser executable check
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/google-chrome-stable")

        result = audit_app("test-app", config)

        assert result["audited_apps"] == 1
        # Should pass (may have warnings but no failures)
        # Check that no FAIL status exists
        app_result = result["results"][0]
        failed_checks = [check for check in app_result["checks"] if check["status"] == "FAIL"]
        assert len(failed_checks) == 0, f"Failed checks: {failed_checks}"

    def test_audit_app_invalid_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit detects invalid YAML."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        manifest_path.parent.mkdir(parents=True)

        # Create invalid YAML
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

        result = audit_app("test-app", config)

        assert result["audited_apps"] == 1
        assert result["failed"] == 1
        app_result = result["results"][0]
        assert any("Invalid YAML" in check["message"] for check in app_result["checks"] if check["status"] == "FAIL")

    def test_audit_app_missing_required_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit detects missing required fields."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
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

        result = audit_app("test-app", config)

        assert result["audited_apps"] == 1
        assert result["failed"] == 1
        app_result = result["results"][0]
        assert any(
            "Missing required fields" in check["message"] for check in app_result["checks"] if check["status"] == "FAIL"
        )

    def test_audit_app_wrapper_not_executable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit detects non-executable wrapper script."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"
        wrapper_path = tmp_path / "wrappers" / "test-app"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        manifest_path.parent.mkdir(parents=True)
        wrapper_path.parent.mkdir(parents=True)

        # Create valid manifest
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create wrapper without execute permission
        wrapper_path.write_text("#!/bin/bash\necho 'test'")
        wrapper_path.chmod(0o644)  # Read/write but not executable

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
                    "desktop_file": str(tmp_path / "desktop" / "test-app.desktop"),
                }
            ],
            "handlers": [],
        })

        result = audit_app("test-app", config)

        assert result["audited_apps"] == 1
        app_result = result["results"][0]
        assert any(
            check["name"] == "Wrapper script executable" and check["status"] == "FAIL" for check in app_result["checks"]
        )

    def test_audit_multiple_apps(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit all apps."""
        config = Config()
        registry_file = tmp_path / "registry.json"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create registry with multiple apps
        registry = Registry(registry_file)
        registry._write({
            "version": 1,
            "apps": [
                {
                    "id": "app1",
                    "name": "App 1",
                    "manifest_path": str(tmp_path / "apps" / "app1" / "manifest.yaml"),
                    "wrapper_script": str(tmp_path / "wrappers" / "app1"),
                    "desktop_file": str(tmp_path / "desktop" / "app1.desktop"),
                },
                {
                    "id": "app2",
                    "name": "App 2",
                    "manifest_path": str(tmp_path / "apps" / "app2" / "manifest.yaml"),
                    "wrapper_script": str(tmp_path / "wrappers" / "app2"),
                    "desktop_file": str(tmp_path / "desktop" / "app2.desktop"),
                },
            ],
            "handlers": [],
        })

        result = audit_app(None, config)

        assert result["audited_apps"] == 2
        assert len(result["results"]) == 2

    def test_audit_app_fix_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit with fix mode regenerates files."""
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

        # Create directories
        manifest_path.parent.mkdir(parents=True)

        # Create valid manifest
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

        # Run audit with fix (wrapper and desktop files missing)
        result = audit_app("test-app", config, fix=True)

        assert result["audited_apps"] == 1
        assert result["fixed"] == 1

        # Verify files were created by sync
        assert wrapper_path.exists()
        assert desktop_path.exists()

        # Check for FIXED status in results
        app_result = result["results"][0]
        assert any(check["status"] == "FIXED" for check in app_result["checks"])

    def test_audit_desktop_file_invalid_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test audit detects invalid desktop file format."""
        config = Config()
        registry_file = tmp_path / "registry.json"
        manifest_path = tmp_path / "apps" / "test-app" / "manifest.yaml"
        desktop_path = tmp_path / "desktop" / "test-app.desktop"

        # Override registry_file property
        monkeypatch.setattr(Config, "registry_file", property(lambda self: registry_file))

        # Create directories
        manifest_path.parent.mkdir(parents=True)
        desktop_path.parent.mkdir(parents=True)

        # Create valid manifest
        manifest_data = {
            "id": "test-app",
            "name": "Test App",
            "url": "https://example.com",
            "browser": "chrome",
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data))

        # Create invalid desktop file (missing required keys)
        desktop_content = """[Desktop Entry]
Type=Application
"""
        desktop_path.write_text(desktop_content)

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
                    "desktop_file": str(desktop_path),
                }
            ],
            "handlers": [],
        })

        result = audit_app("test-app", config)

        assert result["audited_apps"] == 1
        app_result = result["results"][0]
        assert any(
            check["name"] == "Desktop file valid"
            and check["status"] == "FAIL"
            and "Missing required keys" in check["message"]
            for check in app_result["checks"]
        )
