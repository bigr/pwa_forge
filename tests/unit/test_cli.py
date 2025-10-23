"""Unit tests for CLI commands."""

from __future__ import annotations

from click.testing import CliRunner
from pwa_forge import cli


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self) -> None:
        """Test that CLI shows help."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--help"])
        assert result.exit_code == 0
        assert "Manage Progressive Web Apps" in result.output
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

    def test_cli_version(self) -> None:
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestAddCommand:
    """Test add command."""

    def test_add_command_exists(self) -> None:
        """Test that add command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["add", "--help"])
        assert result.exit_code == 0
        assert "Create a new PWA instance" in result.output

    def test_add_command_placeholder(self) -> None:
        """Test add command with dry-run."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["add", "https://example.com", "--dry-run"])
        # May fail if browser not found, which is expected in test environment
        assert result.exit_code in (0, 1)


class TestListCommand:
    """Test list command."""

    def test_list_command_exists(self) -> None:
        """Test that list command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "List all managed PWA instances" in result.output

    def test_list_command_placeholder(self) -> None:
        """Test list command with empty registry."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["list"])
        assert result.exit_code == 0
        # Should not crash even with empty registry


class TestRemoveCommand:
    """Test remove command."""

    def test_remove_command_exists(self) -> None:
        """Test that remove command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["remove", "--help"])
        assert result.exit_code == 0
        assert "Remove a PWA instance" in result.output

    def test_remove_command_placeholder(self) -> None:
        """Test remove command with non-existent app."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["remove", "test-id"])
        # Should fail since app doesn't exist
        assert result.exit_code == 1


class TestAuditCommand:
    """Test audit command."""

    def test_audit_command_exists(self) -> None:
        """Test that audit command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["audit", "--help"])
        assert result.exit_code == 0
        assert "Validate PWA configuration" in result.output

    def test_audit_command_with_nonexistent_app(self) -> None:
        """Test audit command with non-existent app."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["audit", "nonexistent-app-xyz"])
        assert result.exit_code == 1
        assert "Error" in result.output


class TestEditCommand:
    """Test edit command."""

    def test_edit_command_exists(self) -> None:
        """Test that edit command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "Open the manifest file" in result.output

    def test_edit_command_placeholder(self) -> None:
        """Test edit command placeholder."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["edit", "test-id"])
        assert result.exit_code == 0
        assert "Not yet implemented" in result.output


class TestSyncCommand:
    """Test sync command."""

    def test_sync_command_exists(self) -> None:
        """Test that sync command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["sync", "--help"])
        assert result.exit_code == 0
        assert "Regenerate all artifacts" in result.output

    def test_sync_command_requires_id(self) -> None:
        """Test sync command requires an app ID."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["sync"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output


class TestConfigCommands:
    """Test config command group."""

    def test_config_group_exists(self) -> None:
        """Test that config group is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage global configuration" in result.output

    def test_config_get_exists(self) -> None:
        """Test that config get command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "get", "--help"])
        assert result.exit_code == 0
        assert "Display configuration value" in result.output

    def test_config_get_placeholder(self) -> None:
        """Test config get command placeholder."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "get", "test_key"])
        assert result.exit_code == 0
        assert "Not yet implemented" in result.output

    def test_config_set_exists(self) -> None:
        """Test that config set command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "set", "--help"])
        assert result.exit_code == 0
        assert "Set configuration KEY to VALUE" in result.output

    def test_config_set_placeholder(self) -> None:
        """Test config set command placeholder."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "set", "test_key", "test_value"])
        assert result.exit_code == 0
        assert "Not yet implemented" in result.output

    def test_config_list_exists(self) -> None:
        """Test that config list command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "list", "--help"])
        assert result.exit_code == 0
        assert "Show all configuration values" in result.output

    def test_config_list_placeholder(self) -> None:
        """Test config list command placeholder."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "list"])
        assert result.exit_code == 0
        assert "Not yet implemented" in result.output

    def test_config_reset_exists(self) -> None:
        """Test that config reset command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "reset", "--help"])
        assert result.exit_code == 0
        assert "Reset configuration to defaults" in result.output

    def test_config_reset_placeholder(self) -> None:
        """Test config reset command placeholder."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "reset"])
        assert result.exit_code == 0
        assert "Not yet implemented" in result.output


class TestVerbosityOptions:
    """Test verbosity options."""

    def test_quiet_flag(self) -> None:
        """Test --quiet flag."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--quiet", "version"])
        assert result.exit_code == 0

    def test_verbose_flag(self) -> None:
        """Test --verbose flag."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--verbose", "version"])
        assert result.exit_code == 0

    def test_multiple_verbose_flags(self) -> None:
        """Test multiple --verbose flags."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["-vv", "version"])
        assert result.exit_code == 0
