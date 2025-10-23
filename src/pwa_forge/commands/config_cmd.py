"""Configuration management commands for PWA Forge."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

from pwa_forge.config import Config, get_default_config
from pwa_forge.utils.logger import get_logger
from pwa_forge.utils.paths import get_app_config_dir

__all__ = [
    "ConfigCommandError",
    "config_get",
    "config_set",
    "config_list",
    "config_reset",
    "config_edit",
]

logger = get_logger(__name__)


class ConfigCommandError(Exception):
    """Raised when a config command operation fails."""


def _get_config_path() -> Path:
    """Get the user config file path."""
    return get_app_config_dir() / "config.yaml"


def _load_config_dict() -> dict[str, Any]:
    """Load configuration as dictionary from file.

    Returns:
        Dictionary with config values, or empty dict if file doesn't exist.
    """
    config_path = _get_config_path()

    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except yaml.YAMLError as e:
        raise ConfigCommandError(f"Invalid YAML in config file: {e}") from e
    except Exception as e:
        raise ConfigCommandError(f"Error reading config file: {e}") from e


def _save_config_dict(data: dict[str, Any]) -> None:
    """Save configuration dictionary to file.

    Args:
        data: Configuration dictionary to save.
    """
    config_path = _get_config_path()

    # Create config directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        logger.debug(f"Saved configuration to {config_path}")
    except Exception as e:
        raise ConfigCommandError(f"Error writing config file: {e}") from e


def _get_nested_value(data: dict[str, Any], key: str) -> Any:
    """Get value from nested dictionary using dot notation.

    Args:
        data: Dictionary to search.
        key: Key in dot notation (e.g., "browsers.chrome").

    Returns:
        Value at the specified key path.

    Raises:
        KeyError: If key path doesn't exist.
    """
    parts = key.split(".")
    current = data

    for part in parts:
        if not isinstance(current, dict):
            raise KeyError(f"Key '{key}' not found ('{part}' is not a dict)")
        if part not in current:
            raise KeyError(f"Key '{key}' not found")
        current = current[part]

    return current


def _set_nested_value(data: dict[str, Any], key: str, value: Any) -> None:
    """Set value in nested dictionary using dot notation.

    Args:
        data: Dictionary to modify.
        key: Key in dot notation (e.g., "browsers.chrome").
        value: Value to set.
    """
    parts = key.split(".")
    current = data

    # Navigate to parent
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            raise ConfigCommandError(f"Cannot set '{key}': '{part}' is not a dict")
        current = current[part]

    # Set the final value
    current[parts[-1]] = value


def _parse_value(value_str: str) -> Any:
    """Parse string value to appropriate Python type.

    Args:
        value_str: String value to parse.

    Returns:
        Parsed value (str, int, float, bool, or list).
    """
    # Try to parse as YAML to get correct type
    try:
        parsed = yaml.safe_load(value_str)
        # If it's a string, return the original to preserve formatting
        if isinstance(parsed, str):
            return value_str
        return parsed
    except yaml.YAMLError:
        # If YAML parsing fails, return as string
        return value_str


def config_get(key: str, config: Config) -> str:
    """Get configuration value by key.

    Args:
        key: Configuration key (supports dot notation: browsers.chrome).
        config: Current Config instance (not used, we read from file).

    Returns:
        String representation of the configuration value.

    Raises:
        ConfigCommandError: If key is not found or config is invalid.
    """
    # Load from file to get user's actual config (not merged with defaults)
    config_data = _load_config_dict()

    if not config_data:
        # No user config, use defaults
        default = get_default_config()
        config_data = _config_to_dict(default)

    try:
        value = _get_nested_value(config_data, key)
        return _format_value(value)
    except KeyError as e:
        raise ConfigCommandError(f"Configuration key not found: {key}") from e


def config_set(key: str, value: str, config: Config) -> None:
    """Set configuration value by key.

    Args:
        key: Configuration key (supports dot notation).
        value: Value to set (will be parsed to correct type).
        config: Current Config instance (not used).

    Raises:
        ConfigCommandError: If key is invalid or value cannot be set.
    """
    # Load existing config
    config_data = _load_config_dict()

    # Parse value to correct type
    parsed_value = _parse_value(value)

    # Set the value
    _set_nested_value(config_data, key, parsed_value)

    # Validate by trying to load it
    try:
        Config.from_dict(config_data)
    except Exception as e:
        raise ConfigCommandError(f"Invalid configuration value: {e}") from e

    # Save to file
    _save_config_dict(config_data)
    logger.info(f"Set {key} = {parsed_value}")


def config_list(config: Config) -> dict[str, Any]:
    """Get all configuration values.

    Args:
        config: Current Config instance.

    Returns:
        Dictionary with all configuration values.
    """
    # Load from file to show user's actual config
    config_data = _load_config_dict()

    if not config_data:
        # No user config, show defaults
        config_data = _config_to_dict(config)

    return config_data


def config_reset(config: Config) -> None:
    """Reset configuration to defaults.

    Args:
        config: Current Config instance (not used).

    Raises:
        ConfigCommandError: If config file cannot be removed.
    """
    config_path = _get_config_path()

    if not config_path.exists():
        logger.info("No user config file to reset")
        return

    try:
        config_path.unlink()
        logger.info(f"Removed config file: {config_path}")
    except Exception as e:
        raise ConfigCommandError(f"Error removing config file: {e}") from e


def config_edit(config: Config) -> None:
    """Open config file in $EDITOR.

    Args:
        config: Current Config instance (not used).

    Raises:
        ConfigCommandError: If editor cannot be launched or validation fails.
    """
    config_path = _get_config_path()

    # Get editor from environment
    editor = os.environ.get("EDITOR")
    if not editor:
        # Try fallbacks
        for fallback in ["vi", "nano", "vim"]:
            if subprocess.run(["which", fallback], capture_output=True).returncode == 0:
                editor = fallback
                break

    if not editor:
        raise ConfigCommandError(
            "$EDITOR environment variable not set and no fallback editor found. " "Set EDITOR or install vi/nano/vim."
        )

    # Create config file with defaults if it doesn't exist
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        default_config = get_default_config()
        _save_config_dict(_config_to_dict(default_config))

    # Create backup
    backup_path = config_path.with_suffix(".yaml.bak")
    if config_path.exists():
        import shutil

        shutil.copy2(config_path, backup_path)

    # Open in editor
    try:
        result = subprocess.run([editor, str(config_path)])

        if result.returncode != 0:
            raise ConfigCommandError(f"Editor exited with code {result.returncode}")

        # Validate the edited config
        config_data = _load_config_dict()
        Config.from_dict(config_data)

        # Remove backup on success
        if backup_path.exists():
            backup_path.unlink()

        logger.info("Config file edited successfully")

    except ConfigCommandError:
        # Restore backup on validation error
        if backup_path.exists():
            import shutil

            shutil.copy2(backup_path, config_path)
            backup_path.unlink()
        raise
    except Exception as e:
        # Restore backup on any error
        if backup_path.exists():
            import shutil

            shutil.copy2(backup_path, config_path)
            backup_path.unlink()
        raise ConfigCommandError(f"Error editing config: {e}") from e


def _config_to_dict(config: Config) -> dict[str, Any]:
    """Convert Config instance to dictionary.

    Args:
        config: Config instance to convert.

    Returns:
        Dictionary representation of the config.
    """
    return {
        "default_browser": config.default_browser,
        "browsers": {
            "chrome": config.browsers.chrome,
            "chromium": config.browsers.chromium,
            "firefox": config.browsers.firefox,
            "edge": config.browsers.edge,
        },
        "directories": {
            "desktop": str(config.directories.desktop),
            "icons": str(config.directories.icons),
            "wrappers": str(config.directories.wrappers),
            "apps": str(config.directories.apps),
            "userscripts": str(config.directories.userscripts),
        },
        "chrome_flags": {
            "enable": config.chrome_flags.enable,
            "disable": config.chrome_flags.disable,
        },
        "out_of_scope": config.out_of_scope,
        "external_link_scheme": config.external_link_scheme,
        "log_level": config.log_level,
        "log_file": str(config.log_file),
    }


def _format_value(value: Any) -> str:
    """Format a value for display.

    Args:
        value: Value to format.

    Returns:
        String representation of the value.
    """
    if isinstance(value, list | dict):
        return yaml.safe_dump(value, default_flow_style=False).strip()
    return str(value)
