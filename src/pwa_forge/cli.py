"""Command-line entry points for PWA Forge."""

from __future__ import annotations

import importlib.metadata
import logging

import click

from pwa_forge.commands.add import AddCommandError, add_app
from pwa_forge.commands.handler import (
    HandlerCommandError,
)
from pwa_forge.commands.handler import (
    generate_handler as generate_handler_impl,
)
from pwa_forge.commands.handler import (
    install_handler as install_handler_impl,
)
from pwa_forge.commands.list_apps import list_apps as list_apps_impl
from pwa_forge.commands.remove import RemoveCommandError
from pwa_forge.commands.remove import remove_app as remove_app_impl
from pwa_forge.commands.userscript import (
    UserscriptCommandError,
)
from pwa_forge.commands.userscript import (
    generate_userscript as generate_userscript_impl,
)
from pwa_forge.config import load_config
from pwa_forge.utils.logger import setup_logging


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (can be used multiple times: -v for INFO, -vv for DEBUG)",
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress console output except errors")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.pass_context
def cli(ctx: click.Context, verbose: int, quiet: bool, no_color: bool) -> None:
    """Manage Progressive Web Apps as native-feeling Linux launchers.

    pwa-forge automates the creation of isolated browser instances with custom
    launchers, handles external link redirection to system browsers, and provides
    comprehensive PWA lifecycle management.

    Examples:
        pwa-forge add https://chat.openai.com --name ChatGPT
        pwa-forge list
        pwa-forge remove chatgpt
    """
    # Load configuration
    config = load_config()

    # Setup logging based on verbosity
    if quiet:
        log_level = logging.ERROR
    elif verbose >= 2:
        log_level = logging.DEBUG
    elif verbose == 1:
        log_level = logging.INFO
    else:
        # Map config log level to logging level
        log_level_str = config.log_level.upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

    setup_logging(level=log_level, log_file=config.log_file, console=not quiet)

    # Store config in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["no_color"] = no_color


@cli.command()
def version() -> None:
    """Show the installed package version."""
    package_version = _read_package_version()
    click.echo(package_version)


# PWA Management Commands
@cli.command()
@click.argument("url")
@click.option("--name", help="Display name for the application")
@click.option("--id", "app_id", help="Unique identifier (auto-generated from name)")
@click.option(
    "--browser",
    type=click.Choice(["chrome", "chromium", "firefox", "edge"]),
    default="chrome",
    help="Browser engine to use",
)
@click.option("--profile", type=click.Path(), help="Custom profile directory")
@click.option("--icon", type=click.Path(exists=True), help="Path to application icon")
@click.option(
    "--out-of-scope",
    type=click.Choice(["open-in-default", "same-browser-window", "same-browser-new-window"]),
    default="open-in-default",
    help="Behavior for external links",
)
@click.option("--inject-userscript", type=click.Path(exists=True), help="Path to custom userscript")
@click.option("--wm-class", help="Custom StartupWMClass for window manager")
@click.option("--chrome-flags", help="Additional Chrome/Chromium flags")
@click.option("--dry-run", is_flag=True, help="Show what would be created without making changes")
@click.pass_context
def add(
    ctx: click.Context,
    url: str,
    name: str | None,
    app_id: str | None,
    browser: str,
    profile: str | None,
    icon: str | None,
    out_of_scope: str,
    inject_userscript: str | None,
    wm_class: str | None,
    chrome_flags: str | None,
    dry_run: bool,
) -> None:
    """Create a new PWA instance.

    URL is the web application address to create a PWA for.

    Example:
        pwa-forge add https://chat.openai.com --name ChatGPT
    """
    config = ctx.obj["config"]

    try:
        result = add_app(
            url=url,
            config=config,
            name=name,
            app_id=app_id,
            browser=browser,
            profile=profile,
            icon=icon,
            out_of_scope=out_of_scope,
            inject_userscript=inject_userscript,
            wm_class=wm_class,
            chrome_flags=chrome_flags,
            dry_run=dry_run,
        )

        if not ctx.obj.get("no_color"):
            click.secho("✓ PWA created successfully!", fg="green")
        else:
            click.echo("✓ PWA created successfully!")

        click.echo(f"  ID: {result['id']}")
        click.echo(f"  Name: {result['name']}")
        click.echo(f"  URL: {result['url']}")

        if dry_run:
            click.echo("\n[DRY-RUN] No changes were made.")

    except AddCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@cli.command(name="list")
