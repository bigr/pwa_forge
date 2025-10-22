"""Configuration management for PWA Forge."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pwa_forge.utils.logger import get_logger
from pwa_forge.utils.paths import (
    expand_path,
    get_app_config_dir,
    get_app_data_dir,
    get_apps_dir,
    get_desktop_dir,
    get_icons_dir,
    get_userscripts_dir,
    get_wrappers_dir,
)

__all__ = ["Config", "load_config", "get_default_config"]

logger = get_logger(__name__)


@dataclass
class BrowserConfig:
    """Browser executable paths configuration."""

    chrome: str = "/usr/bin/google-chrome-stable"
    chromium: str = "/usr/bin/chromium"
    firefox: str = "/usr/bin/firefox"
    edge: str = "/usr/bin/microsoft-edge"


@dataclass
class DirectoryConfig:
    """Directory paths configuration."""

    desktop: Path = field(default_factory=get_desktop_dir)
    icons: Path = field(default_factory=get_icons_dir)
    wrappers: Path = field(default_factory=get_wrappers_dir)
    apps: Path = field(default_factory=get_apps_dir)
    userscripts: Path = field(default_factory=get_userscripts_dir)


@dataclass
class ChromeFlagsConfig:
    """Chrome/Chromium flags configuration."""

    enable: list[str] = field(default_factory=lambda: ["WebUIDarkMode"])
    disable: list[str] = field(default_factory=lambda: ["IntentPickerPWALinks", "DesktopPWAsStayInWindow"])


@dataclass
class Config:
    """Global configuration for PWA Forge."""

    default_browser: str = "chrome"
    browsers: BrowserConfig = field(default_factory=BrowserConfig)
    directories: DirectoryConfig = field(default_factory=DirectoryConfig)
    chrome_flags: ChromeFlagsConfig = field(default_factory=ChromeFlagsConfig)
    out_of_scope: str = "open-in-default"
    external_link_scheme: str = "ff"
    log_level: str = "info"
    log_file: Path = field(default_factory=lambda: get_app_data_dir() / "pwa-forge.log")

    @property
    def desktop_dir(self) -> Path:
        """Get desktop directory path."""
        return self.directories.desktop

    @property
    def icons_dir(self) -> Path:
        """Get icons directory path."""
        return self.directories.icons

    @property
    def wrappers_dir(self) -> Path:
        """Get wrappers directory path."""
        return self.directories.wrappers

    @property
    def apps_dir(self) -> Path:
        """Get apps directory path."""
        return self.directories.apps

    @property
    def userscripts_dir(self) -> Path:
        """Get userscripts directory path."""
        return self.directories.userscripts

    @property
    def registry_file(self) -> Path:
        """Get registry file path."""
        return get_app_data_dir() / "registry.json"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create Config from a dictionary.

        Args:
            data: Dictionary with configuration values.

        Returns:
            Config instance with values from the dictionary.
        """
        # Handle nested browser config
        browsers_data = data.get("browsers", {})
        browsers = BrowserConfig(**browsers_data) if browsers_data else BrowserConfig()

        # Handle nested directories config
        dirs_data = data.get("directories", {})
        if dirs_data:
            # Expand paths in directories
            expanded_dirs = {k: expand_path(v) for k, v in dirs_data.items()}
            directories = DirectoryConfig(**expanded_dirs)
        else:
            directories = DirectoryConfig()

        # Handle nested chrome flags config
        flags_data = data.get("chrome_flags", {})
        chrome_flags = ChromeFlagsConfig(**flags_data) if flags_data else ChromeFlagsConfig()

        # Handle log_file path expansion
        log_file_str = data.get("log_file")
        log_file = expand_path(log_file_str) if log_file_str else get_app_data_dir() / "pwa-forge.log"

        return cls(
            default_browser=data.get("default_browser", "chrome"),
            browsers=browsers,
            directories=directories,
            chrome_flags=chrome_flags,
            out_of_scope=data.get("out_of_scope", "open-in-default"),
            external_link_scheme=data.get("external_link_scheme", "ff"),
            log_level=data.get("log_level", "info"),
            log_file=log_file,
        )


def get_default_config() -> Config:
    """Get the default configuration.

    Returns:
        Config instance with default values.
    """
    return Config()


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from file or return defaults.

    Args:
        config_path: Path to configuration file. If None, uses default location.

    Returns:
        Config instance loaded from file or with default values.
    """
    if config_path is None:
        config_path = get_app_config_dir() / "config.yaml"

    if not config_path.exists():
        logger.debug(f"Config file not found at {config_path}, using defaults")
        return get_default_config()

    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        logger.debug(f"Loaded configuration from {config_path}")
        return Config.from_dict(data)
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse config file {config_path}: {e}, using defaults")
        return get_default_config()
    except Exception as e:
        logger.warning(f"Error loading config file {config_path}: {e}, using defaults")
        return get_default_config()
