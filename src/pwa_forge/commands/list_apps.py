"""Implementation of the list command."""

from __future__ import annotations

import json
import logging
from typing import Any

from pwa_forge.config import Config
from pwa_forge.registry import Registry

logger = logging.getLogger(__name__)


def list_apps(
    config: Config,
    verbose: bool = False,
    output_format: str = "table",
) -> list[dict[str, Any]]:
    """List all managed PWA instances.

    Args:
        config: Configuration object.
        verbose: Show detailed information.
        output_format: Output format (table, json, yaml).

    Returns:
        List of PWA entries.
    """
    registry = Registry(config.registry_file)
    apps = registry.list_apps()

    if not apps:
        logger.info("No PWAs found")
        return []

    if output_format == "json":
        print(json.dumps(apps, indent=2))
    elif output_format == "yaml":
        import yaml

        print(yaml.dump(apps, default_flow_style=False))
    else:
        # Table format
        _print_table(apps, verbose)

    return apps


def _print_table(apps: list[dict[str, Any]], verbose: bool) -> None:
    """Print apps in table format.

    Args:
        apps: List of app entries.
        verbose: Show detailed information.
    """
    if verbose:
        # Verbose mode - show all fields
        for app in apps:
            print(f"\nID: {app.get('id', 'N/A')}")
            print(f"  Name: {app.get('name', 'N/A')}")
            print(f"  URL: {app.get('url', 'N/A')}")
            print(f"  Status: {app.get('status', 'N/A')}")
            print(f"  Desktop File: {app.get('desktop_file', 'N/A')}")
            print(f"  Wrapper Script: {app.get('wrapper_script', 'N/A')}")
            print(f"  Manifest: {app.get('manifest_path', 'N/A')}")
    else:
        # Compact table
        header = f"{'ID':<20} {'Name':<25} {'URL':<40} {'Status':<10}"
        print(header)
        print("-" * len(header))

        for app in apps:
            app_id = app.get("id", "N/A")[:19]
            name = app.get("name", "N/A")[:24]
            url = app.get("url", "N/A")[:39]
            status = app.get("status", "N/A")[:9]
            print(f"{app_id:<20} {name:<25} {url:<40} {status:<10}")
