"""Integration tests for handler workflow (generate, install, userscript)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pwa_forge.commands.handler import generate_handler, install_handler
from pwa_forge.commands.userscript import generate_userscript
from pwa_forge.config import Config
from pwa_forge.registry import Registry


class IsolatedConfig(Config):
    """Configuration with isolated paths for testing."""

    def __init__(self, tmp_path: Path) -> None:
        """Initialize test config with temp paths."""
        super().__init__()
        self._tmp_path = tmp_path
        # Override directories
        self.directories.desktop = tmp_path / "applications"
        self.directories.icons = tmp_path / "icons"
        self.directories.wrappers = tmp_path / "wrappers"
        self.directories.apps = tmp_path / "apps"
        self.directories.userscripts = tmp_path / "userscripts"

        # Create directories
        for directory in [
            self.directories.desktop,
            self.directories.icons,
            self.directories.wrappers,
            self.directories.apps,
            self.directories.userscripts,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        # Create a fake browser executable
        fake_firefox = tmp_path / "bin" / "firefox"
        fake_firefox.parent.mkdir(parents=True, exist_ok=True)
        fake_firefox.touch()
        fake_firefox.chmod(0o755)
        self.browsers.firefox = str(fake_firefox)

    @property
    def registry_file(self) -> Path:
        """Get test registry file path."""
        registry_dir = self._tmp_path / "data"
        registry_dir.mkdir(parents=True, exist_ok=True)
        return registry_dir / "registry.json"


@pytest.fixture
def test_config(tmp_path: Path) -> IsolatedConfig:  # type: ignore[misc]
    """Provide isolated test configuration."""
    return IsolatedConfig(tmp_path)


class TestHandlerGeneration:
    """Test handler script generation workflow."""

    def test_generate_handler_creates_script(self, test_config: IsolatedConfig) -> None:
        """Test that generate_handler creates executable script."""
        output_path = test_config._tmp_path / "handler-ff"

        result = generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(output_path),
            dry_run=False,
        )

        # Verify result
        assert result["scheme"] == "ff"
        assert result["browser"] == "firefox"
        assert result["script_path"] == str(output_path)

        # Verify file created
        assert output_path.exists()
        assert output_path.stat().st_mode & 0o111  # Executable

        # Verify content
        content = output_path.read_text()
        assert "#!/bin/bash" in content
        assert "ff:" in content
        assert str(test_config.browsers.firefox) in content
        assert "python3 -c" in content  # URL decoding
        assert "http://*|https://*" in content  # Security validation

    def test_generate_handler_multiple_schemes(self, test_config: IsolatedConfig) -> None:
        """Test generating handlers for multiple schemes."""
        schemes = ["ff", "external", "custom"]
        output_dir = test_config._tmp_path / "handlers"
        output_dir.mkdir()

        for scheme in schemes:
            output_path = output_dir / f"handler-{scheme}"
            result = generate_handler(
                scheme=scheme,
                config=test_config,
                browser="firefox",
                out=str(output_path),
                dry_run=False,
            )

            assert result["scheme"] == scheme
            assert output_path.exists()
            content = output_path.read_text()
            assert f"{scheme}:" in content


class TestHandlerInstallation:
    """Test handler installation workflow."""

    @patch("subprocess.run")
    def test_install_handler_full_workflow(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test complete handler installation workflow."""
        # Step 1: Generate handler script
        handler_script = test_config._tmp_path / "pwa-forge-handler-ff"
        generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(handler_script),
            dry_run=False,
        )

        assert handler_script.exists()

        # Mock subprocess calls
        mock_run.return_value = MagicMock(returncode=0, stdout=b"pwa-forge-handler-ff.desktop\n")

        # Step 2: Install handler
        install_result = install_handler(
            scheme="ff",
            config=test_config,
            handler_script=str(handler_script),
            dry_run=False,
        )

        # Verify install result
        assert install_result["scheme"] == "ff"
        assert install_result["mime_type"] == "x-scheme-handler/ff"

        # Verify desktop file created
        desktop_file = test_config.directories.desktop / "pwa-forge-handler-ff.desktop"
        assert desktop_file.exists()

        desktop_content = desktop_file.read_text()
        assert "[Desktop Entry]" in desktop_content
        assert "MimeType=x-scheme-handler/ff" in desktop_content
        assert str(handler_script) in desktop_content

        # Verify registry updated
        registry = Registry(test_config.registry_file)
        handlers = registry.list_handlers()
        assert len(handlers) == 1
        assert handlers[0]["scheme"] == "ff"
        assert handlers[0]["script"] == str(handler_script)

        # Verify subprocess calls
        assert mock_run.call_count >= 2  # update-desktop-database + xdg-mime

    @patch("subprocess.run")
    def test_install_multiple_handlers(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test installing multiple handlers."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"handler.desktop\n")

        schemes = ["ff", "external", "custom"]
        for scheme in schemes:
            # Generate handler
            handler_script = test_config._tmp_path / f"pwa-forge-handler-{scheme}"
            generate_handler(
                scheme=scheme,
                config=test_config,
                browser="firefox",
                out=str(handler_script),
                dry_run=False,
            )

            # Install handler
            install_handler(
                scheme=scheme,
                config=test_config,
                handler_script=str(handler_script),
                dry_run=False,
            )

        # Verify all handlers in registry
        registry = Registry(test_config.registry_file)
        handlers = registry.list_handlers()
        assert len(handlers) == 3
        handler_schemes = {h["scheme"] for h in handlers}
        assert handler_schemes == set(schemes)


class TestUserscriptGeneration:
    """Test userscript generation workflow."""

    def test_generate_userscript_creates_file(self, test_config: IsolatedConfig) -> None:
        """Test that generate_userscript creates valid userscript."""
        output_path = test_config.directories.userscripts / "test.user.js"

        result = generate_userscript(
            config=test_config,
            scheme="ff",
            in_scope_hosts="example.com,api.example.com",
            out=str(output_path),
            dry_run=False,
        )

        # Verify result
        assert result["scheme"] == "ff"
        assert result["in_scope_hosts"] == ["example.com", "api.example.com"]
        assert result["userscript_path"] == str(output_path)

        # Verify file created
        assert output_path.exists()

        # Verify content
        content = output_path.read_text()
        assert "// ==UserScript==" in content
        assert "// @name" in content
        assert "PWA Forge" in content
        assert "ff" in content
        assert "example.com" in content
        assert "api.example.com" in content
        assert "isExternal" in content
        assert "window.open" in content


class TestCompleteHandlerWorkflow:
    """Test complete end-to-end handler workflow."""

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_complete_workflow(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        test_config: IsolatedConfig,
    ) -> None:
        """Test complete workflow: generate handler + install + generate userscript."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"pwa-forge-handler-ff.desktop\n")

        # Step 1: Generate handler script
        handler_script = test_config._tmp_path / "pwa-forge-handler-ff"
        generate_result = generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(handler_script),
            dry_run=False,
        )

        assert generate_result["scheme"] == "ff"
        assert handler_script.exists()

        # Step 2: Install handler
        install_result = install_handler(
            scheme="ff",
            config=test_config,
            handler_script=str(handler_script),
            dry_run=False,
        )

        assert install_result["scheme"] == "ff"
        desktop_file = test_config.directories.desktop / "pwa-forge-handler-ff.desktop"
        assert desktop_file.exists()

        # Step 3: Generate userscript
        userscript_path = test_config.directories.userscripts / "external-links.user.js"
        userscript_result = generate_userscript(
            config=test_config,
            scheme="ff",
            in_scope_hosts="example.com",
            out=str(userscript_path),
            dry_run=False,
        )

        assert userscript_result["scheme"] == "ff"
        assert userscript_path.exists()

        # Verify all components work together
        # 1. Handler script decodes URLs
        handler_content = handler_script.read_text()
        assert "urllib.parse" in handler_content

        # 2. Desktop file references handler script
        desktop_content = desktop_file.read_text()
        assert str(handler_script) in desktop_content

        # 3. Userscript uses same scheme
        userscript_content = userscript_path.read_text()
        assert "const SCHEME = 'ff'" in userscript_content

        # 4. Registry tracks the handler
        registry = Registry(test_config.registry_file)
        handlers = registry.list_handlers()
        assert len(handlers) == 1
        assert handlers[0]["scheme"] == "ff"

    @patch("subprocess.run")
    def test_workflow_with_default_paths(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test workflow using default paths."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"handler.desktop\n")

        # Generate handler with default path
        with patch("pathlib.Path.home", return_value=test_config._tmp_path):
            generate_result = generate_handler(
                scheme="ff",
                config=test_config,
                browser="firefox",
                out=None,  # Use default
                dry_run=False,
            )

        expected_handler = test_config._tmp_path / ".local" / "bin" / "pwa-forge-handler-ff"
        assert generate_result["script_path"] == str(expected_handler)
        assert expected_handler.exists()

        # Install handler (auto-detects script)
        with patch("pathlib.Path.home", return_value=test_config._tmp_path):
            install_result = install_handler(
                scheme="ff",
                config=test_config,
                handler_script=None,  # Auto-detect
                dry_run=False,
            )

        assert install_result["scheme"] == "ff"

        # Generate userscript with default path
        userscript_result = generate_userscript(
            config=test_config,
            scheme=None,  # Use config default
            in_scope_hosts=None,
            out=None,  # Use default
            dry_run=False,
        )

        expected_userscript = test_config.directories.userscripts / "external-links.user.js"
        assert userscript_result["userscript_path"] == str(expected_userscript)
        assert expected_userscript.exists()
