"""System diagnostics command for PWA Forge."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from pwa_forge.config import Config
from pwa_forge.utils.logger import get_logger
from pwa_forge.utils.paths import get_app_config_dir, get_app_data_dir

__all__ = ["DoctorCommandError", "run_doctor"]

logger = get_logger(__name__)


class DoctorCommandError(Exception):
    """Raised when a doctor command operation fails."""


def run_doctor(config: Config) -> dict[str, Any]:
    """Check system requirements and configuration.

    Args:
        config: Current Config instance.

    Returns:
        Dictionary with check results: {
            "checks": [{"name": str, "status": str, "message": str, "details": str}],
            "passed": int,
            "failed": int,
            "warnings": int,
        }
    """
    checks: list[dict[str, str]] = []

    # Check Python version
    checks.append(_check_python_version())

    # Check available browsers
    checks.extend(_check_browsers(config))

    # Check XDG utilities
    checks.extend(_check_xdg_tools())

    # Check directory permissions
    checks.extend(_check_directory_permissions(config))

    # Check desktop environment
    checks.append(_check_desktop_environment())

    # Check config file validity
    checks.append(_check_config_file())

    # Check registry file validity
    checks.append(_check_registry_file())

    # Check optional dependencies
    checks.append(_check_playwright())

    # Count results
    passed = sum(1 for c in checks if c["status"] == "PASS")
    failed = sum(1 for c in checks if c["status"] == "FAIL")
    warnings = sum(1 for c in checks if c["status"] == "WARNING")

    return {
        "checks": checks,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
    }


def _check_python_version() -> dict[str, str]:
    """Check if Python version is >= 3.10."""
    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    if version_info >= (3, 10):
        return {
            "name": "Python Version",
            "status": "PASS",
            "message": f"Python {version_str}",
            "details": "Python 3.10+ is installed",
        }
    else:
        return {
            "name": "Python Version",
            "status": "FAIL",
            "message": f"Python {version_str} (requires >= 3.10)",
            "details": "Please upgrade to Python 3.10 or higher",
        }


def _check_browsers(config: Config) -> list[dict[str, str]]:
    """Check availability of browser executables."""
    checks = []
    # PWA-compatible browsers (Chromium-based only)
    pwa_browsers = {
        "chrome": config.browsers.chrome,
        "chromium": config.browsers.chromium,
        "edge": config.browsers.edge,
    }
    # Firefox only for URL handlers
    other_browsers = {
        "firefox": config.browsers.firefox,
    }

    found_pwa_browser = False

    # Check Chromium-based browsers (PWA-compatible)
    for browser_name, browser_path in pwa_browsers.items():
        path = Path(browser_path)

        if path.exists() and path.is_file():
            found_pwa_browser = True
            checks.append({
                "name": f"Browser: {browser_name}",
                "status": "PASS",
                "message": str(path),
                "details": f"{browser_name.capitalize()} is available (PWA-compatible)",
            })
        else:
            # Try to find it in PATH
            found_path = shutil.which(browser_name)
            if found_path:
                found_pwa_browser = True
                checks.append({
                    "name": f"Browser: {browser_name}",
                    "status": "PASS",
                    "message": found_path,
                    "details": f"{browser_name.capitalize()} found in PATH (PWA-compatible)",
                })
            else:
                checks.append({
                    "name": f"Browser: {browser_name}",
                    "status": "WARNING",
                    "message": "Not found",
                    "details": f"Install {browser_name} or update config path",
                })

    # Check other browsers (handlers only)
    for browser_name, browser_path in other_browsers.items():
        path = Path(browser_path)

        if path.exists() and path.is_file():
            checks.append({
                "name": f"Browser: {browser_name}",
                "status": "INFO",
                "message": str(path),
                "details": f"{browser_name.capitalize()} available (URL handlers only, not PWA-compatible)",
            })
        else:
            found_path = shutil.which(browser_name)
            if found_path:
                checks.append({
                    "name": f"Browser: {browser_name}",
                    "status": "INFO",
                    "message": found_path,
                    "details": f"{browser_name.capitalize()} found (URL handlers only, not PWA-compatible)",
                })

    if not found_pwa_browser:
        checks.append({
            "name": "PWA Browser Availability",
            "status": "FAIL",
            "message": "No PWA-compatible browsers found",
            "details": "At least one Chromium-based browser is required (chrome, chromium, or edge)",
        })

    return checks


def _check_xdg_tools() -> list[dict[str, str]]:
    """Check availability of XDG utilities."""
    checks = []
    tools = ["xdg-mime", "update-desktop-database"]

    for tool in tools:
        tool_path = shutil.which(tool)
        if tool_path:
            checks.append({
                "name": f"XDG Tool: {tool}",
                "status": "PASS",
                "message": tool_path,
                "details": f"{tool} is available",
            })
        else:
            checks.append({
                "name": f"XDG Tool: {tool}",
                "status": "FAIL",
                "message": "Not found",
                "details": f"Install xdg-utils package (provides {tool})",
            })

    return checks


def _check_directory_permissions(config: Config) -> list[dict[str, str]]:
    """Check write permissions for required directories."""
    checks = []
    directories = [
        ("Desktop Applications", config.desktop_dir),
        ("Icons", config.icons_dir),
        ("Wrappers", config.wrappers_dir),
        ("Apps Data", config.apps_dir),
        ("Userscripts", config.userscripts_dir),
    ]

    for name, directory in directories:
        try:
            # Create directory if it doesn't exist
            directory.mkdir(parents=True, exist_ok=True)

            # Try to write a test file
            test_file = directory / ".pwa-forge-test-write"
            test_file.write_text("test")
            test_file.unlink()

            checks.append({
                "name": f"Directory: {name}",
                "status": "PASS",
                "message": str(directory),
                "details": f"Writable: {directory}",
            })
        except (PermissionError, OSError) as e:
            checks.append({
                "name": f"Directory: {name}",
                "status": "FAIL",
                "message": str(directory),
                "details": f"Cannot write to directory: {e}",
            })

    return checks


def _check_desktop_environment() -> dict[str, str]:
    """Check desktop environment detection."""
    de = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")
    session_type = os.environ.get("XDG_SESSION_TYPE", "Unknown")

    if de != "Unknown":
        return {
            "name": "Desktop Environment",
            "status": "PASS",
            "message": f"{de} ({session_type})",
            "details": f"Detected: {de} on {session_type}",
        }
    else:
        return {
            "name": "Desktop Environment",
            "status": "WARNING",
            "message": "Not detected",
            "details": "XDG_CURRENT_DESKTOP not set (may work anyway)",
        }


def _check_config_file() -> dict[str, str]:
    """Check if config file exists and is valid."""
    config_path = get_app_config_dir() / "config.yaml"

    if not config_path.exists():
        return {
            "name": "Config File",
            "status": "INFO",
            "message": "Not found (using defaults)",
            "details": f"No user config at {config_path}",
        }

    try:
        with config_path.open("r", encoding="utf-8") as f:
            yaml.safe_load(f)

        return {
            "name": "Config File",
            "status": "PASS",
            "message": str(config_path),
            "details": "Config file is valid YAML",
        }
    except yaml.YAMLError as e:
        return {
            "name": "Config File",
            "status": "FAIL",
            "message": str(config_path),
            "details": f"Invalid YAML: {e}",
        }
    except Exception as e:
        return {
            "name": "Config File",
            "status": "FAIL",
            "message": str(config_path),
            "details": f"Error reading file: {e}",
        }


def _check_registry_file() -> dict[str, str]:
    """Check if registry file exists and is valid."""
    import json

    registry_path = get_app_data_dir() / "registry.json"

    if not registry_path.exists():
        return {
            "name": "Registry File",
            "status": "INFO",
            "message": "Not found (no PWAs registered)",
            "details": f"No registry at {registry_path}",
        }

    try:
        with registry_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {
                "name": "Registry File",
                "status": "FAIL",
                "message": str(registry_path),
                "details": "Invalid format: not a JSON object",
            }

        num_apps = len(data.get("apps", []))
        num_handlers = len(data.get("handlers", []))

        return {
            "name": "Registry File",
            "status": "PASS",
            "message": str(registry_path),
            "details": f"Valid registry: {num_apps} PWAs, {num_handlers} handlers",
        }
    except json.JSONDecodeError as e:
        return {
            "name": "Registry File",
            "status": "FAIL",
            "message": str(registry_path),
            "details": f"Invalid JSON: {e}",
        }
    except Exception as e:
        return {
            "name": "Registry File",
            "status": "FAIL",
            "message": str(registry_path),
            "details": f"Error reading file: {e}",
        }


def _check_playwright() -> dict[str, str]:
    """Check if Playwright is installed (optional dependency)."""
    try:
        import playwright  # noqa: F401

        # Try to check if browsers are installed
        try:
            result = subprocess.run(
                ["python3", "-m", "playwright", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = result.stdout.strip() if result.returncode == 0 else "unknown"

            return {
                "name": "Playwright (optional)",
                "status": "PASS",
                "message": version,
                "details": "Playwright is installed for browser testing",
            }
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return {
                "name": "Playwright (optional)",
                "status": "PASS",
                "message": "Installed",
                "details": "Playwright package is available",
            }
    except ImportError:
        return {
            "name": "Playwright (optional)",
            "status": "INFO",
            "message": "Not installed",
            "details": "Install with: pip install pwa-forge[playwright]",
        }
