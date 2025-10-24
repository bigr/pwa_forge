"""Implementation of URL scheme handler commands."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pwa_forge.config import Config
from pwa_forge.registry import Registry, RegistryError
from pwa_forge.templates import get_template_engine
from pwa_forge.utils.paths import expand_path

logger = logging.getLogger(__name__)


class HandlerCommandError(Exception):
    """Base exception for handler command errors."""


def _find_browser_executable(browser: str, config: Config) -> Path:
    """Find the executable path for a browser.

    Uses multiple detection strategies:
    1. Configured path from config.browsers
    2. Known platform-specific install paths
    3. System PATH search (shutil.which) with multiple executable names

    Args:
        browser: Browser name (chrome, chromium, firefox, edge).
        config: Configuration object.

    Returns:
        Path to the browser executable.

    Raises:
        HandlerCommandError: If browser executable is not found.
    """
    # Strategy 1: Check configured path
    browser_path_str = getattr(config.browsers, browser, None)
    if browser_path_str:
        browser_path = Path(browser_path_str)
        if browser_path.exists():
            logger.debug(f"Found {browser} via config: {browser_path}")
            return browser_path

    # Strategy 2: Check known install locations
    known_paths = {
        "chrome": [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/snap/bin/chromium",
            "/usr/local/bin/google-chrome",
        ],
        "chromium": [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ],
        "firefox": [
            "/usr/bin/firefox",
            "/snap/bin/firefox",
            "/usr/local/bin/firefox",
        ],
        "edge": [
            "/usr/bin/microsoft-edge",
            "/opt/microsoft/msedge/microsoft-edge",
        ],
    }

    for path_str in known_paths.get(browser, []):
        path = Path(path_str)
        if path.exists():
            logger.debug(f"Found {browser} at known location: {path}")
            return path

    # Strategy 3: Search system PATH with multiple executable names
    executable_names = {
        "chrome": ["google-chrome-stable", "google-chrome", "chrome"],
        "chromium": ["chromium-browser", "chromium"],
        "firefox": ["firefox"],
        "edge": ["microsoft-edge", "edge"],
    }

    for name in executable_names.get(browser, [browser]):
        found_path = shutil.which(name)
        if found_path:
            logger.info(f"Found {browser} in PATH as '{name}': {found_path}")
            return Path(found_path)

    # Not found
    raise HandlerCommandError(
        f"Browser '{browser}' not found\n" f"  → Install {browser} or use a different browser with --browser"
    )


def generate_handler(
    scheme: str,
    config: Config,
    browser: str = "firefox",
    out: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate a URL scheme handler script.

    Args:
        scheme: URL scheme to handle (e.g., "ff" for ff:// URLs).
        config: Configuration object.
        browser: Browser to open URLs in.
        out: Output path for handler script.
        dry_run: If True, show what would be created without making changes.

    Returns:
        Dictionary with details of the generated handler.

    Raises:
        HandlerCommandError: If the operation fails.
    """
    logger.info(f"Generating handler script for scheme: {scheme}://")

    # Validate scheme
    if not scheme or not scheme.replace("-", "").replace("_", "").isalnum():
        raise HandlerCommandError(
            f"Invalid scheme: {scheme}\n  → Scheme must contain only alphanumeric characters, hyphens, and underscores"
        )

    # Find browser executable
    browser_exec = _find_browser_executable(browser, config)

    # Determine output path
    if out is None:
        handler_script_path = Path.home() / ".local" / "bin" / f"pwa-forge-handler-{scheme}"
    else:
        handler_script_path = expand_path(out)

    logger.debug(f"Handler script path: {handler_script_path}")

    # Render handler script
    template_engine = get_template_engine()
    handler_content = template_engine.render_handler_script(
        scheme=scheme,
        browser=browser,
        browser_exec=str(browser_exec),
    )

    # Write handler script
    if dry_run:
        logger.info(f"[DRY-RUN] Would write handler script to {handler_script_path}")
        logger.debug(f"[DRY-RUN] Content:\n{handler_content}")
    else:
        handler_script_path.parent.mkdir(parents=True, exist_ok=True)
        handler_script_path.write_text(handler_content)
        handler_script_path.chmod(0o755)  # Make executable
        logger.info(f"Generated handler script: {handler_script_path}")

    return {
        "scheme": scheme,
        "browser": browser,
        "browser_exec": str(browser_exec),
        "script_path": str(handler_script_path),
    }