@click.option("--verbose", is_flag=True, help="Show detailed information")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.pass_context
def list_apps(ctx: click.Context, verbose: bool, format: str) -> None:  # noqa: A002
    """List all managed PWA instances."""
    config = ctx.obj["config"]
    list_apps_impl(config, verbose=verbose, output_format=format)


@cli.command()
@click.argument("id")
@click.option("--remove-profile", is_flag=True, help="Also delete the browser profile directory")
@click.option("--remove-icon", is_flag=True, help="Also delete the icon file")
@click.option("--keep-userdata", is_flag=True, help="Keep browser profile but remove launcher")
@click.option("--dry-run", is_flag=True, help="Show what would be removed")
@click.pass_context
def remove(
    ctx: click.Context,
    id: str,  # noqa: A002
    remove_profile: bool,
    remove_icon: bool,
    keep_userdata: bool,
    dry_run: bool,
) -> None:
    """Remove a PWA instance.

    ID is the application identifier or name.

    Example:
        pwa-forge remove chatgpt
    """
    config = ctx.obj["config"]

    try:
        remove_app_impl(
            app_id=id,
            config=config,
            remove_profile=remove_profile,
            remove_icon=remove_icon,
            keep_userdata=keep_userdata,
            dry_run=dry_run,
        )

        if not ctx.obj.get("no_color"):
            click.secho(f"✓ PWA removed successfully: {id}", fg="green")
        else:
            click.echo(f"✓ PWA removed successfully: {id}")

        if dry_run:
            click.echo("\n[DRY-RUN] No changes were made.")

    except RemoveCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("id", required=False)
@click.option("--open-test-page", is_flag=True, help="Launch PWA with test page")
@click.option("--fix", is_flag=True, help="Attempt to repair broken configurations")
@click.pass_context
def audit(ctx: click.Context, id: str | None, open_test_page: bool, fix: bool) -> None:  # noqa: A002
    """Validate PWA configuration and functionality.

    If ID is omitted, audits all managed PWAs.
    """
    click.echo("Audit command - Not yet implemented")


@cli.command()
@click.argument("id")
@click.pass_context
def edit(ctx: click.Context, id: str) -> None:  # noqa: A002
    """Open the manifest file in $EDITOR for manual editing.

    ID is the application identifier or name.
    """
    click.echo("Edit command - Not yet implemented")


@cli.command()
@click.argument("id")
@click.pass_context
def sync(ctx: click.Context, id: str) -> None:  # noqa: A002
    """Regenerate all artifacts from the manifest file.

    ID is the application identifier or name.
    """
    click.echo("Sync command - Not yet implemented")


# Configuration Management
@cli.group()
def config() -> None:
    """Manage global configuration."""


