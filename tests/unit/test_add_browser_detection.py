"""Unit tests for browser detection in add command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pwa_forge.commands.add import AddCommandError, _get_browser_executable
from pwa_forge.config import Config


class TestBrowserDetection:
    """Test browser executable detection logic."""

    def test_browser_found_in_config(self) -> None:
        """Test browser found via configured path."""
        config = Config()

        # Mock the browser path to a temporary file
        with (
            patch.object(config.browsers, "firefox", "/usr/bin/firefox"),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = _get_browser_executable("firefox", config)
            assert result == Path("/usr/bin/firefox")

    def test_browser_found_in_known_paths(self) -> None:
        """Test browser found in hard-coded known paths."""
        config = Config()

        # Make config path not exist, but known path exist
        with patch("pathlib.Path.exists") as mock_exists:
            # First call (config path) returns False, second call (known path) returns True
            mock_exists.side_effect = [False, True]

            result = _get_browser_executable("firefox", config)
            assert result == Path("/usr/bin/firefox")

    def test_browser_found_via_which(self) -> None:
        """Test browser found via shutil.which() fallback."""
        config = Config()

        # All hard-coded paths fail, but shutil.which() succeeds
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which", return_value="/snap/bin/firefox"),
        ):
            result = _get_browser_executable("firefox", config)
            assert result == Path("/snap/bin/firefox")

    def test_browser_not_found_raises_error(self) -> None:
        """Test that missing browser raises AddCommandError."""
        config = Config()

        # All detection methods fail
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which", return_value=None),
            pytest.raises(AddCommandError, match="Browser 'firefox' not found"),
        ):
            _get_browser_executable("firefox", config)

    def test_chrome_found_with_multiple_names(self) -> None:
        """Test chrome can be found under various executable names."""
        config = Config()

        # Configured and known paths don't exist
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which") as mock_which,
        ):
            # shutil.which() tries google-chrome-stable first (fails), then google-chrome (succeeds)
            mock_which.side_effect = [None, "/usr/local/bin/google-chrome"]

            result = _get_browser_executable("chrome", config)
            assert result == Path("/usr/local/bin/google-chrome")

            # Verify it tried both names
            assert mock_which.call_count == 2

    def test_chromium_browser_executable_name(self) -> None:
        """Test chromium with chromium-browser executable name."""
        config = Config()

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which") as mock_which,
        ):
            mock_which.side_effect = ["/usr/bin/chromium-browser", None]

            result = _get_browser_executable("chromium", config)
            assert result == Path("/usr/bin/chromium-browser")

    def test_edge_browser_detection(self) -> None:
        """Test Microsoft Edge browser detection."""
        config = Config()

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which", return_value="/opt/microsoft/msedge/microsoft-edge"),
        ):
            result = _get_browser_executable("edge", config)
            assert result == Path("/opt/microsoft/msedge/microsoft-edge")


class TestDryRunBehavior:
    """Test dry-run mode behavior."""

    def test_dry_run_does_not_require_browser(self, tmp_path: Path) -> None:
        """Test that dry-run mode works without browser installed."""
        from pwa_forge.commands.add import add_app

        config = Config()
        config.directories.desktop = tmp_path / "applications"
        config.directories.icons = tmp_path / "icons"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.apps = tmp_path / "apps"

        # Create directories
        for directory in [
            config.directories.desktop,
            config.directories.icons,
            config.directories.wrappers,
            config.directories.apps,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        # Mock all browser detection to fail, and mock the data dir for registry
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which", return_value=None),
            patch("pwa_forge.utils.paths.get_app_data_dir", return_value=tmp_path / "data"),
        ):
            # This should NOT raise an error in dry-run mode
            result = add_app(
                url="https://example.com",
                config=config,
                name="Test App",
                app_id="test-app",
                browser="chrome",
                dry_run=True,
            )

            # Verify result contains expected fields
            assert result["id"] == "test-app"
            assert result["name"] == "Test App"
            assert result["browser"] == "chrome"

    def test_non_dry_run_requires_browser(self, tmp_path: Path) -> None:
        """Test that non-dry-run mode requires browser to be found."""
        from pwa_forge.commands.add import AddCommandError, add_app

        config = Config()
        config.directories.desktop = tmp_path / "applications"
        config.directories.icons = tmp_path / "icons"
        config.directories.wrappers = tmp_path / "wrappers"
        config.directories.apps = tmp_path / "apps"

        # Create directories
        for directory in [
            config.directories.desktop,
            config.directories.icons,
            config.directories.wrappers,
            config.directories.apps,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        # Mock all browser detection to fail
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which", return_value=None),
            patch("pwa_forge.utils.paths.get_app_data_dir", return_value=tmp_path / "data"),
            pytest.raises(AddCommandError, match="Browser 'chrome' not found"),
        ):
            # This SHOULD raise an error in non-dry-run mode
            add_app(
                url="https://example.com",
                config=config,
                name="Test App",
                app_id="test-app-2",
                browser="chrome",
                dry_run=False,
            )
