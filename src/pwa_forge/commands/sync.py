"""Implementation of the sync command."""

from __future__ import annotations

import logging
import stat
from datetime import datetime
from typing import Any

import yaml

from pwa_forge.config import Config
from pwa_forge.registry import AppNotFoundError, Registry
from pwa_forge.templates import get_template_engine
from pwa_forge.utils.paths import expand_path

logger = logging.getLogger(__name__)


class SyncCommandError(Exception):
    """Base exception for sync command errors."""


def sync_app(
    app_id: str,
    config: Config,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Regenerate all artifacts from manifest file.

    Args:
        app_id: Application identifier.
        config: Config instance.
        dry_run: Show what would be regenerated.

    Returns:
        Dict with sync results: {
            "id": str,
            "regenerated": ["wrapper", "desktop"],
            "warnings": [str],
        }

    Raises:
        SyncCommandError: If sync operation fails.
    """
    logger.info(f"Syncing PWA: {app_id}")

    # Get app from registry
    registry = Registry(config.registry_file)
    try:
        app_entry = registry.get_app(app_id)
    except AppNotFoundError as e:
        raise SyncCommandError(str(e)) from e

    # Load manifest file
    manifest_path_str = app_entry.get("manifest_path")
    if not manifest_path_str:
        raise SyncCommandError(f"App '{app_id}' has no manifest_path in registry")

    manifest_path = expand_path(manifest_path_str)
    if not manifest_path.exists():
        raise SyncCommandError(f"Manifest file not found: {manifest_path}")

    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SyncCommandError(f"Invalid YAML in manifest: {e}") from e
    except Exception as e:
        raise SyncCommandError(f"Failed to read manifest: {e}") from e

    if not manifest:
        raise SyncCommandError("Manifest file is empty")

    # Validate required fields
    required_fields = ["id", "name", "url", "browser"]
    missing_fields = [field for field in required_fields if field not in manifest]
    if missing_fields:
        raise SyncCommandError(f"Manifest missing required fields: {', '.join(missing_fields)}")

    # Prepare template context
    template_engine = get_template_engine()
    warnings: list[str] = []
    regenerated: list[str] = []

    # Get paths from registry
    wrapper_script_path_str = app_entry.get("wrapper_script")
    desktop_file_path_str = app_entry.get("desktop_file")

    if not wrapper_script_path_str:
        raise SyncCommandError(f"App '{app_id}' has no wrapper_script in registry")
    if not desktop_file_path_str:
        raise SyncCommandError(f"App '{app_id}' has no desktop_file in registry")

    wrapper_script_path = expand_path(wrapper_script_path_str)
    desktop_file_path = expand_path(desktop_file_path_str)

    # Get browser executable
    browser = manifest.get("browser", "chrome")
    browser_attr = getattr(config.browsers, browser, None)
    if not browser_attr:
        raise SyncCommandError(f"Unknown browser: {browser}")
    browser_exec = browser_attr

    # Check if files have been manually edited (compare modification times)
    manifest_mtime = manifest_path.stat().st_mtime
    modified_timestamp = manifest.get("modified")

    if wrapper_script_path.exists():
        wrapper_mtime = wrapper_script_path.stat().st_mtime
        if modified_timestamp:
            # Parse ISO timestamp
            try:
                modified_dt = datetime.fromisoformat(modified_timestamp.replace("Z", "+00:00"))
                modified_ts = modified_dt.timestamp()
                if wrapper_mtime > modified_ts and wrapper_mtime > manifest_mtime:
                    warnings.append(
                        "Wrapper script appears to have been manually edited "
                        "(modified after manifest). Changes will be overwritten."
                    )
            except (ValueError, AttributeError):
                logger.debug(f"Could not parse modified timestamp: {modified_timestamp}")

    if desktop_file_path.exists():
        desktop_mtime = desktop_file_path.stat().st_mtime
        if modified_timestamp:
            try:
                modified_dt = datetime.fromisoformat(modified_timestamp.replace("Z", "+00:00"))
                modified_ts = modified_dt.timestamp()
                if desktop_mtime > modified_ts and desktop_mtime > manifest_mtime:
                    warnings.append(
                        "Desktop file appears to have been manually edited "
                        "(modified after manifest). Changes will be overwritten."
                    )
            except (ValueError, AttributeError):
                logger.debug(f"Could not parse modified timestamp: {modified_timestamp}")

    # Prepare wrapper script context
    profile = expand_path(manifest.get("profile", config.apps_dir / app_id / "profile"))
    flags = manifest.get("flags", {})
    enable_features = flags.get("enable_features", config.chrome_flags.enable)
    disable_features = flags.get("disable_features", config.chrome_flags.disable)
    ozone_platform = flags.get("ozone_platform", "x11")

    wrapper_context = {
        "name": manifest["name"],
        "id": manifest["id"],
        "url": manifest["url"],
        "browser_exec": browser_exec,
        "wm_class": manifest.get("wm_class", "App"),
        "profile": str(profile),
        "ozone_platform": ozone_platform,
        "enable_features": enable_features,
        "disable_features": disable_features,
    }

    # Prepare desktop file context
    icon_path = manifest.get("icon")
    if icon_path:
        icon_path = expand_path(icon_path)

    desktop_context = {
        "name": manifest["name"],
        "comment": manifest.get("comment", f"{manifest['name']} PWA"),
        "wrapper_path": str(wrapper_script_path),
        "icon_path": str(icon_path) if icon_path else "web-browser",
        "wm_class": manifest.get("wm_class", "App"),
        "categories": manifest.get("categories", ["Network", "WebBrowser"]),
    }

    # Regenerate wrapper script
    if dry_run:
        logger.info(f"[DRY-RUN] Would regenerate wrapper script: {wrapper_script_path}")
    else:
        try:
            wrapper_content = template_engine.render_wrapper_script(**wrapper_context)
            wrapper_script_path.parent.mkdir(parents=True, exist_ok=True)
            wrapper_script_path.write_text(wrapper_content)
            # Set executable permissions
            wrapper_script_path.chmod(wrapper_script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            logger.info(f"Regenerated wrapper script: {wrapper_script_path}")
            regenerated.append("wrapper")
        except Exception as e:
            raise SyncCommandError(f"Failed to regenerate wrapper script: {e}") from e

    # Regenerate desktop file
    if dry_run:
        logger.info(f"[DRY-RUN] Would regenerate desktop file: {desktop_file_path}")
    else:
        try:
            desktop_content = template_engine.render_desktop_file(**desktop_context)
            desktop_file_path.parent.mkdir(parents=True, exist_ok=True)
            desktop_file_path.write_text(desktop_content)
            logger.info(f"Regenerated desktop file: {desktop_file_path}")
            regenerated.append("desktop")
        except Exception as e:
            raise SyncCommandError(f"Failed to regenerate desktop file: {e}") from e

    # Update manifest modified timestamp
    if not dry_run:
        try:
            manifest["modified"] = datetime.now().isoformat()
            with manifest_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)
            logger.info("Updated manifest modified timestamp")
        except Exception as e:
            logger.warning(f"Failed to update manifest timestamp: {e}")
            warnings.append(f"Could not update manifest timestamp: {e}")

    logger.info(f"Sync completed for {app_id}: regenerated {', '.join(regenerated)}")

    return {
        "id": app_id,
        "regenerated": regenerated,
        "warnings": warnings,
    }