@config.command(name="get")
@click.argument("key")
def config_get(key: str) -> None:
    """Display configuration value for KEY."""
    click.echo("Config get command - Not yet implemented")


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set configuration KEY to VALUE."""
    click.echo("Config set command - Not yet implemented")


@config.command(name="list")
def config_list() -> None:
    """Show all configuration values."""
    click.echo("Config list command - Not yet implemented")


@config.command(name="reset")
def config_reset() -> None:
    """Reset configuration to defaults."""
    click.echo("Config reset command - Not yet implemented")


# URL Handler System Commands
@cli.command()
@click.option("--scheme", required=True, help="URL scheme to handle (e.g., 'ff' for ff:// URLs)")
@click.option(
    "--browser",
    type=click.Choice(["firefox", "chrome", "chromium", "edge"]),
    default="firefox",
    help="Browser to open URLs in",
)
@click.option("--out", type=click.Path(), help="Output path for handler script")
@click.option("--dry-run", is_flag=True, help="Show what would be created")
@click.pass_context
def generate_handler(
    ctx: click.Context,
    scheme: str,
    browser: str,
    out: str | None,
    dry_run: bool,
) -> None:
    """Generate a URL scheme handler script.

    The handler script decodes URLs from custom schemes (e.g., ff://) and opens
    them in the specified browser.

    Example:
        pwa-forge generate-handler --scheme ff --browser firefox
    """
    config = ctx.obj["config"]

    try:
        result = generate_handler_impl(
            scheme=scheme,
            config=config,
            browser=browser,
            out=out,
            dry_run=dry_run,
        )

        if not ctx.obj.get("no_color"):
            click.secho("✓ Handler script generated successfully!", fg="green")
        else:
            click.echo("✓ Handler script generated successfully!")

        click.echo(f"  Scheme: {result['scheme']}://")
        click.echo(f"  Browser: {result['browser']}")
        click.echo(f"  Script: {result['script_path']}")

        if not dry_run:
            click.echo(f"\nNext step: Install the handler with:\n" f"  pwa-forge install-handler --scheme {scheme}")

        if dry_run:
            click.echo("\n[DRY-RUN] No changes were made.")

    except HandlerCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--scheme", required=True, help="URL scheme to register")
@click.option("--handler-script", type=click.Path(), help="Path to handler script (auto-detected if omitted)")
@click.option("--dry-run", is_flag=True, help="Show what would be created")
@click.pass_context
def install_handler(
    ctx: click.Context,
    scheme: str,
    handler_script: str | None,
    dry_run: bool,
) -> None:
    """Register a URL scheme handler with the system.

    Creates a .desktop file, registers the MIME type handler with XDG, and adds
    the handler to the registry.

    Example:
        pwa-forge install-handler --scheme ff
    """
    config = ctx.obj["config"]

    try:
        result = install_handler_impl(
            scheme=scheme,
            config=config,
            handler_script=handler_script,
            dry_run=dry_run,
        )

        if not ctx.obj.get("no_color"):
            click.secho("✓ Handler installed successfully!", fg="green")
        else:
            click.echo("✓ Handler installed successfully!")

        click.echo(f"  Scheme: {result['scheme']}://")
        click.echo(f"  MIME type: {result['mime_type']}")
        click.echo(f"  Desktop file: {result['desktop_file']}")

        if not dry_run:
            click.echo(f"\nHandler is now registered. Links using {scheme}:// will open in your browser.")

        if dry_run:
            click.echo("\n[DRY-RUN] No changes were made.")

    except HandlerCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--scheme", help="URL scheme to redirect to (default: from config)")
@click.option("--in-scope-hosts", help="Comma-separated list of hosts to keep in-app")
@click.option("--url-pattern", default="*://*/*", help="URL pattern to match")
@click.option("--out", type=click.Path(), help="Output path for userscript")
@click.option("--dry-run", is_flag=True, help="Show what would be created")
@click.pass_context
def generate_userscript(
    ctx: click.Context,
    scheme: str | None,
    in_scope_hosts: str | None,
    url_pattern: str,
    out: str | None,
    dry_run: bool,
) -> None:
    """Generate a userscript for external link interception.

    The userscript intercepts external links in a PWA and redirects them to a
    custom URL scheme, which is then handled by a registered handler.

    Example:
        pwa-forge generate-userscript --scheme ff --in-scope-hosts "example.com,api.example.com"
    """
    config = ctx.obj["config"]

    try:
        result = generate_userscript_impl(
            config=config,
            scheme=scheme,
            in_scope_hosts=in_scope_hosts,
            url_pattern=url_pattern,
            out=out,
            dry_run=dry_run,
        )

        if not ctx.obj.get("no_color"):
            click.secho("✓ Userscript generated successfully!", fg="green")
        else:
            click.echo("✓ Userscript generated successfully!")

        click.echo(f"  Scheme: {result['scheme']}://")
        click.echo(f"  In-scope hosts: {', '.join(result['in_scope_hosts']) if result['in_scope_hosts'] else 'none'}")
        click.echo(f"  Userscript: {result['userscript_path']}")

        if dry_run:
            click.echo("\n[DRY-RUN] No changes were made.")

    except UserscriptCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


def _read_package_version() -> str:
    """Return the installed package version, falling back to static metadata."""
    try:
        return importlib.metadata.version("pwa-forge")
    except importlib.metadata.PackageNotFoundError:
        from pwa_forge import __version__

        return __version__


def main(argv: list[str] | None = None) -> None:
    """Execute the CLI entry point."""
    cli.main(args=argv, prog_name="pwa-forge", standalone_mode=False)  # type: ignore[attr-defined,unused-ignore]


if __name__ == "__main__":  # pragma: no cover - convenience entry point
    main()
