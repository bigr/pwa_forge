"""Path utilities for managing XDG directories and file operations."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from platformdirs import user_cache_dir, user_config_dir, user_data_dir

__all__ = [
    "get_app_data_dir",
    "get_app_config_dir",
    "get_app_cache_dir",
    "get_desktop_dir",
    "get_icons_dir",
    "get_wrappers_dir",
    "get_apps_dir",
    "get_userscripts_dir",
    "get_registry_path",
    "expand_path",
    "ensure_dir",
]

APP_NAME: Final[str] = "pwa-forge"


def get_app_data_dir() -> Path:
    """Return the application data directory (~/.local/share/pwa-forge).

    Returns:
        Path to the application data directory.
    """
    return Path(user_data_dir(APP_NAME, appauthor=False))


def get_app_config_dir() -> Path:
    """Return the application config directory (~/.config/pwa-forge).

    Returns:
        Path to the application config directory.
    """
    return Path(user_config_dir(APP_NAME, appauthor=False))


def get_app_cache_dir() -> Path:
    """Return the application cache directory (~/.cache/pwa-forge).

    Returns:
        Path to the application cache directory.
    """
    return Path(user_cache_dir(APP_NAME, appauthor=False))


def get_desktop_dir() -> Path:
    """Return the XDG desktop applications directory.

    Returns:
        Path to ~/.local/share/applications
    """
    return Path.home() / ".local" / "share" / "applications"


def get_icons_dir() -> Path:
    """Return the icons directory for PWA Forge.

    Returns:
        Path to ~/.local/share/icons/pwa-forge
    """
    return Path.home() / ".local" / "share" / "icons" / APP_NAME


def get_wrappers_dir() -> Path:
    """Return the wrapper scripts directory.

    Returns:
        Path to ~/.local/bin/pwa-forge-wrappers
    """
    return Path.home() / ".local" / "bin" / "pwa-forge-wrappers"


def get_apps_dir() -> Path:
    """Return the directory for storing per-app manifests and profiles.

    Returns:
        Path to ~/.local/share/pwa-forge/apps
    """
    return get_app_data_dir() / "apps"


def get_userscripts_dir() -> Path:
    """Return the directory for storing userscripts.

    Returns:
        Path to ~/.local/share/pwa-forge/userscripts
    """
    return get_app_data_dir() / "userscripts"


def get_registry_path() -> Path:
    """Return the path to the registry index file.

    Returns:
        Path to ~/.local/share/pwa-forge/registry.json
    """
    return get_app_data_dir() / "registry.json"


def expand_path(path: str | Path) -> Path:
    """Expand and resolve a path, handling ~ and environment variables.

    Args:
        path: Path string or Path object to expand.

    Returns:
        Absolute, normalized Path object.
    """
    return Path(path).expanduser().resolve()


def ensure_dir(path: Path, mode: int = 0o755) -> Path:
    """Ensure a directory exists, creating it with specified permissions if needed.

    Args:
        path: Directory path to ensure exists.
        mode: Permission mode for directory creation (default: 0o755).

    Returns:
        The directory path.

    Raises:
        OSError: If directory creation fails.
    """
    path.mkdir(parents=True, exist_ok=True, mode=mode)
    return path
