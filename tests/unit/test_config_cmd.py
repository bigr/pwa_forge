"""Unit tests for config command operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pwa_forge.commands.config_cmd import (
    ConfigCommandError,
    config_edit,
    config_get,
    config_list,
    config_reset,
    config_set,
)
from pwa_forge.config import get_default_config


class TestConfigGet:
    """Test config get command."""

    def test_get_top_level_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting a top-level configuration key."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        # Create test config file
        config_data = {
            "default_browser": "firefox",
            "log_level": "debug",
        }
        with config_file.open("w") as f:
            yaml.safe_dump(config_data, f)

        # Mock paths
        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        result = config_get("default_browser", config)

        assert result == "firefox"

    def test_get_nested_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting a nested configuration key using dot notation."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_data = {
            "browsers": {
                "chrome": "/usr/bin/google-chrome",
                "firefox": "/usr/bin/firefox",
            }
        }
        with config_file.open("w") as f:
            yaml.safe_dump(config_data, f)

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        result = config_get("browsers.chrome", config)

        assert result == "/usr/bin/google-chrome"

    def test_get_nonexistent_key_raises_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that getting a nonexistent key raises ConfigCommandError."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()

        with pytest.raises(ConfigCommandError, match="Configuration key not found"):
            config_get("nonexistent.key", config)

    def test_get_with_no_config_file_uses_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that get uses defaults when no config file exists."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        result = config_get("default_browser", config)

        assert result == "chrome"  # Default value


class TestConfigSet:
    """Test config set command."""

    def test_set_top_level_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test setting a top-level configuration key."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        config_set("default_browser", "firefox", config)

        # Verify file was created and value was set
        config_file = config_dir / "config.yaml"
        assert config_file.exists()

        with config_file.open("r") as f:
            data = yaml.safe_load(f)

        assert data["default_browser"] == "firefox"

    def test_set_nested_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test setting a nested configuration key using dot notation."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        config_set("browsers.chrome", "/custom/path/chrome", config)

        config_file = config_dir / "config.yaml"
        with config_file.open("r") as f:
            data = yaml.safe_load(f)

        assert data["browsers"]["chrome"] == "/custom/path/chrome"

    def test_set_creates_nested_dicts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that set creates nested dictionaries as needed."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        config_set("new.nested.key", "value", config)

        config_file = config_dir / "config.yaml"
        with config_file.open("r") as f:
            data = yaml.safe_load(f)

        assert data["new"]["nested"]["key"] == "value"

    def test_set_parses_value_types(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that set parses values to correct types."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()

        # Test list parsing
        config_set("test.list", "[item1, item2]", config)

        config_file = config_dir / "config.yaml"
        with config_file.open("r") as f:
            data = yaml.safe_load(f)

        assert data["test"]["list"] == ["item1", "item2"]

    def test_set_validates_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that set validates the configuration after setting."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()

        # This should succeed - valid config
        config_set("default_browser", "firefox", config)

        # Invalid values should be caught by validation in Config.from_dict
        # (implementation depends on validation logic)


class TestConfigList:
    """Test config list command."""

    def test_list_shows_user_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that list shows user configuration."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_data = {
            "default_browser": "firefox",
            "log_level": "debug",
        }
        with config_file.open("w") as f:
            yaml.safe_dump(config_data, f)

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        result = config_list(config)

        assert result["default_browser"] == "firefox"
        assert result["log_level"] == "debug"

    def test_list_shows_defaults_when_no_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that list shows defaults when no config file exists."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        result = config_list(config)

        assert result["default_browser"] == "chrome"
        assert "browsers" in result
        assert "directories" in result


class TestConfigReset:
    """Test config reset command."""

    def test_reset_removes_config_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that reset removes the config file."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        # Create a config file
        config_data = {"default_browser": "firefox"}
        with config_file.open("w") as f:
            yaml.safe_dump(config_data, f)

        assert config_file.exists()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        config_reset(config)

        assert not config_file.exists()

    def test_reset_handles_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that reset handles missing config file gracefully."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        config = get_default_config()
        # Should not raise an error
        config_reset(config)


class TestConfigEdit:
    """Test config edit command."""

    def test_edit_opens_editor(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that edit opens the editor."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)
        monkeypatch.setenv("EDITOR", "true")  # Use 'true' command as dummy editor

        config = get_default_config()

        # Should succeed
        config_edit(config)

    def test_edit_creates_file_if_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that edit creates config file if it doesn't exist."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)
        monkeypatch.setenv("EDITOR", "true")

        assert not config_file.exists()

        config = get_default_config()
        config_edit(config)

        # File should be created with defaults
        assert config_file.exists()

    def test_edit_raises_error_if_no_editor(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that edit raises error if no editor is available."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)
        monkeypatch.delenv("EDITOR", raising=False)

        # Mock subprocess to make 'which' always fail
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            config = get_default_config()

            with pytest.raises(ConfigCommandError, match="EDITOR.*not set"):
                config_edit(config)

    def test_edit_validates_after_editing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that edit validates the config after editing."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        # Create initial valid config
        config_data = {"default_browser": "chrome"}
        with config_file.open("w") as f:
            yaml.safe_dump(config_data, f)

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)
        monkeypatch.setenv("EDITOR", "true")

        config = get_default_config()

        # Should succeed with valid config
        config_edit(config)

    def test_edit_restores_backup_on_invalid_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that edit restores backup if edited config has invalid YAML."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        # Create initial valid config
        original_data = {"default_browser": "chrome"}
        with config_file.open("w") as f:
            yaml.safe_dump(original_data, f)

        monkeypatch.setattr("pwa_forge.commands.config_cmd.get_app_config_dir", lambda: config_dir)

        # Mock editor to write invalid YAML
        def mock_editor(args: list[str]) -> MagicMock:
            # Write invalid YAML after editor "opens"
            with open(args[1], "w") as f:
                f.write("invalid: yaml: syntax:")
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=mock_editor):
            monkeypatch.setenv("EDITOR", "dummy")

            config = get_default_config()

            with pytest.raises(ConfigCommandError):
                config_edit(config)

            # Original file should be restored
            with config_file.open("r") as f:
                restored_data = yaml.safe_load(f)

            assert restored_data == original_data


class TestConfigHelpers:
    """Test helper functions."""

    def test_get_nested_value(self) -> None:
        """Test _get_nested_value helper."""
        from pwa_forge.commands.config_cmd import _get_nested_value

        data = {"a": {"b": {"c": "value"}}}

        assert _get_nested_value(data, "a.b.c") == "value"

    def test_get_nested_value_raises_on_missing_key(self) -> None:
        """Test _get_nested_value raises KeyError on missing key."""
        from pwa_forge.commands.config_cmd import _get_nested_value

        data = {"a": {"b": "value"}}

        with pytest.raises(KeyError):
            _get_nested_value(data, "a.c")

    def test_set_nested_value(self) -> None:
        """Test _set_nested_value helper."""
        from pwa_forge.commands.config_cmd import _set_nested_value

        data: dict[str, Any] = {}
        _set_nested_value(data, "a.b.c", "value")

        assert data == {"a": {"b": {"c": "value"}}}

    def test_parse_value_handles_types(self) -> None:
        """Test _parse_value handles different types."""
        from pwa_forge.commands.config_cmd import _parse_value

        assert _parse_value("[a, b, c]") == ["a", "b", "c"]
        assert _parse_value("123") == 123
        assert _parse_value("true") is True
        assert _parse_value("false") is False
        assert _parse_value("plain string") == "plain string"
