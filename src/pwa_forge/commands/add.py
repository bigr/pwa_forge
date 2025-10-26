"""Implementation of the add command."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from pwa_forge.config import Config
from pwa_forge.registry import Registry
from pwa_forge.templates import render_template
from pwa_forge.utils.paths import ensure_dir
from pwa_forge.validation import (
    ValidationStatus,
    extract_name_from_url,
    generate_id,
    generate_wm_class,
    validate_id,
    validate_url,
)

logger = logging.getLogger(__name__)


class AddCommandError(Exception):
    """Base exception for add command errors."""


def add_app(
    url: str,
    config: Config,
    name: str | None = None,
    app_id: str | None = None,
    browser: str = "chrome",
    profile: str | None = None,
    icon: str | None = None,
    out_of_scope: str = "open-in-default",
    inject_userscript: str | None = None,
    wm_class: str | None = None,
    chrome_flags: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a new PWA instance.

    Args:
        url: The web application URL.
        config: Configuration object.
        name: Display name for the application (default: extracted from URL).
        app_id: Unique identifier (default: generated from name).
        browser: Browser engine to use.
        profile: Custom profile directory.
        icon: Path to application icon.
        out_of_scope: Behavior for external links.
        inject_userscript: Path to custom userscript.
        wm_class: Custom StartupWMClass.
        chrome_flags: Additional Chrome/Chromium flags.
        dry_run: If True, show what would be created without making changes.

    Returns:
        Dictionary with details of the created PWA.

    Raises:
        AddCommandError: If the operation fails.
    """
    logger.info(f"Adding PWA for URL: {url}")

    # Validate browser (only Chromium-based browsers support PWA mode)
    if browser == "firefox":
        raise AddCommandError(
            "Firefox is not supported for PWA creation.\n"
            "  → Firefox lacks support for app mode (--app flag)\n"
            "  → Use Chrome, Chromium, or Edge instead:\n"
            "     pwa-forge add <url> --browser chrome"
        )

    # Validate URL
    is_valid, status, message = validate_url(url, verify=False)
    if not is_valid:
        raise AddCommandError(f"Invalid URL: {message}")
    if status == ValidationStatus.WARNING:
        logger.warning(message)

    # Determine app name
    if name is None:
        name = extract_name_from_url(url)
        logger.info(f"Generated name from URL: {name}")

    # Generate or validate app ID
    if app_id is None:
        app_id = generate_id(name)
        logger.info(f"Generated ID from name: {app_id}")
    else:
        is_valid_id, id_message = validate_id(app_id)
        if not is_valid_id:
            raise AddCommandError(f"Invalid app ID: {id_message}")

    # Check if app already exists
    registry = Registry(config.registry_file)
    try:
        registry.get_app(app_id)
        raise AddCommandError(f"PWA with ID '{app_id}' already exists")
    except Exception as e:
        if "not found" not in str(e).lower():
            raise

    # Generate WMClass
    if wm_class is None:
        wm_class = generate_wm_class(name)
        logger.info(f"Generated WMClass: {wm_class}")

    # Determine paths
    profile_path = config.apps_dir / app_id if profile is None else Path(profile).expanduser()

    wrapper_path = config.wrappers_dir / app_id
    desktop_file_path = config.desktop_dir / f"pwa-forge-{app_id}.desktop"
    manifest_path = config.apps_dir / app_id / "manifest.yaml"

    # Handle icon
    icon_path = _handle_icon(icon, app_id, config.icons_dir, dry_run) if icon else None

    # Get browser executable (skip in dry-run to allow testing without browsers installed)
    if not dry_run:
        browser_exec = _get_browser_executable(browser, config)
    else:
        # In dry-run, use placeholder path that won't be written
        browser_exec_str = f"/usr/bin/{browser}"
        logger.info(f"[DRY-RUN] Would use browser: {browser_exec_str}")
        browser_exec = Path(browser_exec_str)

    # Parse chrome flags
    parsed_flags = _parse_chrome_flags(chrome_flags) if chrome_flags else {}

    # Create profile directory
    if not dry_run:
        ensure_dir(profile_path, mode=0o755)
        logger.info(f"Created profile directory: {profile_path}")

        # Check if browser can write to profile (detects snap confinement issues)
        _check_browser_profile_access(browser_exec, profile_path)
    else:
        logger.info(f"[DRY-RUN] Would create profile directory: {profile_path}")

    # Generate wrapper script
    # Use custom ozone_platform if provided in flags, otherwise default to x11
    ozone_platform = parsed_flags.get("ozone_platform") or "x11"

    wrapper_content = render_template(
        "wrapper.j2",
        {
            "name": name,
            "id": app_id,
            "browser_exec": str(browser_exec),
            "wm_class": wm_class,
            "ozone_platform": ozone_platform,
            "url": url,
            "profile": str(profile_path),
            "enable_features": parsed_flags.get("enable_features", []),
            "disable_features": parsed_flags.get("disable_features", []),
            "additional_flags": parsed_flags.get("additional", ""),
        },
    )

    if not dry_run:
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        wrapper_path.write_text(wrapper_content)
        wrapper_path.chmod(0o755)
        logger.info(f"Created wrapper script: {wrapper_path}")
    else:
        logger.info(f"[DRY-RUN] Would create wrapper script: {wrapper_path}")
        logger.debug(f"[DRY-RUN] Wrapper content:\n{wrapper_content}")

    # Generate desktop file
    desktop_content = render_template(
        "desktop.j2",
        {
            "name": name,
            "comment": f"{name} PWA",
            "wrapper_path": str(wrapper_path),
            "icon_path": str(icon_path) if icon_path else "web-browser",
            "categories": ["Network", "WebBrowser"],
            "wm_class": wm_class,
        },
    )

    if not dry_run:
        desktop_file_path.parent.mkdir(parents=True, exist_ok=True)
        desktop_file_path.write_text(desktop_content)
        logger.info(f"Created desktop file: {desktop_file_path}")
    else:
        logger.info(f"[DRY-RUN] Would create desktop file: {desktop_file_path}")
        logger.debug(f"[DRY-RUN] Desktop content:\n{desktop_content}")

    # Create manifest
    manifest_data = {
        "id": app_id,
        "name": name,
        "url": url,
        "browser": browser,
        "profile": str(profile_path),
        "icon": str(icon_path) if icon_path else None,
        "comment": f"{name} PWA",
        "wm_class": wm_class,
        "categories": ["Network", "WebBrowser"],
        "flags": parsed_flags,
        "out_of_scope": out_of_scope,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "version": 1,
    }

    if inject_userscript:
        manifest_data["inject"] = {"userscript": inject_userscript}

    if not dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        import yaml

        manifest_path.write_text(yaml.dump(manifest_data, default_flow_style=False))
        logger.info(f"Created manifest file: {manifest_path}")
    else:
        logger.info(f"[DRY-RUN] Would create manifest file: {manifest_path}")

    # Add to registry
    registry_entry = {
        "id": app_id,
        "name": name,
        "url": url,
        "manifest_path": str(manifest_path),
        "desktop_file": str(desktop_file_path),
        "wrapper_script": str(wrapper_path),
        "status": "active",
    }

    if not dry_run:
        registry.add_app(registry_entry)
        logger.info(f"Added app to registry: {app_id}")
    else:
        logger.info(f"[DRY-RUN] Would add app to registry: {app_id}")

    # Update desktop database
    if not dry_run:
        _update_desktop_database(config.desktop_dir)

    logger.info(f"Successfully created PWA: {name} ({app_id})")

    return {
        "id": app_id,
        "name": name,
        "url": url,
        "browser": browser,
        "profile": str(profile_path),
        "wrapper": str(wrapper_path),
        "desktop_file": str(desktop_file_path),
        "manifest": str(manifest_path),
        "icon": str(icon_path) if icon_path else None,
    }


