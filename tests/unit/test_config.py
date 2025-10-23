"""Unit tests for configuration management."""

from __future__ import annotations

from pathlib import Path

import yaml
from pwa_forge import config


class TestBrowserConfig:
    """Test BrowserConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default browser paths."""
        browser_config = config.BrowserConfig()
        assert browser_config.chrome == "/usr/bin/google-chrome-stable"
        assert browser_config.chromium == "/usr/bin/chromium"
        assert browser_config.firefox == "/usr/bin/firefox"
        assert browser_config.edge == "/usr/bin/microsoft-edge"

    def test_custom_values(self) -> None:
        """Test custom browser paths."""
        browser_config = config.BrowserConfig(
            chrome="/custom/chrome",
            firefox="/custom/firefox",
        )
        assert browser_config.chrome == "/custom/chrome"
        assert browser_config.firefox == "/custom/firefox"


class TestDirectoryConfig:
    """Test DirectoryConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default directory paths."""
        dir_config = config.DirectoryConfig()
        assert isinstance(dir_config.desktop, Path)
        assert isinstance(dir_config.icons, Path)
        assert isinstance(dir_config.wrappers, Path)
        assert isinstance(dir_config.apps, Path)
        assert isinstance(dir_config.userscripts, Path)

    def test_custom_values(self, tmp_path: Path) -> None:
        """Test custom directory paths."""
        dir_config = config.DirectoryConfig(
            desktop=tmp_path / "desktop",
            icons=tmp_path / "icons",
        )
        assert dir_config.desktop == tmp_path / "desktop"
        assert dir_config.icons == tmp_path / "icons"


class TestChromeFlagsConfig:
    """Test ChromeFlagsConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default Chrome flags."""
        flags_config = config.ChromeFlagsConfig()
        assert "WebUIDarkMode" in flags_config.enable
        assert "IntentPickerPWALinks" in flags_config.disable
        assert "DesktopPWAsStayInWindow" in flags_config.disable

    def test_custom_values(self) -> None:
        """Test custom Chrome flags."""
        flags_config = config.ChromeFlagsConfig(
            enable=["CustomFeature1", "CustomFeature2"],
            disable=["DisabledFeature"],
        )
        assert flags_config.enable == ["CustomFeature1", "CustomFeature2"]
        assert flags_config.disable == ["DisabledFeature"]


