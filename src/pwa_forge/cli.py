"""Command-line entry points for PWA Forge."""

from __future__ import annotations

import importlib.metadata

import click


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Manage Progressive Web Apps as native-feeling Linux launchers."""


@cli.command()
def version() -> None:
    """Show the installed package version."""
    package_version = _read_package_version()
    click.echo(package_version)


def _read_package_version() -> str:
    """Return the installed package version, falling back to static metadata."""
    try:
        return importlib.metadata.version("pwa-forge")
    except importlib.metadata.PackageNotFoundError:
        from pwa_forge import __version__

        return __version__


def main(argv: list[str] | None = None) -> None:
    """Execute the CLI entry point."""
    cli.main(args=argv, prog_name="pwa-forge", standalone_mode=False)


if __name__ == "__main__":  # pragma: no cover - convenience entry point
    main()
