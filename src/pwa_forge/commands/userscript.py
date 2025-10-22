"""Implementation of userscript generation command."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pwa_forge.config import Config
from pwa_forge.templates import get_template_engine
from pwa_forge.utils.paths import expand_path

logger = logging.getLogger(__name__)


class UserscriptCommandError(Exception):
    """Base exception for userscript command errors."""


def generate_userscript(
    config: Config,
    scheme: str | None = None,
    in_scope_hosts: str | None = None,
    url_pattern: str = "*://*/*",
    out: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate a userscript for external link interception.

    Args:
        config: Configuration object.
        scheme: URL scheme to redirect to (default: from config).
        in_scope_hosts: Comma-separated list of hosts to keep in-app.
        url_pattern: URL pattern to match (default: all URLs).
        out: Output path for userscript.
        dry_run: If True, show what would be created without making changes.

    Returns:
        Dictionary with details of the generated userscript.

    Raises:
        UserscriptCommandError: If the operation fails.
    """
    logger.info("Generating userscript for external link interception")

    # Determine scheme
    if scheme is None:
        scheme = config.external_link_scheme
    logger.debug(f"Using scheme: {scheme}://")

    # Parse in-scope hosts
    hosts_list = [h.strip() for h in in_scope_hosts.split(",") if h.strip()] if in_scope_hosts else []
    logger.debug(f"In-scope hosts: {hosts_list}")

    # Determine output path
    userscript_path = config.userscripts_dir / "external-links.user.js" if out is None else expand_path(out)
    logger.debug(f"Userscript path: {userscript_path}")

    # Render userscript
    template_engine = get_template_engine()
    userscript_content = template_engine.render_userscript(
        scheme=scheme,
        in_scope_hosts=hosts_list,
        url_pattern=url_pattern,
    )

    # Write userscript
    if dry_run:
        logger.info(f"[DRY-RUN] Would write userscript to {userscript_path}")
        logger.debug(f"[DRY-RUN] Content:\n{userscript_content}")
    else:
        userscript_path.parent.mkdir(parents=True, exist_ok=True)
        userscript_path.write_text(userscript_content)
        logger.info(f"Generated userscript: {userscript_path}")

    # Print installation instructions
    if not dry_run:
        _print_installation_instructions(userscript_path, scheme)

    return {
        "scheme": scheme,
        "in_scope_hosts": hosts_list,
        "userscript_path": str(userscript_path),
    }


def _print_installation_instructions(userscript_path: Path, scheme: str) -> None:
    """Print instructions for installing the userscript.

    Args:
        userscript_path: Path to the generated userscript.
        scheme: URL scheme used for redirection.
    """
    print("\n" + "=" * 70)
    print("  Userscript Installation Instructions")
    print("=" * 70)
    print()
    print("To enable external link redirection in your PWA, follow these steps:")
    print()
    print("1. Install a userscript manager in your PWA profile:")
    print("   • Launch your PWA")
    print("   • Visit the Chrome Web Store or Firefox Add-ons")
    print("   • Install 'Violentmonkey' or 'Tampermonkey'")
    print()
    print("2. Install the generated userscript:")
    print("   • Open Violentmonkey/Tampermonkey dashboard")
    print("   • Click '+' or 'Create new script'")
    print(f"   • Copy the content from: {userscript_path}")
    print("   • Paste and save the script")
    print()
    print("3. Make sure the URL scheme handler is installed:")
    print(f"   pwa-forge generate-handler --scheme {scheme}")
    print(f"   pwa-forge install-handler --scheme {scheme}")
    print()
    print("4. Test external link redirection:")
    print("   • Click an external link in your PWA")
    print("   • It should open in your system browser")
    print()
    print("For more help, see the documentation or run:")
    print("   pwa-forge --help")
    print("=" * 70)
    print()
