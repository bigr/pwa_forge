"""Command-line entry points for PWA Forge."""

from __future__ import annotations

import importlib.metadata
import logging

import click

from pwa_forge.commands.add import AddCommandError, add_app
from pwa_forge.commands.audit import AuditCommandError
from pwa_forge.commands.audit import audit_app as audit_app_impl
from pwa_forge.commands.config_cmd import (
    ConfigCommandError,
    config_edit,
    config_get,
    config_list,
    config_reset,
    config_set,
)
from pwa_forge.commands.edit import EditCommandError
from pwa_forge.commands.edit import edit_app as edit_app_impl
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
from pwa_forge.commands.sync import SyncCommandError
from pwa_forge.commands.sync import sync_app as sync_app_impl
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

    Checks performed:
    - Manifest file exists and is valid YAML
    - Desktop file exists and has required fields
    - Wrapper script exists and is executable
    - Profile directory exists
    - Browser executable is available
    - Icon file exists (if specified)
    - Handler is registered (if userscript configured)

    Example:
        pwa-forge audit chatgpt
        pwa-forge audit --fix
    """
    config = ctx.obj["config"]

    try:
        result = audit_app_impl(
            app_id=id,
            config=config,
            fix=fix,
            open_test_page=open_test_page,
        )

        # Display results
        no_color = ctx.obj.get("no_color", False)

        if result["audited_apps"] == 0:
            click.echo("No PWAs to audit.")
            return

        click.echo(f"\nAudited {result['audited_apps']} PWA(s)\n")

        for app_result in result["results"]:
            app_id_str = app_result["id"]
            if not no_color:
                click.secho(f"━━━ {app_id_str} ━━━", fg="blue", bold=True)
            else:
                click.echo(f"━━━ {app_id_str} ━━━")

            for check in app_result["checks"]:
                status = check["status"]
                name = check["name"]
                message = check["message"]

                if status == "PASS":
                    symbol = "✓"
                    color = "green"
                elif status == "FAIL":
                    symbol = "✗"
                    color = "red"
                elif status == "FIXED":
                    symbol = "✓"
                    color = "green"
                elif status == "WARNING":
                    symbol = "⚠"
                    color = "yellow"
                else:
                    symbol = "•"
                    color = None

                if not no_color and color:
                    click.secho(f"  {symbol} {name}: {message}", fg=color)
                else:
                    click.echo(f"  {symbol} {name}: {message}")

            # Summary for this app
            passed = app_result["passed"]
            failed = app_result["failed"]
            total = len(app_result["checks"])

            click.echo(f"  → {passed}/{total} checks passed")
            if failed > 0:
                if not no_color:
                    click.secho(f"  → {failed} issues found", fg="red")
                else:
                    click.echo(f"  → {failed} issues found")

            click.echo()

        # Overall summary
        if not no_color:
            click.secho("━━━ Summary ━━━", fg="blue", bold=True)
        else:
            click.echo("━━━ Summary ━━━")

        click.echo(f"  Total: {result['audited_apps']} PWAs")
        if result["passed"] > 0:
            if not no_color:
                click.secho(f"  Passed: {result['passed']}", fg="green")
            else:
                click.echo(f"  Passed: {result['passed']}")

        if result["failed"] > 0:
            if not no_color:
                click.secho(f"  Failed: {result['failed']}", fg="red")
            else:
                click.echo(f"  Failed: {result['failed']}")

        if result["fixed"] > 0:
            if not no_color:
                click.secho(f"  Fixed: {result['fixed']}", fg="green")
            else:
                click.echo(f"  Fixed: {result['fixed']}")

        # Exit code
        if result["failed"] > 0 and not fix:
            if not no_color:
                click.secho("\nRun with --fix to attempt repairs.", fg="yellow")
            else:
                click.echo("\nRun with --fix to attempt repairs.")
            ctx.exit(1)

    except AuditCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("id")
@click.option("--no-sync", is_flag=True, help="Skip automatic sync after editing")
@click.pass_context
def edit(ctx: click.Context, id: str, no_sync: bool) -> None:  # noqa: A002
    """Open the manifest file in $EDITOR for manual editing.

    After editing, the manifest is validated for correct YAML syntax and
    required fields. If validation passes and --no-sync is not specified,
    the wrapper and desktop files are automatically regenerated.

    If validation fails, the original manifest is restored from backup.

    ID is the application identifier or name.

    Example:
        pwa-forge edit chatgpt
        pwa-forge edit chatgpt --no-sync
    """
    config = ctx.obj["config"]

    try:
        result = edit_app_impl(
            app_id=id,
            config=config,
            auto_sync=not no_sync,
        )

        no_color = ctx.obj.get("no_color", False)

        if result["validation_errors"]:
            # Validation failed
            if not no_color:
                click.secho(f"✗ Validation failed for: {result['id']}", fg="red", err=True)
            else:
                click.echo(f"✗ Validation failed for: {result['id']}", err=True)

            for error in result["validation_errors"]:
                if not no_color:
                    click.secho(f"  • {error}", fg="red", err=True)
                else:
                    click.echo(f"  • {error}", err=True)

            click.echo("\nManifest has been restored from backup.", err=True)
            ctx.exit(1)
        else:
            # Success
            if not no_color:
                click.secho(f"✓ Manifest edited successfully: {result['id']}", fg="green")
            else:
                click.echo(f"✓ Manifest edited successfully: {result['id']}")

            if result["synced"]:
                click.echo("  Artifacts regenerated (wrapper, desktop file)")
            elif not no_sync:
                if not no_color:
                    click.secho("  ⚠ Sync skipped (sync failed)", fg="yellow")
                else:
                    click.echo("  ⚠ Sync skipped (sync failed)")
            else:
                click.echo("  Sync skipped (--no-sync)")
                if not no_color:
                    click.secho(f"  Run 'pwa-forge sync {id}' to regenerate artifacts", fg="blue")
                else:
                    click.echo(f"  Run 'pwa-forge sync {id}' to regenerate artifacts")

    except EditCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("id")
@click.option("--dry-run", is_flag=True, help="Show what would be regenerated")
@click.pass_context
def sync(ctx: click.Context, id: str, dry_run: bool) -> None:  # noqa: A002
    """Regenerate all artifacts from the manifest file.

    ID is the application identifier or name.

    Use this command after manually editing the manifest to regenerate
    wrapper scripts and desktop files.

    Example:
        pwa-forge sync chatgpt
    """
    config = ctx.obj["config"]

    try:
        result = sync_app_impl(
            app_id=id,
            config=config,
            dry_run=dry_run,
        )

        if not ctx.obj.get("no_color"):
            click.secho(f"✓ Synced successfully: {result['id']}", fg="green")
        else:
            click.echo(f"✓ Synced successfully: {result['id']}")

        if result["regenerated"]:
            click.echo(f"  Regenerated: {', '.join(result['regenerated'])}")

        for warning in result["warnings"]:
            if not ctx.obj.get("no_color"):
                click.secho(f"  ⚠ {warning}", fg="yellow")
            else:
                click.echo(f"  ⚠ {warning}")

        if dry_run:
            click.echo("\n[DRY-RUN] No changes were made.")

    except SyncCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


# Configuration Management
@cli.group()
def config() -> None:
    """Manage global configuration.

    Examples:
        pwa-forge config list
        pwa-forge config get default_browser
        pwa-forge config set default_browser firefox
        pwa-forge config reset
    """


@config.command(name="get")
@click.argument("key")
@click.pass_context
def config_get_cmd(ctx: click.Context, key: str) -> None:
    """Display configuration value for KEY.

    KEY can use dot notation to access nested values (e.g., browsers.chrome).

    Examples:
        pwa-forge config get default_browser
        pwa-forge config get browsers.chrome
        pwa-forge config get chrome_flags.enable
    """
    cfg = ctx.obj["config"]

    try:
        value = config_get(key, cfg)
        click.echo(value)
    except ConfigCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set_cmd(ctx: click.Context, key: str, value: str) -> None:
    """Set configuration KEY to VALUE.

    KEY can use dot notation to access nested values.
    VALUE will be parsed to the correct type (string, number, boolean, list).

    Examples:
        pwa-forge config set default_browser firefox
        pwa-forge config set browsers.chrome /usr/bin/google-chrome
        pwa-forge config set log_level debug
        pwa-forge config set chrome_flags.enable "[WebUIDarkMode,WebUIEnableLazyLoading]"
    """
    cfg = ctx.obj["config"]

    try:
        config_set(key, value, cfg)

        if not ctx.obj.get("no_color"):
            click.secho(f"✓ Configuration updated: {key} = {value}", fg="green")
        else:
            click.echo(f"✓ Configuration updated: {key} = {value}")
    except ConfigCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@config.command(name="list")
@click.pass_context
def config_list_cmd(ctx: click.Context) -> None:
    """Show all configuration values.

    Displays the current configuration in YAML format.

    Example:
        pwa-forge config list
    """
    cfg = ctx.obj["config"]

    try:
        import yaml

        config_data = config_list(cfg)
        output = yaml.safe_dump(config_data, default_flow_style=False, sort_keys=False)

        if not ctx.obj.get("no_color"):
            click.secho("Current configuration:", fg="blue", bold=True)
        else:
            click.echo("Current configuration:")

        click.echo(output)
    except ConfigCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@config.command(name="reset")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def config_reset_cmd(ctx: click.Context, yes: bool) -> None:
    """Reset configuration to defaults.

    This will delete the user configuration file and revert to default settings.

    Example:
        pwa-forge config reset
        pwa-forge config reset --yes
    """
    cfg = ctx.obj["config"]

    if not yes and not click.confirm("Are you sure you want to reset configuration to defaults?"):
        click.echo("Cancelled.")
        ctx.exit(0)

    try:
        config_reset(cfg)

        if not ctx.obj.get("no_color"):
            click.secho("✓ Configuration reset to defaults", fg="green")
        else:
            click.echo("✓ Configuration reset to defaults")
    except ConfigCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


@config.command(name="edit")
@click.pass_context
def config_edit_cmd(ctx: click.Context) -> None:
    """Open configuration file in $EDITOR.

    Opens the user configuration file in your preferred text editor.
    If the file doesn't exist, it will be created with default values.

    The file is validated after editing. If validation fails, the original
    file is restored from backup.

    Example:
        pwa-forge config edit
    """
    cfg = ctx.obj["config"]

    try:
        config_edit(cfg)

        if not ctx.obj.get("no_color"):
            click.secho("✓ Configuration file edited successfully", fg="green")
        else:
            click.echo("✓ Configuration file edited successfully")
    except ConfigCommandError as e:
        if not ctx.obj.get("no_color"):
            click.secho(f"✗ Error: {e}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)


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
            click.echo(f"\nNext step: Install the handler with:\n  pwa-forge install-handler --scheme {scheme}")

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
