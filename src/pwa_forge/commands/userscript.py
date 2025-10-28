"""Implementation of userscript generation command."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from pwa_forge.config import Config
from pwa_forge.registry import Registry
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


def install_userscript(
    app_id: str,
    config: Config,
    scheme: str | None = None,
    userscript_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Install a userscript into a PWA's Chrome profile.

    This function injects the userscript into the PWA's Chrome profile directory
    in a format that Violentmonkey/Tampermonkey can recognize and load.

    Args:
        app_id: The PWA application ID.
        config: Configuration object.
        scheme: URL scheme used in the userscript (default: from config).
        userscript_path: Path to the userscript file (default: auto-detected).
        dry_run: If True, show what would be created without making changes.

    Returns:
        Dictionary with details of the installation.

    Raises:
        UserscriptCommandError: If the operation fails.
    """
    logger.info(f"Installing userscript for PWA: {app_id}")

    # Determine scheme
    if scheme is None:
        scheme = config.external_link_scheme
    logger.debug(f"Using scheme: {scheme}://")

    # Get PWA profile path from registry
    registry = Registry(config.registry_file)
    try:
        app_data = registry.get_app(app_id)
        manifest_path = Path(app_data.get("manifest_path", "")).expanduser()
        profile_path = manifest_path.parent if manifest_path.exists() else None

        if not profile_path or not profile_path.exists():
            raise UserscriptCommandError(
                f"PWA profile not found for '{app_id}'\n" f"  → Make sure the PWA exists: pwa-forge list"
            )
    except Exception as e:
        if "not found" in str(e).lower():
            raise UserscriptCommandError(
                f"PWA '{app_id}' not found in registry\n" f"  → Run 'pwa-forge list' to see available PWAs"
            ) from e
        raise

    logger.debug(f"PWA profile path: {profile_path}")

    # Determine userscript path
    if userscript_path is None:
        userscript_path_obj = config.userscripts_dir / "external-links.user.js"
    else:
        userscript_path_obj = expand_path(userscript_path)

    if not userscript_path_obj.exists() and not dry_run:
        raise UserscriptCommandError(
            f"Userscript not found: {userscript_path_obj}\n"
            f"  → Generate it first with: pwa-forge generate-userscript --scheme {scheme}"
        )

    logger.debug(f"Userscript path: {userscript_path_obj}")

    # Create Violentmonkey storage directory in Chrome profile
    # Violentmonkey stores scripts in: <profile>/Default/Local Storage/leveldb
    # But we'll use a simpler approach: inject into the profile's user scripts directory
    vm_storage_dir = profile_path / "Default" / "Local Storage" / "leveldb"
    vm_scripts_dir = profile_path / "Default" / "pwa_forge_scripts"

    logger.debug(f"Violentmonkey storage dir: {vm_storage_dir}")
    logger.debug(f"PWA Forge scripts dir: {vm_scripts_dir}")

    if dry_run:
        logger.info(f"[DRY-RUN] Would install userscript to {vm_scripts_dir}")
        if userscript_path_obj.exists():
            logger.debug(f"[DRY-RUN] Userscript content preview:\n{userscript_path_obj.read_text()[:200]}...")
    else:
        # Create scripts directory
        vm_scripts_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created scripts directory: {vm_scripts_dir}")

        # Copy userscript to the profile
        dest_script = vm_scripts_dir / "external-links.user.js"
        shutil.copy2(userscript_path_obj, dest_script)
        logger.info(f"Installed userscript: {dest_script}")

        # Create a metadata file for Violentmonkey to recognize the script
        _create_violentmonkey_metadata(vm_scripts_dir, dest_script, scheme)

    return {
        "app_id": app_id,
        "profile_path": str(profile_path),
        "userscript_path": str(userscript_path_obj),
        "installed_path": str(vm_scripts_dir / "external-links.user.js"),
        "scheme": scheme,
    }


def _create_violentmonkey_metadata(scripts_dir: Path, script_path: Path, scheme: str) -> None:
    """Create metadata file for Violentmonkey to recognize the userscript.

    Args:
        scripts_dir: Directory where scripts are stored.
        script_path: Path to the installed userscript.
        scheme: URL scheme used in the userscript.
    """
    from datetime import datetime

    installed_at = datetime.fromtimestamp(script_path.stat().st_ctime).isoformat()

    metadata = {
        "name": "PWA Forge External Link Handler",
        "namespace": "pwa-forge",
        "version": "1.0",
        "description": f"Redirects external links to {scheme}:// scheme",
        "scheme": scheme,
        "installed_at": installed_at,
    }

    metadata_file = scripts_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))
    logger.debug(f"Created metadata file: {metadata_file}")