class TestConfig:
    """Test main Config dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        cfg = config.Config()
        assert cfg.default_browser == "chrome"
        assert isinstance(cfg.browsers, config.BrowserConfig)
        assert isinstance(cfg.directories, config.DirectoryConfig)
        assert isinstance(cfg.chrome_flags, config.ChromeFlagsConfig)
        assert cfg.out_of_scope == "open-in-default"
        assert cfg.external_link_scheme == "ff"
        assert cfg.log_level == "info"
        assert isinstance(cfg.log_file, Path)

    def test_from_dict_empty(self) -> None:
        """Test creating Config from empty dictionary."""
        cfg = config.Config.from_dict({})
        assert cfg.default_browser == "chrome"
        assert cfg.out_of_scope == "open-in-default"

    def test_from_dict_partial(self) -> None:
        """Test creating Config from partial dictionary."""
        data = {
            "default_browser": "firefox",
            "log_level": "debug",
        }
        cfg = config.Config.from_dict(data)
        assert cfg.default_browser == "firefox"
        assert cfg.log_level == "debug"
        assert cfg.out_of_scope == "open-in-default"  # Default value

    def test_from_dict_with_nested_browsers(self) -> None:
        """Test creating Config with nested browser configuration."""
        data = {
            "browsers": {
                "chrome": "/custom/chrome",
                "firefox": "/custom/firefox",
            }
        }
        cfg = config.Config.from_dict(data)
        assert cfg.browsers.chrome == "/custom/chrome"
        assert cfg.browsers.firefox == "/custom/firefox"
        assert cfg.browsers.chromium == "/usr/bin/chromium"  # Default

    def test_from_dict_with_nested_directories(self, tmp_path: Path) -> None:
        """Test creating Config with nested directories configuration."""
        data = {
            "directories": {
                "desktop": str(tmp_path / "desktop"),
                "icons": str(tmp_path / "icons"),
            }
        }
        cfg = config.Config.from_dict(data)
        assert cfg.directories.desktop == tmp_path / "desktop"
        assert cfg.directories.icons == tmp_path / "icons"

    def test_from_dict_with_nested_chrome_flags(self) -> None:
        """Test creating Config with nested chrome_flags configuration."""
        data = {
            "chrome_flags": {
                "enable": ["Feature1", "Feature2"],
                "disable": ["Feature3"],
            }
        }
        cfg = config.Config.from_dict(data)
        assert cfg.chrome_flags.enable == ["Feature1", "Feature2"]
        assert cfg.chrome_flags.disable == ["Feature3"]

    def test_from_dict_expands_paths(self) -> None:
        """Test that paths are expanded in from_dict."""
        data = {
            "log_file": "~/test/log.log",
            "directories": {
                "desktop": "~/desktop",
            },
        }
        cfg = config.Config.from_dict(data)
        assert "~" not in str(cfg.log_file)
        assert "~" not in str(cfg.directories.desktop)


class TestGetDefaultConfig:
    """Test get_default_config function."""

    def test_returns_config_instance(self) -> None:
        """Test that get_default_config returns a Config instance."""
        cfg = config.get_default_config()
        assert isinstance(cfg, config.Config)

    def test_returns_defaults(self) -> None:
        """Test that get_default_config returns default values."""
        cfg = config.get_default_config()
        assert cfg.default_browser == "chrome"
        assert cfg.log_level == "info"


class TestLoadConfig:
    """Test load_config function."""

    def test_load_nonexistent_file_returns_defaults(self, tmp_path: Path) -> None:
        """Test loading from nonexistent file returns defaults."""
        config_path = tmp_path / "nonexistent.yaml"
        cfg = config.load_config(config_path)
        assert isinstance(cfg, config.Config)
        assert cfg.default_browser == "chrome"

    def test_load_valid_config_file(self, tmp_path: Path) -> None:
        """Test loading valid configuration file."""
        config_path = tmp_path / "config.yaml"
        config_data = {
            "default_browser": "firefox",
            "log_level": "debug",
            "out_of_scope": "same-browser-window",
        }
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        cfg = config.load_config(config_path)
        assert cfg.default_browser == "firefox"
        assert cfg.log_level == "debug"
        assert cfg.out_of_scope == "same-browser-window"

    def test_load_empty_config_file(self, tmp_path: Path) -> None:
        """Test loading empty configuration file returns defaults."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("", encoding="utf-8")

        cfg = config.load_config(config_path)
        assert cfg.default_browser == "chrome"

    def test_load_invalid_yaml_returns_defaults(self, tmp_path: Path) -> None:
        """Test loading invalid YAML returns defaults."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("invalid: yaml: content:", encoding="utf-8")

        cfg = config.load_config(config_path)
        assert isinstance(cfg, config.Config)
        assert cfg.default_browser == "chrome"

    def test_load_config_with_nested_structures(self, tmp_path: Path) -> None:
        """Test loading configuration with nested structures."""
        config_path = tmp_path / "config.yaml"
        config_data = {
            "default_browser": "chromium",
            "browsers": {
                "chrome": "/opt/chrome/chrome",
            },
            "chrome_flags": {
                "enable": ["TestFeature"],
                "disable": ["OtherFeature"],
            },
        }
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        cfg = config.load_config(config_path)
        assert cfg.default_browser == "chromium"
        assert cfg.browsers.chrome == "/opt/chrome/chrome"
        assert "TestFeature" in cfg.chrome_flags.enable

    def test_load_config_none_uses_default_path(self) -> None:
        """Test that load_config with None uses default config path."""
        # This will likely not exist, so should return defaults
        cfg = config.load_config(None)
        assert isinstance(cfg, config.Config)


class TestConfigProperties:
    """Test Config property accessors."""

    def test_desktop_dir_property(self) -> None:
        """Test desktop_dir property."""
        cfg = config.Config()
        desktop_dir = cfg.desktop_dir
        assert isinstance(desktop_dir, Path)

    def test_icons_dir_property(self) -> None:
        """Test icons_dir property."""
        cfg = config.Config()
        icons_dir = cfg.icons_dir
        assert isinstance(icons_dir, Path)

    def test_wrappers_dir_property(self) -> None:
        """Test wrappers_dir property."""
        cfg = config.Config()
        wrappers_dir = cfg.wrappers_dir
        assert isinstance(wrappers_dir, Path)

    def test_apps_dir_property(self) -> None:
        """Test apps_dir property."""
        cfg = config.Config()
        apps_dir = cfg.apps_dir
        assert isinstance(apps_dir, Path)

    def test_userscripts_dir_property(self) -> None:
        """Test userscripts_dir property."""
        cfg = config.Config()
        userscripts_dir = cfg.userscripts_dir
        assert isinstance(userscripts_dir, Path)

    def test_registry_file_property(self) -> None:
        """Test registry_file property."""
        cfg = config.Config()
        registry_file = cfg.registry_file
        assert isinstance(registry_file, Path)
        assert registry_file.name == "registry.json"


class TestLoadConfigErrorHandling:
    """Test error handling in load_config."""

    def test_load_config_io_error_returns_defaults(self, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Test that IO errors in load_config return defaults."""
        config_path = tmp_path / "config.yaml"

        # Create a file but make reading it fail
        config_path.write_text("valid: yaml")

        # Mock yaml.safe_load to raise a general exception
        def mock_safe_load(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("Mock general error")

        monkeypatch.setattr("yaml.safe_load", mock_safe_load)

        cfg = config.load_config(config_path)
        assert isinstance(cfg, config.Config)
        assert cfg.default_browser == "chrome"  # Should return defaults
