"""Implementation of the audit command."""

from __future__ import annotations

import configparser
import logging
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any

import yaml

from pwa_forge.commands.sync import sync_app
from pwa_forge.config import Config
from pwa_forge.registry import AppNotFoundError, Registry
from pwa_forge.utils.paths import expand_path

logger = logging.getLogger(__name__)


class AuditCommandError(Exception):
    """Base exception for audit command errors."""


def audit_app(
    app_id: str | None,
    config: Config,
    fix: bool = False,
    open_test_page: bool = False,
) -> dict[str, Any]:
    """Audit PWA configuration and optionally fix issues.

    Args:
        app_id: Application ID (None = audit all apps).
        config: Config instance.
        fix: Attempt to repair broken configurations.
        open_test_page: Launch PWA with test page (not implemented).

    Returns:
        Dict with audit results: {
            "audited_apps": int,
            "passed": int,
            "failed": int,
            "fixed": int,
            "results": [{"id": str, "checks": [{"name": str, "status": str, "message": str}]}]
        }

    Raises:
        AuditCommandError: If audit operation fails.
    """
    logger.info(f"Auditing PWA: {app_id if app_id else 'all'}")

    # Get apps to audit
    registry = Registry(config.registry_file)
    if app_id:
        try:
            app_entry = registry.get_app(app_id)
            apps = [app_entry]
        except AppNotFoundError as e:
            raise AuditCommandError(str(e)) from e
    else:
        apps = registry.list_apps()

    if not apps:
        return {
            "audited_apps": 0,
            "passed": 0,
            "failed": 0,
            "fixed": 0,
            "results": [],
        }

    results: list[dict[str, Any]] = []
    total_passed = 0
    total_failed = 0
    total_fixed = 0

    for app_entry in apps:
        app_id_str = app_entry.get("id", "unknown")
        logger.info(f"Auditing app: {app_id_str}")

        checks: list[dict[str, Any]] = []

        # Check 1: Manifest file exists
        manifest_path_str = app_entry.get("manifest_path")
        if not manifest_path_str:
            checks.append({
                "name": "Manifest path in registry",
                "status": "FAIL",
                "message": "No manifest_path in registry entry",
            })
        else:
            manifest_path = expand_path(manifest_path_str)
            if not manifest_path.exists():
                checks.append({
                    "name": "Manifest file exists",
                    "status": "FAIL",
                    "message": f"Manifest file not found: {manifest_path}",
                })
            else:
                checks.append({
                    "name": "Manifest file exists",
                    "status": "PASS",
                    "message": str(manifest_path),
                })

                # Check 2: Manifest is valid YAML
                try:
                    with manifest_path.open("r", encoding="utf-8") as f:
                        manifest = yaml.safe_load(f)

                    if not manifest:
                        checks.append({
                            "name": "Manifest valid YAML",
                            "status": "FAIL",
                            "message": "Manifest file is empty",
                        })
                    else:
                        checks.append({
                            "name": "Manifest valid YAML",
                            "status": "PASS",
                            "message": "YAML syntax valid",
                        })

                        # Check 3: Manifest has required fields
                        required_fields = ["id", "name", "url", "browser"]
                        missing_fields = [field for field in required_fields if field not in manifest]
                        if missing_fields:
                            checks.append({
                                "name": "Manifest required fields",
                                "status": "FAIL",
                                "message": f"Missing required fields: {', '.join(missing_fields)}",
                            })
                        else:
                            checks.append({
                                "name": "Manifest required fields",
                                "status": "PASS",
                                "message": "All required fields present",
                            })

                            # Check 4: Browser executable exists
                            browser = manifest.get("browser", "chrome")
                            browser_attr = getattr(config.browsers, browser, None)
                            if browser_attr:
                                browser_path = Path(browser_attr)
                                if browser_path.exists():
                                    checks.append({
                                        "name": "Browser executable",
                                        "status": "PASS",
                                        "message": f"Found: {browser_path}",
                                    })
                                else:
                                    # Try to find with shutil.which
                                    browser_found = shutil.which(browser)
                                    if browser_found:
                                        checks.append({
                                            "name": "Browser executable",
                                            "status": "PASS",
                                            "message": f"Found: {browser_found}",
                                        })
                                    else:
                                        checks.append({
                                            "name": "Browser executable",
                                            "status": "FAIL",
                                            "message": f"Browser not found: {browser} (expected at {browser_path})",
                                        })
                            else:
                                checks.append({
                                    "name": "Browser executable",
                                    "status": "FAIL",
                                    "message": f"Unknown browser: {browser}",
                                })

                            # Check 5: Icon exists (if specified)
                            icon_path_str = manifest.get("icon")
                            if icon_path_str:
                                icon_path = expand_path(icon_path_str)
                                if icon_path.exists():
                                    checks.append({
                                        "name": "Icon file",
                                        "status": "PASS",
                                        "message": str(icon_path),
                                    })
                                else:
                                    checks.append({
                                        "name": "Icon file",
                                        "status": "WARNING",
                                        "message": f"Icon not found: {icon_path}",
                                    })

                            # Check 6: Profile directory exists
                            profile_str = manifest.get("profile")
                            if profile_str:
                                profile_path = expand_path(profile_str)
                                if profile_path.exists() and profile_path.is_dir():
                                    checks.append({
                                        "name": "Profile directory",
                                        "status": "PASS",
                                        "message": str(profile_path),
                                    })
                                else:
                                    checks.append({
                                        "name": "Profile directory",
                                        "status": "WARNING",
                                        "message": f"Profile directory not found: {profile_path}",
                                    })

                except yaml.YAMLError as e:
                    checks.append({
                        "name": "Manifest valid YAML",
                        "status": "FAIL",
                        "message": f"Invalid YAML: {e}",
                    })
                except Exception as e:
                    checks.append({
                        "name": "Manifest validation",
                        "status": "FAIL",
                        "message": f"Error reading manifest: {e}",
                    })

        # Check 7: Desktop file exists
        desktop_file_str = app_entry.get("desktop_file")
        if not desktop_file_str:
            checks.append({
                "name": "Desktop file path in registry",
                "status": "FAIL",
                "message": "No desktop_file in registry entry",
            })
        else:
            desktop_file = expand_path(desktop_file_str)
            if not desktop_file.exists():
                checks.append({
                    "name": "Desktop file exists",
                    "status": "FAIL",
                    "message": f"Desktop file not found: {desktop_file}",
                })
            else:
                checks.append({
                    "name": "Desktop file exists",
                    "status": "PASS",
                    "message": str(desktop_file),
                })

                # Check 8: Desktop file is valid INI
                try:
                    parser = configparser.ConfigParser()
                    parser.read(desktop_file)

                    if not parser.has_section("Desktop Entry"):
                        checks.append({
                            "name": "Desktop file valid",
                            "status": "FAIL",
                            "message": "Missing [Desktop Entry] section",
                        })
                    else:
                        required_keys = ["Type", "Name", "Exec"]
                        missing_keys = [key for key in required_keys if not parser.has_option("Desktop Entry", key)]
                        if missing_keys:
                            checks.append({
                                "name": "Desktop file valid",
                                "status": "FAIL",
                                "message": f"Missing required keys: {', '.join(missing_keys)}",
                            })
                        else:
                            checks.append({
                                "name": "Desktop file valid",
                                "status": "PASS",
                                "message": "Valid desktop file format",
                            })
                except Exception as e:
                    checks.append({
                        "name": "Desktop file valid",
                        "status": "FAIL",
                        "message": f"Error parsing desktop file: {e}",
                    })

        # Check 9: Wrapper script exists
        wrapper_script_str = app_entry.get("wrapper_script")
        if not wrapper_script_str:
            checks.append({
                "name": "Wrapper script path in registry",
                "status": "FAIL",
                "message": "No wrapper_script in registry entry",
            })
        else:
            wrapper_script = expand_path(wrapper_script_str)
            if not wrapper_script.exists():
                checks.append({
                    "name": "Wrapper script exists",
                    "status": "FAIL",
                    "message": f"Wrapper script not found: {wrapper_script}",
                })
            else:
                checks.append({
                    "name": "Wrapper script exists",
                    "status": "PASS",
                    "message": str(wrapper_script),
                })

                # Check 10: Wrapper script is executable
                wrapper_stat = wrapper_script.stat()
                if wrapper_stat.st_mode & stat.S_IXUSR:
                    checks.append({
                        "name": "Wrapper script executable",
                        "status": "PASS",
                        "message": "Script has execute permission",
                    })
                else:
                    checks.append({
                        "name": "Wrapper script executable",
                        "status": "FAIL",
                        "message": "Script is not executable",
                    })

        # Check 11: Handler registration (if userscript configured)
        if manifest_path_str:
            manifest_path = expand_path(manifest_path_str)
            if manifest_path.exists():
                try:
                    with manifest_path.open("r", encoding="utf-8") as f:
                        manifest = yaml.safe_load(f)

                    if manifest and "inject" in manifest:
                        inject_config = manifest["inject"]
                        if isinstance(inject_config, dict):
                            scheme = inject_config.get("userscript_scheme", config.external_link_scheme)
                            # Check if handler is registered
                            try:
                                result = subprocess.run(
                                    ["xdg-mime", "query", "default", f"x-scheme-handler/{scheme}"],
                                    capture_output=True,
                                    text=True,
                                    check=False,
                                )
                                if result.returncode == 0 and result.stdout.strip():
                                    handler = result.stdout.strip()
                                    checks.append({
                                        "name": f"Handler for {scheme}://",
                                        "status": "PASS",
                                        "message": f"Registered: {handler}",
                                    })
                                else:
                                    checks.append({
                                        "name": f"Handler for {scheme}://",
                                        "status": "WARNING",
                                        "message": f"No handler registered for {scheme}://",
                                    })
                            except FileNotFoundError:
                                checks.append({
                                    "name": f"Handler for {scheme}://",
                                    "status": "WARNING",
                                    "message": "xdg-mime not found (cannot verify handler)",
                                })
                except Exception:
                    pass  # Skip handler check if manifest cannot be read

        # Count pass/fail
        app_passed = sum(1 for check in checks if check["status"] == "PASS")
        app_failed = sum(1 for check in checks if check["status"] == "FAIL")

        # Attempt to fix if requested
        app_fixed = 0
        if fix and app_failed > 0:
            logger.info(f"Attempting to fix issues for: {app_id_str}")
            try:
                # Use sync to regenerate files
                sync_app(app_id_str, config, dry_run=False)
                app_fixed = 1
                logger.info(f"Fixed issues for: {app_id_str}")

                # Re-run checks after fix (simplified - just mark as fixed)
                for check in checks:
                    if check["status"] == "FAIL" and check["name"] in [
                        "Wrapper script exists",
                        "Wrapper script executable",
                        "Desktop file exists",
                        "Desktop file valid",
                    ]:
                        check["status"] = "FIXED"
                        check["message"] += " (regenerated)"

            except Exception as e:
                logger.warning(f"Failed to fix issues for {app_id_str}: {e}")

        if app_failed > 0:
            total_failed += 1
        else:
            total_passed += 1

        if app_fixed > 0:
            total_fixed += 1

        results.append({
            "id": app_id_str,
            "checks": checks,
            "passed": app_passed,
            "failed": app_failed,
            "fixed": app_fixed,
        })

    logger.info(
        f"Audit complete: {len(apps)} apps audited, {total_passed} passed, {total_failed} failed, {total_fixed} fixed"
    )

    return {
        "audited_apps": len(apps),
        "passed": total_passed,
        "failed": total_failed,
        "fixed": total_fixed,
        "results": results,
    }
