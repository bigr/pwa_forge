"""Implementation of the remove command."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from pwa_forge.config import Config
from pwa_forge.registry import AppNotFoundError, Registry

logger = logging.getLogger(__name__)


class RemoveCommandError(Exception):
    """Base exception for remove command errors."""


def remove_app(
    app_id: str,
    config: Config,
    remove_profile: bool = False,
    remove_icon: bool = False,
    keep_userdata: bool = False,
    dry_run: bool = False,
) -> None:
    """Remove a PWA instance.

    Args:
        app_id: Application identifier or name.
        config: Configuration object.
        remove_profile: Also delete the browser profile directory.
        remove_icon: Also delete the icon file.
        keep_userdata: Keep browser profile but remove launcher.
        dry_run: If True, show what would be removed without making changes.

    Raises:
        RemoveCommandError: If the operation fails.
    """
    logger.info(f"Removing PWA: {app_id}")

    # Get app from registry
    registry = Registry(config.registry_file)
    try:
        app = registry.get_app(app_id)
    except AppNotFoundError as e:
        raise RemoveCommandError(str(e)) from e

    # Get paths
    desktop_file = Path(app.get("desktop_file", ""))
    wrapper_script = Path(app.get("wrapper_script", ""))
    manifest_path = Path(app.get("manifest_path", ""))

    # Load manifest to get more details
    profile_path = None
    icon_path = None
    if manifest_path.exists():
        import yaml

        try:
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
                if manifest:
                    profile_path = Path(manifest.get("profile", "")) if manifest.get("profile") else None
                    icon_path = Path(manifest.get("icon", "")) if manifest.get("icon") else None
        except Exception as e:
            logger.warning(f"Failed to load manifest: {e}")

    # Remove desktop file
    if desktop_file.exists():
        if not dry_run:
            desktop_file.unlink()
            logger.info(f"Removed desktop file: {desktop_file}")
        else:
            logger.info(f"[DRY-RUN] Would remove desktop file: {desktop_file}")
    else:
        logger.warning(f"Desktop file not found: {desktop_file}")

    # Remove wrapper script
    if wrapper_script.exists():
        if not dry_run:
            wrapper_script.unlink()
            logger.info(f"Removed wrapper script: {wrapper_script}")
        else:
            logger.info(f"[DRY-RUN] Would remove wrapper script: {wrapper_script}")
    else:
        logger.warning(f"Wrapper script not found: {wrapper_script}")

    # Remove manifest
    if manifest_path.exists():
        if not dry_run:
            manifest_path.unlink()
            logger.info(f"Removed manifest: {manifest_path}")

            # Try to remove parent directory if empty and not the profile directory
            # Only remove if we're also removing the profile or if they're different
            manifest_parent = manifest_path.parent
            if remove_profile or (profile_path and manifest_parent != profile_path):
                try:
                    manifest_parent.rmdir()
                    logger.info(f"Removed empty directory: {manifest_parent}")
                except OSError:
                    pass  # Directory not empty or doesn't exist
        else:
            logger.info(f"[DRY-RUN] Would remove manifest: {manifest_path}")

    # Optionally remove profile
    if remove_profile and not keep_userdata and profile_path and profile_path.exists():
        if not dry_run:
            shutil.rmtree(profile_path)
            logger.info(f"Removed profile directory: {profile_path}")
        else:
            logger.info(f"[DRY-RUN] Would remove profile directory: {profile_path}")

    # Optionally remove icon
    if remove_icon and icon_path and icon_path.exists():
        if not dry_run:
            icon_path.unlink()
            logger.info(f"Removed icon: {icon_path}")
        else:
            logger.info(f"[DRY-RUN] Would remove icon: {icon_path}")

    # Remove from registry
    if not dry_run:
        registry.remove_app(app_id)
        logger.info(f"Removed app from registry: {app_id}")
    else:
        logger.info(f"[DRY-RUN] Would remove app from registry: {app_id}")

    # Update desktop database
    if not dry_run:
        _update_desktop_database(config.desktop_dir)

    logger.info(f"Successfully removed PWA: {app_id}")


def _update_desktop_database(desktop_dir: Path) -> None:
    """Update the desktop database.

    Args:
        desktop_dir: Desktop files directory.
    """
    import subprocess

    try:
        subprocess.run(
            ["update-desktop-database", str(desktop_dir)],
            check=True,
            capture_output=True,
        )
        logger.info("Updated desktop database")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to update desktop database: {e.stderr.decode()}")
    except FileNotFoundError:
        logger.warning("update-desktop-database command not found")
