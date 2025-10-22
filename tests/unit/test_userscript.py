"""Unit tests for userscript command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from pwa_forge.commands.userscript import generate_userscript
from pwa_forge.config import Config


class TestGenerateUserscript:
    """Test generate_userscript function."""

    def test_generate_userscript_basic(self, tmp_path: Path) -> None:
        """Test basic userscript generation."""
        config = Config()
        output_path = tmp_path / "test.user.js"

        result = generate_userscript(
            config=config,
            scheme="testscheme",
            in_scope_hosts="example.com,api.example.com",
            url_pattern="*://*/*",
            out=str(output_path),
            dry_run=False,
        )

        assert result["scheme"] == "testscheme"
        assert result["in_scope_hosts"] == ["example.com", "api.example.com"]
        assert output_path.exists()

        # Verify content
        content = output_path.read_text()
        assert "testscheme" in content
        assert "example.com" in content
        assert "api.example.com" in content
        assert "// ==UserScript==" in content

    def test_generate_userscript_dry_run(self, tmp_path: Path) -> None:
        """Test userscript generation in dry-run mode."""
        config = Config()
        output_path = tmp_path / "test.user.js"

        result = generate_userscript(
            config=config,
            scheme="testscheme",
            in_scope_hosts=None,
            out=str(output_path),
            dry_run=True,
        )

        assert result["scheme"] == "testscheme"
        assert result["in_scope_hosts"] == []
        assert not output_path.exists()  # File not created in dry-run

    def test_generate_userscript_default_scheme(self, tmp_path: Path) -> None:
        """Test userscript generation with default scheme from config."""
        config = Config()
        config.external_link_scheme = "customscheme"
        output_path = tmp_path / "test.user.js"

        result = generate_userscript(
            config=config,
            scheme=None,  # Use default from config
            in_scope_hosts=None,
            out=str(output_path),
            dry_run=False,
        )

        assert result["scheme"] == "customscheme"
        content = output_path.read_text()
        assert "customscheme" in content

    def test_generate_userscript_default_output_path(self, tmp_path: Path) -> None:
        """Test userscript generation with default output path."""
        config = Config()
        config.directories.userscripts = tmp_path / "userscripts"

        result = generate_userscript(
            config=config,
            scheme="ff",
            in_scope_hosts=None,
            out=None,  # Use default
            dry_run=False,
        )

        expected_path = tmp_path / "userscripts" / "external-links.user.js"
        assert result["userscript_path"] == str(expected_path)
        assert expected_path.exists()

    def test_generate_userscript_empty_in_scope_hosts(self, tmp_path: Path) -> None:
        """Test userscript generation with empty in-scope hosts."""
        config = Config()
        output_path = tmp_path / "test.user.js"

        result = generate_userscript(
            config=config,
            scheme="ff",
            in_scope_hosts="",
            out=str(output_path),
            dry_run=False,
        )

        assert result["in_scope_hosts"] == []
        content = output_path.read_text()
        assert "[]" in content  # Empty array in JavaScript

    def test_generate_userscript_whitespace_in_hosts(self, tmp_path: Path) -> None:
        """Test userscript generation with whitespace in host list."""
        config = Config()
        output_path = tmp_path / "test.user.js"

        result = generate_userscript(
            config=config,
            scheme="ff",
            in_scope_hosts="  example.com  ,  api.example.com  ",
            out=str(output_path),
            dry_run=False,
        )

        # Whitespace should be stripped
        assert result["in_scope_hosts"] == ["example.com", "api.example.com"]

    @patch("builtins.print")
    def test_generate_userscript_prints_instructions(
        self,
        mock_print: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that userscript generation prints installation instructions."""
        config = Config()
        output_path = tmp_path / "test.user.js"

        generate_userscript(
            config=config,
            scheme="ff",
            in_scope_hosts=None,
            out=str(output_path),
            dry_run=False,
        )

        # Verify instructions were printed
        assert mock_print.called
        # Collect all printed strings
        printed_text = " ".join(
            str(args[0]) if args else "" for call in mock_print.call_args_list for args in [call[0]]
        )
        assert "Installation Instructions" in printed_text
        assert "Violentmonkey" in printed_text or "Tampermonkey" in printed_text

    @patch("builtins.print")
    def test_generate_userscript_no_instructions_in_dry_run(
        self,
        mock_print: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that dry-run doesn't print installation instructions."""
        config = Config()
        output_path = tmp_path / "test.user.js"

        generate_userscript(
            config=config,
            scheme="ff",
            in_scope_hosts=None,
            out=str(output_path),
            dry_run=True,
        )

        # Instructions should not be printed in dry-run
        if mock_print.called:
            printed_text = " ".join(
                str(args[0]) if args else "" for call in mock_print.call_args_list for args in [call[0]]
            )
            assert "Installation Instructions" not in printed_text
