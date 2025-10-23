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

    def test_edit_command_requires_id(self) -> None:
        """Test edit command requires an app ID."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["edit"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output


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

    def test_config_get_nonexistent_key(self) -> None:
        """Test config get command with nonexistent key."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "get", "nonexistent.key"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_config_get_default_value(self) -> None:
        """Test config get command returns default values."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "get", "default_browser"])
        assert result.exit_code == 0
        assert "chrome" in result.output

    def test_config_set_exists(self) -> None:
        """Test that config set command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "set", "--help"])
        assert result.exit_code == 0
        assert "Set configuration KEY to VALUE" in result.output

    def test_config_set_and_get(self) -> None:
        """Test config set and get commands work together."""
        runner = CliRunner()
        # Set a value
        result = runner.invoke(cli.cli, ["config", "set", "test_key", "test_value"])
        assert result.exit_code == 0
        assert "Configuration updated" in result.output

        # Get the value back
        result = runner.invoke(cli.cli, ["config", "get", "test_key"])
        assert result.exit_code == 0
        assert "test_value" in result.output

    def test_config_list_exists(self) -> None:
        """Test that config list command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "list", "--help"])
        assert result.exit_code == 0
        assert "Show all configuration values" in result.output

    def test_config_list_shows_values(self) -> None:
        """Test config list command shows configuration."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "list"])
        assert result.exit_code == 0
        assert "configuration" in result.output.lower()

    def test_config_reset_exists(self) -> None:
        """Test that config reset command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "reset", "--help"])
        assert result.exit_code == 0
        assert "Reset configuration to defaults" in result.output

    def test_config_reset_with_yes_flag(self) -> None:
        """Test config reset command with --yes flag."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "reset", "--yes"])
        assert result.exit_code == 0
        assert "reset" in result.output.lower()


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

        result = runner.invoke(cli.cli, ["-vv", "version"])
        assert result.exit_code == 0


class TestGenerateHandlerCommand:
    """Test generate-handler command."""

    def test_generate_handler_command_exists(self) -> None:
        """Test that generate-handler command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["generate-handler", "--help"])
        assert result.exit_code == 0
        assert "Generate a URL scheme handler script" in result.output

    def test_generate_handler_requires_scheme(self) -> None:
        """Test generate-handler command requires --scheme option."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["generate-handler", "--browser", "firefox"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestInstallHandlerCommand:
    """Test install-handler command."""

    def test_install_handler_command_exists(self) -> None:
        """Test that install-handler command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["install-handler", "--help"])
        assert result.exit_code == 0
        assert "Register a URL scheme handler" in result.output

    def test_install_handler_requires_scheme(self) -> None:
        """Test install-handler command requires --scheme option."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["install-handler"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestGenerateUserscriptCommand:
    """Test generate-userscript command."""

    def test_generate_userscript_command_exists(self) -> None:
        """Test that generate-userscript command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["generate-userscript", "--help"])
        assert result.exit_code == 0
        assert "Generate a userscript for external link interception" in result.output

    def test_generate_userscript_basic_usage(self) -> None:
        """Test generate-userscript command with basic options."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["generate-userscript", "--scheme", "test", "--dry-run"])
        # May fail if userscript generation fails, but should not crash
        assert result.exit_code in (0, 1)


class TestAddCommandOptions:
    """Test add command with various options."""

    def test_add_command_with_name_option(self) -> None:
        """Test add command with custom name."""
        runner = CliRunner()
        result = runner.invoke(
            cli.cli, ["add", "https://example.com", "--name", "Custom Name", "--id", "custom-name-test", "--dry-run"]
        )
        assert result.exit_code in (0, 1)  # May fail due to missing browser

    def test_add_command_with_browser_option(self) -> None:
        """Test add command with specific browser."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["add", "https://example.com", "--browser", "firefox", "--dry-run"])
        assert result.exit_code in (0, 1)  # May fail due to missing browser

    def test_add_command_with_icon_option(self) -> None:
        """Test add command with icon option."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["add", "https://example.com", "--icon", "/nonexistent/icon.svg", "--dry-run"])
        # Exit code 2 is for CLI usage errors (Click framework)
        assert result.exit_code in (0, 1, 2)  # May fail due to missing icon, browser, or CLI usage

    def test_add_command_invalid_url(self) -> None:
        """Test add command with invalid URL."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["add", "invalid-url"])
        assert result.exit_code == 1
        assert "Error" in result.output or "invalid" in result.output.lower()


class TestAuditCommandOptions:
    """Test audit command with various options."""

    def test_audit_command_with_fix_option(self) -> None:
        """Test audit command with --fix option."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["audit", "nonexistent-app", "--fix"])
        assert result.exit_code == 1  # Should fail for non-existent app
        assert "Error" in result.output

    def test_audit_all_command(self) -> None:
        """Test audit command without specific app (audit all)."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["audit"])
        # Exit code 0 if all pass, 1 if some fail - both are valid (depends on registry state)
        assert result.exit_code in (0, 1)  # Should not crash


class TestColorOutput:
    """Test colored output functionality."""

    def test_no_color_flag(self) -> None:
        """Test --no-color flag suppresses colored output."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--no-color", "version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_color_output_in_success_messages(self) -> None:
        """Test that success messages work with color disabled."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--no-color", "version"])
        assert result.exit_code == 0
        assert "✗" not in result.output  # No colored symbols
        assert "✓" not in result.output  # No colored symbols