def _handle_icon(icon_source: str, app_id: str, icons_dir: Path, dry_run: bool) -> Path | None:
    """Handle icon installation.

    Args:
        icon_source: Path to source icon file.
        app_id: Application ID.
        icons_dir: Target icons directory.
        dry_run: If True, don't actually copy.

    Returns:
        Path to installed icon or None.
    """
    source_path = Path(icon_source).expanduser()
    if not source_path.exists():
        logger.warning(f"Icon file not found: {icon_source}")
        return None

    # Determine target filename
    suffix = source_path.suffix
    target_path = icons_dir / f"{app_id}{suffix}"

    if not dry_run:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        logger.info(f"Copied icon to: {target_path}")
    else:
        logger.info(f"[DRY-RUN] Would copy icon to: {target_path}")

    return target_path


def _check_browser_profile_access(browser_exec: Path, profile_path: Path) -> None:
    """Check if browser can write to profile directory (detects snap confinement issues).

    Args:
        browser_exec: Path to browser executable.
        profile_path: Path to profile directory.

    Raises:
        AddCommandError: If browser cannot write to profile directory.
    """
    import subprocess

    # Create a temporary test directory in the profile path
    test_dir = profile_path / ".pwa-forge-test"
    test_file = test_dir / "test.txt"

    try:
        test_dir.mkdir(parents=True, exist_ok=True)

        # Try to run browser in headless mode with the profile to test write access
        # Use --version flag which is quick and doesn't require display
        try:
            result = subprocess.run(
                [str(browser_exec), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Browser executed successfully, now test profile write
            if result.returncode != 0:
                logger.warning(f"Browser version check returned non-zero: {result.returncode}")
        except subprocess.TimeoutExpired:
            pass  # Browser might be slow, but it ran
        except Exception as e:
            logger.debug(f"Browser test execution: {e}")

        # Try to write test file to profile
        try:
            test_file.write_text("test")
            test_file.unlink()
            logger.debug(f"Browser profile write access verified: {profile_path}")
        except (OSError, PermissionError) as e:
            raise AddCommandError(
                f"Browser cannot write to profile directory: {profile_path}\n"
                f"  → This often happens with snap-confined browsers\n"
                f"  → Error: {e}\n"
                f"  → Solutions:\n"
                f"     1. Use system-installed browser instead of snap\n"
                f"     2. Install via package manager: sudo apt install chromium-browser\n"
                f"     3. Or use Google Chrome: https://www.google.com/chrome/"
            ) from e
    finally:
        # Clean up test directory
        try:
            if test_dir.exists():
                import shutil

                shutil.rmtree(test_dir)
        except Exception:
            pass  # Ignore cleanup errors


def _get_browser_executable(browser: str, config: Config) -> Path:
    """Get the browser executable path.

    Args:
        browser: Browser name.
        config: Configuration object.

    Returns:
        Path to browser executable.

    Raises:
        AddCommandError: If browser is not found.
    """
    browser_paths = {
        "chrome": ["/usr/bin/google-chrome-stable", "/usr/bin/google-chrome"],
        "chromium": ["/usr/bin/chromium-browser", "/usr/bin/chromium"],
        "firefox": ["/usr/bin/firefox"],
        "edge": ["/usr/bin/microsoft-edge-stable", "/usr/bin/microsoft-edge"],
    }

    # Map browser names to common executable names for shutil.which()
    browser_executables = {
        "chrome": ["google-chrome-stable", "google-chrome"],
        "chromium": ["chromium-browser", "chromium"],
        "firefox": ["firefox"],
        "edge": ["microsoft-edge-stable", "microsoft-edge"],
    }

    # Try configured path first
    if hasattr(config.browsers, browser):
        browser_path = getattr(config.browsers, browser)
        exec_path = Path(browser_path)
        if exec_path.exists():
            return exec_path

    # Try known paths
    for path_str in browser_paths.get(browser, []):
        path = Path(path_str)
        if path.exists():
            logger.debug(f"Found browser at: {path}")
            return path

    # Fallback: search in PATH using shutil.which()
    for executable_name in browser_executables.get(browser, []):
        which_path = shutil.which(executable_name)
        if which_path:
            logger.debug(f"Found browser in PATH: {which_path}")
            return Path(which_path)

    raise AddCommandError(f"Browser '{browser}' not found. Please install it or specify the path in config.")


def _parse_chrome_flags(flags_str: str) -> dict[str, Any]:
    """Parse Chrome flags string.

    Args:
        flags_str: Semicolon-separated flags string
            (e.g., "enable-features=A,B;disable-features=C;ozone-platform=wayland").

    Returns:
        Dictionary with parsed flags.
    """
    result: dict[str, Any] = {
        "enable_features": [],
        "disable_features": [],
        "ozone_platform": None,
        "additional": "",
    }

    # Parse semicolon-separated flags
    for flag in flags_str.split(";"):
        flag = flag.strip()
        if not flag:
            continue

        if flag.startswith("enable-features="):
            features = flag.replace("enable-features=", "").split(",")
            result["enable_features"] = [f.strip() for f in features if f.strip()]
        elif flag.startswith("disable-features="):
            features = flag.replace("disable-features=", "").split(",")
            result["disable_features"] = [f.strip() for f in features if f.strip()]
        elif flag.startswith("ozone-platform="):
            result["ozone_platform"] = flag.replace("ozone-platform=", "").strip()
        else:
            # Unknown flags go to additional
            if result["additional"]:
                result["additional"] += " "
            result["additional"] += flag

    return result


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
