"""Smoke tests for package metadata and CLI wiring."""

from __future__ import annotations

from click.testing import CliRunner

from pwa_forge import __version__
from pwa_forge.cli import cli


def test_version_has_semver_shape() -> None:
    """The package version should follow a basic MAJOR.MINOR.PATCH shape."""
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_cli_version_command_emits_package_version() -> None:
    """Running `pwa-forge version` should show the same version as the package."""
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])  # type: ignore[arg-type]

    assert result.exit_code == 0
    assert result.output.strip() == __version__
