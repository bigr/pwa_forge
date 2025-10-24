"""Unit tests for handler command."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pwa_forge.commands.handler import (
    HandlerCommandError,
    _find_browser_executable,
    generate_handler,
    install_handler,
)
from pwa_forge.config import Config


class TestFindBrowserExecutable:
    """Test browser executable finding."""

    def test_find_browser_from_config(self, tmp_path: Path) -> None:
        """Test finding browser executable from config."""
        # Create a fake browser executable
        fake_browser = tmp_path / "fake-firefox"
        fake_browser.touch()

        config = Config()
        config.browsers.firefox = str(fake_browser)

        result = _find_browser_executable("firefox", config)
        assert result == fake_browser

    @patch("shutil.which")
    @patch("pathlib.Path.exists")
    def test_find_browser_not_found(self, mock_exists: MagicMock, mock_which: MagicMock) -> None:
        """Test error when browser not found."""
        config = Config()
        config.browsers.firefox = "/nonexistent/firefox"

        # Mock all paths as non-existent and which returns None
        mock_exists.return_value = False
        mock_which.return_value = None

        with pytest.raises(HandlerCommandError, match="Browser 'firefox' not found"):
            _find_browser_executable("firefox", config)

    @patch("shutil.which")
    @patch("pathlib.Path.exists")
    def test_find_browser_unknown(self, mock_exists: MagicMock, mock_which: MagicMock) -> None:
        """Test error for unknown browser."""
        config = Config()

        # Mock all paths as non-existent and which returns None
        mock_exists.return_value = False
        mock_which.return_value = None

        with pytest.raises(HandlerCommandError, match="Browser 'unknown' not found"):
            _find_browser_executable("unknown", config)

    @patch("shutil.which")
    @patch("pathlib.Path.exists")
    def test_find_browser_via_which(self, mock_exists: MagicMock, mock_which: MagicMock) -> None:
        """Test finding browser via shutil.which() when not in standard locations."""
        config = Config()
        config.browsers.firefox = "/nonexistent/firefox"

        # Mock all paths as non-existent, but which finds it
        mock_exists.return_value = False
        mock_which.return_value = "/snap/bin/firefox"

        result = _find_browser_executable("firefox", config)
        assert result == Path("/snap/bin/firefox")


class TestGenerateHandler:
    """Test generate_handler function."""

    def test_generate_handler_basic(self, tmp_path: Path) -> None:
        """Test basic handler generation."""
        config = Config()
        fake_browser = tmp_path / "fake-firefox"
        fake_browser.touch()
        config.browsers.firefox = str(fake_browser)

        output_path = tmp_path / "handler-script"

        result = generate_handler(
            scheme="testscheme",
            config=config,
            browser="firefox",
            out=str(output_path),
            dry_run=False,
        )

        assert result["scheme"] == "testscheme"
        assert result["browser"] == "firefox"
        assert output_path.exists()
        assert output_path.stat().st_mode & 0o111  # Executable bit set

        # Verify content
        content = output_path.read_text()
        assert "testscheme" in content
        assert str(fake_browser) in content
        assert "#!/bin/bash" in content

    def test_generate_handler_dry_run(self, tmp_path: Path) -> None:
        """Test handler generation in dry-run mode."""
        config = Config()
        fake_browser = tmp_path / "fake-firefox"
        fake_browser.touch()
        config.browsers.firefox = str(fake_browser)

        output_path = tmp_path / "handler-script"

        result = generate_handler(
            scheme="testscheme",
            config=config,
            browser="firefox",
            out=str(output_path),
            dry_run=True,
        )

        assert result["scheme"] == "testscheme"
        assert not output_path.exists()  # File not created in dry-run

    def test_generate_handler_invalid_scheme(self, tmp_path: Path) -> None:
        """Test error for invalid scheme."""
        config = Config()
        fake_browser = tmp_path / "fake-firefox"
        fake_browser.touch()
        config.browsers.firefox = str(fake_browser)

        with pytest.raises(HandlerCommandError, match="Invalid scheme"):
            generate_handler(
                scheme="invalid scheme!",
                config=config,
                browser="firefox",
                dry_run=False,
            )

    def test_generate_handler_default_output_path(self, tmp_path: Path) -> None:
        """Test handler generation with default output path."""
        config = Config()
        fake_browser = tmp_path / "fake-firefox"
        fake_browser.touch()
        config.browsers.firefox = str(fake_browser)

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = generate_handler(
                scheme="ff",
                config=config,
                browser="firefox",
                out=None,
                dry_run=False,
            )

            expected_path = tmp_path / ".local" / "bin" / "pwa-forge-handler-ff"
            assert result["script_path"] == str(expected_path)
            assert expected_path.exists()


class TestInstallHandler:
    """Test install_handler function."""

    def test_install_handler_script_not_found(self, tmp_path: Path) -> None:
        """Test error when handler script not found."""
        config = Config()
        config.directories.desktop = tmp_path / "desktop"

        with pytest.raises(HandlerCommandError, match="Handler script not found"):
            install_handler(
                scheme="ff",
                config=config,
                handler_script=str(tmp_path / "nonexistent"),
                dry_run=False,
            )

    def test_install_handler_dry_run(self, tmp_path: Path) -> None:
        """Test handler installation in dry-run mode."""
        config = Config()
        config.directories.desktop = tmp_path / "desktop"

        # Script doesn't need to exist in dry-run mode
        result = install_handler(
            scheme="testscheme",
            config=config,
            handler_script=str(tmp_path / "handler-script"),
            dry_run=True,
        )

        assert result["scheme"] == "testscheme"
        assert not (tmp_path / "desktop").exists()  # No files created

    @patch("subprocess.run")
    def test_install_handler_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test successful handler installation."""
        config = Config()
        config.directories.desktop = tmp_path / "desktop"
        config.directories.desktop.mkdir(parents=True)

        # Create handler script
        handler_script = tmp_path / "handler-script"
        handler_script.write_text("#!/bin/bash\necho test")

        # Mock subprocess calls
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"pwa-forge-handler-testscheme.desktop\n",
        )

        result = install_handler(
            scheme="testscheme",
            config=config,
            handler_script=str(handler_script),
            dry_run=False,
        )

        assert result["scheme"] == "testscheme"
        assert result["mime_type"] == "x-scheme-handler/testscheme"

        # Check desktop file was created
        desktop_file = tmp_path / "desktop" / "pwa-forge-handler-testscheme.desktop"
        assert desktop_file.exists()
        content = desktop_file.read_text()
        assert "MimeType=x-scheme-handler/testscheme" in content
        assert str(handler_script) in content

        # Verify xdg-mime was called
        assert any("xdg-mime" in str(call) for call in mock_run.call_args_list)

    @patch("subprocess.run")
    def test_install_handler_xdg_mime_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test error when xdg-mime fails."""
        config = Config()
        config.directories.desktop = tmp_path / "desktop"
        config.directories.desktop.mkdir(parents=True)

        # Create handler script
        handler_script = tmp_path / "handler-script"
        handler_script.write_text("#!/bin/bash\necho test")

        # Mock subprocess to fail on xdg-mime
        def side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            if "xdg-mime" in args[0] and "default" in args[0]:
                raise subprocess.CalledProcessError(1, args[0], stderr=b"Error")
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        with pytest.raises(HandlerCommandError, match="Failed to register MIME type"):
            install_handler(
                scheme="testscheme",
                config=config,
                handler_script=str(handler_script),
                dry_run=False,
            )