def install_handler(
    scheme: str,
    config: Config,
    handler_script: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Register a URL scheme handler with the system.

    Args:
        scheme: URL scheme to register.
        config: Configuration object.
        handler_script: Path to handler script (default: auto-detected).
        dry_run: If True, show what would be created without making changes.

    Returns:
        Dictionary with details of the installed handler.

    Raises:
        HandlerCommandError: If the operation fails.
    """
    logger.info(f"Installing handler for scheme: {scheme}://")

    # Determine handler script path
    if handler_script is None:
        handler_script_path = Path.home() / ".local" / "bin" / f"pwa-forge-handler-{scheme}"
    else:
        handler_script_path = expand_path(handler_script)

    # Verify handler script exists
    if not handler_script_path.exists() and not dry_run:
        raise HandlerCommandError(
            f"Handler script not found: {handler_script_path}\n"
            f"  → Generate it first with: pwa-forge generate-handler --scheme {scheme}"
        )

    # Determine desktop file path
    desktop_file_path = config.desktop_dir / f"pwa-forge-handler-{scheme}.desktop"
    desktop_file_name = f"pwa-forge-handler-{scheme}.desktop"

    logger.debug(f"Desktop file path: {desktop_file_path}")

    # Render desktop file
    template_engine = get_template_engine()
    desktop_content = template_engine.render_handler_desktop(
        scheme=scheme,
        browser="firefox",  # Just for display name
        handler_script=str(handler_script_path),
        icon=None,
    )

    # Write desktop file
    if dry_run:
        logger.info(f"[DRY-RUN] Would write desktop file to {desktop_file_path}")
        logger.debug(f"[DRY-RUN] Content:\n{desktop_content}")
    else:
        desktop_file_path.parent.mkdir(parents=True, exist_ok=True)
        desktop_file_path.write_text(desktop_content)
        logger.info(f"Generated desktop file: {desktop_file_path}")

    # Update desktop database
    if not dry_run:
        try:
            subprocess.run(
                ["update-desktop-database", str(config.desktop_dir)],
                check=True,
                capture_output=True,
            )
            logger.info("Updated desktop database")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to update desktop database: {e.stderr.decode()}")
        except FileNotFoundError:
            logger.warning("update-desktop-database not found, skipping database update")

    # Register MIME type handler
    mime_type = f"x-scheme-handler/{scheme}"
    if not dry_run:
        try:
            subprocess.run(
                ["xdg-mime", "default", desktop_file_name, mime_type],
                check=True,
                capture_output=True,
            )
            logger.info(f"Registered MIME type handler: {mime_type}")
        except subprocess.CalledProcessError as e:
            raise HandlerCommandError(
                f"Failed to register MIME type handler: {e.stderr.decode()}\n  → Make sure xdg-utils is installed"
            ) from e
        except FileNotFoundError as e:
            raise HandlerCommandError("xdg-mime command not found\n  → Install xdg-utils package") from e

        # Verify registration
        try:
            result = subprocess.run(
                ["xdg-mime", "query", "default", mime_type],
                check=True,
                capture_output=True,
                text=True,
            )
            registered_handler = result.stdout.strip()
            if registered_handler != desktop_file_name:
                logger.warning(f"Handler verification failed: expected {desktop_file_name}, got {registered_handler}")
            else:
                logger.info(f"Verified handler registration: {registered_handler}")
        except subprocess.CalledProcessError:
            logger.warning("Failed to verify handler registration")

    # Add to registry
    registry = Registry(config.registry_file)
    handler_data = {
        "scheme": scheme,
        "desktop_file": str(desktop_file_path),
        "script": str(handler_script_path),
    }

    if not dry_run:
        try:
            registry.add_handler(handler_data)
            logger.info(f"Added handler to registry: {scheme}")
        except RegistryError as e:
            # Handler already exists, update it
            logger.warning(f"Handler already in registry, skipping: {e}")

    return {
        "scheme": scheme,
        "desktop_file": str(desktop_file_path),
        "script_path": str(handler_script_path),
        "mime_type": mime_type,
    }