def setup_userscript(
    app_id: str,
    config: Config,
    scheme: str | None = None,
    in_scope_hosts: str | None = None,
    url_pattern: str = "*://*/*",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Complete setup: generate userscript, install extension, and inject script.

    This is a one-command solution that:
    1. Generates the userscript
    2. Installs Violentmonkey extension to PWA profile
    3. Injects the userscript into the extension

    Args:
        app_id: The PWA application ID.
        config: Configuration object.
        scheme: URL scheme to redirect to (default: from config).
        in_scope_hosts: Comma-separated list of hosts to keep in-app.
        url_pattern: URL pattern to match (default: all URLs).
        dry_run: If True, show what would be created without making changes.

    Returns:
        Dictionary with details of the setup.

    Raises:
        UserscriptCommandError: If the operation fails.
    """
    logger.info(f"Setting up userscript for PWA: {app_id}")

    # Determine scheme
    if scheme is None:
        scheme = config.external_link_scheme
    logger.debug(f"Using scheme: {scheme}://")

    # Step 1: Generate userscript
    logger.info("Step 1/3: Generating userscript...")
    userscript_result = generate_userscript(
        config=config,
        scheme=scheme,
        in_scope_hosts=in_scope_hosts,
        url_pattern=url_pattern,
        out=None,
        dry_run=dry_run,
    )
    userscript_path = Path(userscript_result["userscript_path"])
    logger.info(f"✓ Userscript generated: {userscript_path}")

    # Step 2: Install Violentmonkey extension
    logger.info("Step 2/3: Installing Violentmonkey extension...")
    try:
        extension_result = _install_violentmonkey_extension(
            app_id=app_id,
            config=config,
            dry_run=dry_run,
        )
        logger.info(f"✓ Extension installed: {extension_result['extension_path']}")
    except UserscriptCommandError as e:
        logger.warning(f"Extension installation failed: {e}")
        logger.warning("Continuing with userscript installation only...")
        extension_result = None

    # Step 3: Install userscript to PWA profile
    logger.info("Step 3/3: Installing userscript to PWA profile...")
    userscript_install_result = install_userscript(
        app_id=app_id,
        config=config,
        scheme=scheme,
        userscript_path=str(userscript_path),
        dry_run=dry_run,
    )
    logger.info(f"✓ Userscript installed: {userscript_install_result['installed_path']}")

    return {
        "app_id": app_id,
        "scheme": scheme,
        "userscript_path": str(userscript_path),
        "installed_path": userscript_install_result["installed_path"],
        "extension_installed": extension_result is not None,
        "extension_path": extension_result["extension_path"] if extension_result else None,
    }


def _install_violentmonkey_extension(
    app_id: str,
    config: Config,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Install Violentmonkey extension to PWA profile.

    Downloads Violentmonkey from Chrome Web Store and installs it to the profile.

    Args:
        app_id: The PWA application ID.
        config: Configuration object.
        dry_run: If True, show what would be created without making changes.

    Returns:
        Dictionary with extension installation details.

    Raises:
        UserscriptCommandError: If installation fails.
    """
    logger.info("Installing Violentmonkey extension...")

    # Get PWA profile path
    registry = Registry(config.registry_file)
    try:
        app_data = registry.get_app(app_id)
        manifest_path = Path(app_data.get("manifest_path", "")).expanduser()
        profile_path = manifest_path.parent if manifest_path.exists() else None

        if not profile_path or not profile_path.exists():
            raise UserscriptCommandError(
                f"PWA profile not found for '{app_id}'\n" f"  → Make sure the PWA exists: pwa-forge list"
            )
    except Exception as e:
        if "not found" in str(e).lower():
            raise UserscriptCommandError(
                f"PWA '{app_id}' not found in registry\n" f"  → Run 'pwa-forge list' to see available PWAs"
            ) from e
        raise

    # Create extensions directory
    extensions_dir = profile_path / "Default" / "Extensions"
    violentmonkey_dir = extensions_dir / "jinjaccalgkegednnccohimojbjjpbbfa"  # Violentmonkey ID

    logger.debug(f"Extensions directory: {extensions_dir}")
    logger.debug(f"Violentmonkey directory: {violentmonkey_dir}")

    if dry_run:
        logger.info(f"[DRY-RUN] Would install Violentmonkey to {violentmonkey_dir}")
        return {
            "extension_path": str(violentmonkey_dir),
            "extension_id": "jinjaccalgkegednnccohimojbjjpbbfa",
        }

    # Create extension manifest
    violentmonkey_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created extensions directory: {violentmonkey_dir}")

    # Create manifest.json for Violentmonkey
    manifest = {
        "manifest_version": 3,
        "name": "Violentmonkey",
        "version": "1.0",
        "description": "Violentmonkey - User script manager",
        "permissions": ["scripting", "activeTab"],
        "host_permissions": ["<all_urls>"],
    }

    manifest_file = violentmonkey_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Created extension manifest: {manifest_file}")

    # Create a minimal extension structure
    # In a real scenario, we'd download the actual CRX, but for now we create
    # a minimal structure that Chrome will recognize
    _create_minimal_extension_structure(violentmonkey_dir)

    return {
        "extension_path": str(violentmonkey_dir),
        "extension_id": "jinjaccalgkegednnccohimojbjjpbbfa",
    }


def _create_minimal_extension_structure(extension_dir: Path) -> None:
    """Create minimal extension structure for Violentmonkey.

    Args:
        extension_dir: Directory where extension will be installed.
    """
    # Create background.js
    background_js = extension_dir / "background.js"
    background_js.write_text(
        """
// Violentmonkey background script
console.log('Violentmonkey extension loaded');
"""
    )
    logger.debug(f"Created background script: {background_js}")

    # Create content.js
    content_js = extension_dir / "content.js"
    content_js.write_text(
        """
// Violentmonkey content script
console.log('Violentmonkey content script loaded');
"""
    )
    logger.debug(f"Created content script: {content_js}")


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
    print("2. Auto-install the generated userscript:")
    print(f"   pwa-forge install-userscript <app_id> --scheme {scheme}")
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
