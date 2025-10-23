"""Implementation of the edit command."""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any

import yaml

from pwa_forge.commands.sync import sync_app
from pwa_forge.config import Config
from pwa_forge.registry import AppNotFoundError, Registry
from pwa_forge.utils.paths import expand_path

logger = logging.getLogger(__name__)


class EditCommandError(Exception):
    """Base exception for edit command errors."""


def edit_app(
    app_id: str,
    config: Config,
    auto_sync: bool = True,
) -> dict[str, Any]:
    """Open manifest in $EDITOR and optionally sync after edit.

    Args:
        app_id: Application identifier.
        config: Config instance.
        auto_sync: Automatically sync after successful edit.

    Returns:
        Dict with edit results: {
            "id": str,
            "edited": bool,
            "synced": bool,
            "validation_errors": [str] | None,
        }

    Raises:
        EditCommandError: If edit operation fails.
    """
    logger.info(f"Editing PWA manifest: {app_id}")

    # Get app from registry
    registry = Registry(config.registry_file)
    try:
        app_entry = registry.get_app(app_id)
    except AppNotFoundError as e:
        raise EditCommandError(str(e)) from e

    # Get manifest path
    manifest_path_str = app_entry.get("manifest_path")
    if not manifest_path_str:
        raise EditCommandError(f"App '{app_id}' has no manifest_path in registry")

    manifest_path = expand_path(manifest_path_str)
    if not manifest_path.exists():
        raise EditCommandError(f"Manifest file not found: {manifest_path}")

    # Check for $EDITOR environment variable
    import os

    editor = os.environ.get("EDITOR")
    if not editor:
        # Try common fallbacks
        for fallback in ["vi", "nano", "vim"]:
            if shutil.which(fallback):
                editor = fallback
                logger.debug(f"Using fallback editor: {editor}")
                break

    if not editor:
        raise EditCommandError("No editor found. Set $EDITOR environment variable or install vi/nano/vim.")

    # Create backup
    backup_path = manifest_path.with_suffix(".yaml.bak")
    try:
        shutil.copy2(manifest_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
    except Exception as e:
        logger.warning(f"Failed to create backup: {e}")
        # Continue anyway

    # Open manifest in editor
    logger.info(f"Opening {manifest_path} in {editor}")
    try:
        result = subprocess.run([editor, str(manifest_path)], check=False)
        if result.returncode != 0:
            logger.warning(f"Editor exited with code {result.returncode}")
    except Exception as e:
        raise EditCommandError(f"Failed to open editor: {e}") from e

    # Validate YAML after edit
    validation_errors: list[str] = []
    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)

        if not manifest:
            validation_errors.append("Manifest file is empty")
        else:
            # Check required fields
            required_fields = ["id", "name", "url", "browser"]
            missing_fields = [field for field in required_fields if field not in manifest]
            if missing_fields:
                validation_errors.append(f"Missing required fields: {', '.join(missing_fields)}")

    except yaml.YAMLError as e:
        validation_errors.append(f"Invalid YAML syntax: {e}")
    except Exception as e:
        validation_errors.append(f"Error reading manifest: {e}")

    # If validation failed, restore backup
    if validation_errors:
        logger.error(f"Manifest validation failed: {validation_errors}")
        if backup_path.exists():
            try:
                shutil.copy2(backup_path, manifest_path)
                logger.info("Restored manifest from backup")
            except Exception as e:
                logger.error(f"Failed to restore backup: {e}")

        return {
            "id": app_id,
            "edited": True,
            "synced": False,
            "validation_errors": validation_errors,
        }

    # Sync if requested and validation passed
    synced = False
    if auto_sync:
        try:
            logger.info(f"Auto-syncing after edit: {app_id}")
            sync_app(app_id, config, dry_run=False)
            synced = True
            logger.info("Sync completed successfully")
        except Exception as e:
            logger.warning(f"Failed to sync after edit: {e}")
            # Don't fail the edit, just warn

    # Remove backup on success
    if backup_path.exists():
        try:
            backup_path.unlink()
            logger.debug("Removed backup file")
        except Exception as e:
            logger.warning(f"Failed to remove backup: {e}")

    return {
        "id": app_id,
        "edited": True,
        "synced": synced,
        "validation_errors": None,
    }
