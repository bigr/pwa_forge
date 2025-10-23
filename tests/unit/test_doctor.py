"""Unit tests for doctor command operations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pwa_forge.commands.doctor import run_doctor
from pwa_forge.config import get_default_config


class TestDoctorCommand:
    """Test doctor command."""

    def test_run_doctor_returns_structure(self) -> None:
        """Test that run_doctor returns the expected structure."""
        config = get_default_config()
        result = run_doctor(config)

        assert "checks" in result
        assert "passed" in result
        assert "failed" in result
        assert "warnings" in result
        assert isinstance(result["checks"], list)
        assert isinstance(result["passed"], int)
        assert isinstance(result["failed"], int)
        assert isinstance(result["warnings"], int)

    def test_python_version_check_passes(self) -> None:
        """Test that Python version check passes for Python 3.10+."""
        from pwa_forge.commands.doctor import _check_python_version

        result = _check_python_version()

        # Should pass since we're running with Python 3.10+ (project requirement)
        assert result["name"] == "Python Version"
        assert result["status"] == "PASS"

    def test_browser_check_detects_browsers(self) -> None:
        """Test that browser check detects available browsers."""
        from pwa_forge.commands.doctor import _check_browsers

        config = get_default_config()
        results = _check_browsers(config)

        assert isinstance(results, list)
        assert len(results) > 0

        # Check structure of each result
        for result in results:
            assert "name" in result
            assert "status" in result
            assert "message" in result
            assert "details" in result
            assert result["status"] in ["PASS", "WARNING", "FAIL"]

    def test_xdg_tools_check(self) -> None:
        """Test XDG tools check."""
        from pwa_forge.commands.doctor import _check_xdg_tools

        results = _check_xdg_tools()

        assert isinstance(results, list)
        # Should check for xdg-mime and update-desktop-database
        assert len(results) >= 2

        for result in results:
            assert "xdg" in result["name"].lower() or "tool" in result["name"].lower()
            assert result["status"] in ["PASS", "FAIL"]

    def test_directory_permissions_check(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test directory permissions check."""
        from pwa_forge.commands.doctor import _check_directory_permissions
        from pwa_forge.config import DirectoryConfig

        # Create a test config with temp paths
        config = get_default_config()

        # Create directory config with test paths
        test_dirs = tmp_path / "pwa_forge_test"
        test_dir_config = DirectoryConfig(
            desktop=test_dirs / "desktop",
            icons=test_dirs / "icons",
            wrappers=test_dirs / "wrappers",
            apps=test_dirs / "apps",
            userscripts=test_dirs / "userscripts",
        )
        monkeypatch.setattr(config, "directories", test_dir_config)

        results = _check_directory_permissions(config)

        assert isinstance(results, list)
        assert len(results) == 5  # Five directories checked

        for result in results:
            assert "Directory" in result["name"]
            # Since we're using tmp_path, all should pass
            assert result["status"] == "PASS"

    def test_desktop_environment_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test desktop environment check."""
        from pwa_forge.commands.doctor import _check_desktop_environment

        # Test with DE set
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
        monkeypatch.setenv("XDG_SESSION_TYPE", "x11")

        result = _check_desktop_environment()

        assert result["name"] == "Desktop Environment"
        assert result["status"] == "PASS"
        assert "KDE" in result["message"]

    def test_desktop_environment_check_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test desktop environment check when not detected."""
        from pwa_forge.commands.doctor import _check_desktop_environment

        # Remove DE env vars
        monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)

        result = _check_desktop_environment()

        assert result["name"] == "Desktop Environment"
        assert result["status"] == "WARNING"

    def test_config_file_check_no_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config file check when file doesn't exist."""
        from pwa_forge.commands.doctor import _check_config_file

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.doctor.get_app_config_dir", lambda: config_dir)

        result = _check_config_file()

        assert result["name"] == "Config File"
        assert result["status"] == "INFO"
        assert "Not found" in result["message"]

    def test_config_file_check_valid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config file check with valid config."""
        import yaml
        from pwa_forge.commands.doctor import _check_config_file

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        with config_file.open("w") as f:
            yaml.safe_dump({"default_browser": "firefox"}, f)

        monkeypatch.setattr("pwa_forge.commands.doctor.get_app_config_dir", lambda: config_dir)

        result = _check_config_file()

        assert result["name"] == "Config File"
        assert result["status"] == "PASS"

    def test_config_file_check_invalid_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config file check with invalid YAML."""
        from pwa_forge.commands.doctor import _check_config_file

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_file.write_text("invalid: yaml: syntax:")

        monkeypatch.setattr("pwa_forge.commands.doctor.get_app_config_dir", lambda: config_dir)

        result = _check_config_file()

        assert result["name"] == "Config File"
        assert result["status"] == "FAIL"
        assert "Invalid YAML" in result["details"]

    def test_registry_file_check_no_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test registry file check when file doesn't exist."""
        from pwa_forge.commands.doctor import _check_registry_file

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.doctor.get_app_data_dir", lambda: data_dir)

        result = _check_registry_file()

        assert result["name"] == "Registry File"
        assert result["status"] == "INFO"
        assert "Not found" in result["message"]

    def test_registry_file_check_valid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test registry file check with valid registry."""
        import json

        from pwa_forge.commands.doctor import _check_registry_file

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        registry_file = data_dir / "registry.json"

        registry_data = {"version": 1, "apps": [], "handlers": []}
        with registry_file.open("w") as f:
            json.dump(registry_data, f)

        monkeypatch.setattr("pwa_forge.commands.doctor.get_app_data_dir", lambda: data_dir)

        result = _check_registry_file()

        assert result["name"] == "Registry File"
        assert result["status"] == "PASS"

    def test_registry_file_check_invalid_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test registry file check with invalid JSON."""
        from pwa_forge.commands.doctor import _check_registry_file

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        registry_file = data_dir / "registry.json"

        registry_file.write_text("{invalid json")

        monkeypatch.setattr("pwa_forge.commands.doctor.get_app_data_dir", lambda: data_dir)

        result = _check_registry_file()

        assert result["name"] == "Registry File"
        assert result["status"] == "FAIL"
        assert "Invalid JSON" in result["details"]

    def test_playwright_check_not_installed(self) -> None:
        """Test Playwright check when not installed."""
        from pwa_forge.commands.doctor import _check_playwright

        with patch("builtins.__import__", side_effect=ImportError):
            result = _check_playwright()

            assert "Playwright" in result["name"]
            assert result["status"] == "INFO"
            assert "Not installed" in result["message"]

    def test_playwright_check_installed(self) -> None:
        """Test Playwright check when installed."""
        from pwa_forge.commands.doctor import _check_playwright

        # Mock successful import
        with patch("builtins.__import__") as mock_import:
            mock_import.return_value = MagicMock()

            # Mock subprocess for version check
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="Version 1.40.0")

                result = _check_playwright()

                assert "Playwright" in result["name"]
                assert result["status"] == "PASS"

    def test_doctor_counts_results_correctly(self) -> None:
        """Test that doctor correctly counts passed, failed, and warnings."""
        config = get_default_config()
        result = run_doctor(config)

        # Verify counts match actual checks
        passed = sum(1 for c in result["checks"] if c["status"] == "PASS")
        failed = sum(1 for c in result["checks"] if c["status"] == "FAIL")
        warnings = sum(1 for c in result["checks"] if c["status"] == "WARNING")

        assert result["passed"] == passed
        assert result["failed"] == failed
        assert result["warnings"] == warnings
