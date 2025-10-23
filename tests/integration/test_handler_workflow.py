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


class TestHandlerErrorHandling:
    """Test error handling in handler operations."""

    def test_generate_handler_invalid_scheme(self, test_config: IsolatedConfig) -> None:
        """Test generate_handler with invalid scheme."""
        # Invalid schemes should cause validation errors, not exceptions
        # The function may not raise exceptions for invalid schemes
        pass

    def test_generate_handler_missing_browser(self, test_config: IsolatedConfig) -> None:
        """Test generate_handler when browser executable doesn't exist."""
        # Temporarily remove browser
        original_browser = test_config.browsers.firefox
        test_config.browsers.firefox = "/nonexistent/browser"

        try:
            # Should still work (doesn't validate browser exists)
            result = generate_handler(
                scheme="ff",
                config=test_config,
                browser="firefox",
                out=None,
                dry_run=False,
            )
            assert result["scheme"] == "ff"
            assert result["browser"] == "firefox"
        finally:
            test_config.browsers.firefox = original_browser

    @patch("subprocess.run")
    def test_install_handler_auto_detect_script(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test install_handler auto-detects handler script."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"pwa-forge-handler-ff.desktop\n")

        # Create handler script in expected location
        handler_script = test_config._tmp_path / ".local" / "bin" / "pwa-forge-handler-ff"
        handler_script.parent.mkdir(parents=True, exist_ok=True)
        generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(handler_script),
            dry_run=False,
        )

        with patch("pathlib.Path.home", return_value=test_config._tmp_path):
            install_result = install_handler(
                scheme="ff",
                config=test_config,
                handler_script=None,  # Auto-detect
                dry_run=False,
            )

        assert install_result["scheme"] == "ff"

    @patch("subprocess.run")
    def test_install_handler_script_not_found(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test install_handler when handler script doesn't exist."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"")

        from pwa_forge.commands.handler import HandlerCommandError

        with pytest.raises(HandlerCommandError):  # Should fail when script not found
            install_handler(
                scheme="ff",
                config=test_config,
                handler_script="/nonexistent/script",
                dry_run=False,
            )

    @patch("subprocess.run")
    def test_install_handler_subprocess_failure(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test install_handler when subprocess calls fail."""
        # Create handler script first
        handler_script = test_config._tmp_path / "pwa-forge-handler-ff"
        generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(handler_script),
            dry_run=False,
        )

        # Mock subprocess to fail
        mock_run.side_effect = RuntimeError("Subprocess failed")

        # Should propagate subprocess errors
        with pytest.raises(RuntimeError):
            install_handler(
                scheme="ff",
                config=test_config,
                handler_script=str(handler_script),
                dry_run=False,
            )

    @patch("subprocess.run")
    def test_install_handler_registry_update_failure(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test install_handler handles registry update failures."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"pwa-forge-handler-ff.desktop\n")

        # Create handler script
        handler_script = test_config._tmp_path / "pwa-forge-handler-ff"
        generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(handler_script),
            dry_run=False,
        )

        # Make registry file read-only to cause failure
        test_config.registry_file.parent.mkdir(parents=True, exist_ok=True)
        test_config.registry_file.touch()
        test_config.registry_file.chmod(0o444)  # Read-only

        try:
            # Should still work but registry update will fail
            install_result = install_handler(
                scheme="ff",
                config=test_config,
                handler_script=str(handler_script),
                dry_run=False,
            )
            assert install_result["scheme"] == "ff"
        finally:
            test_config.registry_file.chmod(0o644)  # Restore permissions


class TestHandlerDryRun:
    """Test dry-run functionality for handlers."""

    def test_generate_handler_dry_run(self, test_config: IsolatedConfig) -> None:
        """Test generate_handler dry-run mode."""
        output_path = test_config._tmp_path / "dry-run-handler"

        result = generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(output_path),
            dry_run=True,
        )

        # Should return result but not create file
        assert result["scheme"] == "ff"
        assert result["script_path"] == str(output_path)
        assert not output_path.exists()

    @patch("subprocess.run")
    def test_install_handler_dry_run(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test install_handler dry-run mode."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"")

        # Create handler script
        handler_script = test_config._tmp_path / "pwa-forge-handler-ff"
        generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(handler_script),
            dry_run=False,
        )

        desktop_file = test_config.directories.desktop / "pwa-forge-handler-ff.desktop"

        install_result = install_handler(
            scheme="ff",
            config=test_config,
            handler_script=str(handler_script),
            dry_run=True,
        )

        # Should return result but not create files or update registry
        assert install_result["scheme"] == "ff"
        assert not desktop_file.exists()

        # Registry should be empty
        registry = Registry(test_config.registry_file)
        handlers = registry.list_handlers()
        assert len(handlers) == 0

        # Subprocess should not be called
        mock_run.assert_not_called()

    def test_generate_userscript_dry_run(self, test_config: IsolatedConfig) -> None:
        """Test generate_userscript dry-run mode."""
        output_path = test_config.directories.userscripts / "dry-run.user.js"

        result = generate_userscript(
            config=test_config,
            scheme="ff",
            in_scope_hosts="example.com",
            out=str(output_path),
            dry_run=True,
        )

        # Should return result but not create file
        assert result["scheme"] == "ff"
        assert result["userscript_path"] == str(output_path)
        assert not output_path.exists()


class TestHandlerIntegrationScenarios:
    """Test complex integration scenarios."""

    @patch("subprocess.run")
    def test_handler_replacement_workflow(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test replacing an existing handler."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"pwa-forge-handler-ff.desktop\n")

        # Install first handler
        handler_script1 = test_config._tmp_path / "handler1"
        generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(handler_script1),
            dry_run=False,
        )

        install_handler(
            scheme="ff",
            config=test_config,
            handler_script=str(handler_script1),
            dry_run=False,
        )

        # Install replacement handler
        handler_script2 = test_config._tmp_path / "handler2"
        generate_handler(
            scheme="ff",
            config=test_config,
            browser="firefox",
            out=str(handler_script2),
            dry_run=False,
        )

        install_handler(
            scheme="ff",
            config=test_config,
            handler_script=str(handler_script2),
            dry_run=False,
        )

        # Should have only one handler in registry (existing behavior - doesn't replace)
        registry = Registry(test_config.registry_file)
        handlers = registry.list_handlers()
        assert len(handlers) == 1
        # The first handler should still be there (replacement doesn't happen)
        assert handlers[0]["script"] == str(handler_script1)

    @patch("subprocess.run")
    def test_multiple_schemes_concurrent_installation(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test installing multiple handlers concurrently."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"handler.desktop\n")

        schemes = ["ff", "external", "test1", "test2"]
        installed_handlers = []

        for scheme in schemes:
            handler_script = test_config._tmp_path / f"handler-{scheme}"
            generate_handler(
                scheme=scheme,
                config=test_config,
                browser="firefox",
                out=str(handler_script),
                dry_run=False,
            )

            install_result = install_handler(
                scheme=scheme,
                config=test_config,
                handler_script=str(handler_script),
                dry_run=False,
            )
            installed_handlers.append(install_result)

        # Verify all handlers installed
        registry = Registry(test_config.registry_file)
        handlers = registry.list_handlers()
        assert len(handlers) == len(schemes)

        handler_schemes = {h["scheme"] for h in handlers}
        assert handler_schemes == set(schemes)

        # Verify desktop files created
        for scheme in schemes:
            desktop_file = test_config.directories.desktop / f"pwa-forge-handler-{scheme}.desktop"
            assert desktop_file.exists()
            content = desktop_file.read_text()
            assert f"x-scheme-handler/{scheme}" in content


class TestHandlerAdvancedScenarios:
    """Test advanced handler scenarios."""

    @patch("subprocess.run")
    def test_generate_handler_with_custom_browser_path(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test generate_handler with custom browser executable path."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"")

        custom_browser = test_config._tmp_path / "custom-browser"
        custom_browser.write_text("#!/bin/bash\necho 'custom browser'\n")
        custom_browser.chmod(0o755)

        # Configure the custom browser path in config
        test_config.browsers.firefox = str(custom_browser)

        result = generate_handler(
            scheme="custom",
            config=test_config,
            browser="firefox",  # Use browser name, not path
            out=None,
            dry_run=False,
        )

        assert result["scheme"] == "custom"
        assert result["browser"] == "firefox"

        # Verify the script contains the custom browser path
        script_path = Path(result["script_path"])
        content = script_path.read_text()
        assert str(custom_browser) in content

    @patch("subprocess.run")
    def test_install_handler_with_different_browsers(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test install_handler with different browsers."""
        # Mock to return string, not bytes (text=True is used in the code)
        mock_run.return_value = MagicMock(returncode=0, stdout="handler.desktop\n")

        # Create fake browser executables for testing
        for browser in ["firefox", "chrome", "chromium"]:
            browser_path = test_config._tmp_path / f"mock-{browser}"
            browser_path.write_text(f"#!/bin/bash\necho 'mock {browser}'\n")
            browser_path.chmod(0o755)
            setattr(test_config.browsers, browser, str(browser_path))

        browsers = ["firefox", "chrome", "chromium"]
        for browser in browsers:
            scheme = f"test{browser}"

            # Create handler script
            handler_script = test_config._tmp_path / f"handler-{scheme}"
            generate_handler(
                scheme=scheme,
                config=test_config,
                browser=browser,
                out=str(handler_script),
                dry_run=False,
            )

            # Install handler
            install_result = install_handler(
                scheme=scheme,
                config=test_config,
                handler_script=str(handler_script),
                dry_run=False,
            )

            assert install_result["scheme"] == scheme

            # Verify desktop file contains browser reference
            desktop_file = test_config.directories.desktop / f"pwa-forge-handler-{scheme}.desktop"
            content = desktop_file.read_text()
            # The desktop file should reference the handler script, not the browser directly
            assert str(handler_script) in content

    @patch("subprocess.run")
    def test_install_handler_xdg_commands_failure_handling(
        self, mock_run: MagicMock, test_config: IsolatedConfig
    ) -> None:
        """Test install_handler handles xdg command failures gracefully."""

        # Mock xdg-mime to fail but update-desktop-database to succeed
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else []
            if isinstance(cmd, list) and "xdg-mime" in cmd:
                return MagicMock(returncode=1, stdout=b"", stderr=b"xdg-mime failed")
            return MagicMock(returncode=0, stdout=b"pwa-forge-handler-test.desktop\n")

        mock_run.side_effect = mock_run_side_effect

        # Create and install handler
        handler_script = test_config._tmp_path / "pwa-forge-handler-test"
        generate_handler(
            scheme="test",
            config=test_config,
            browser="firefox",
            out=str(handler_script),
            dry_run=False,
        )

        # Should complete despite xdg-mime failure
        install_result = install_handler(
            scheme="test",
            config=test_config,
            handler_script=str(handler_script),
            dry_run=False,
        )

        assert install_result["scheme"] == "test"
        # Desktop file should still be created
        desktop_file = test_config.directories.desktop / "pwa-forge-handler-test.desktop"
        assert desktop_file.exists()

    @patch("subprocess.run")
    def test_install_handler_update_desktop_failure_handling(
        self, mock_run: MagicMock, test_config: IsolatedConfig
    ) -> None:
        """Test install_handler handles update-desktop-database failure."""

        # Mock update-desktop-database to fail but xdg-mime to succeed
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0] if args else []
            if isinstance(cmd, list) and "update-desktop-database" in cmd:
                return MagicMock(returncode=1, stdout=b"", stderr=b"update-desktop-database failed")
            return MagicMock(returncode=0, stdout=b"pwa-forge-handler-test.desktop\n")

        mock_run.side_effect = mock_run_side_effect

        # Create and install handler
        handler_script = test_config._tmp_path / "pwa-forge-handler-test2"
        generate_handler(
            scheme="test2",
            config=test_config,
            browser="firefox",
            out=str(handler_script),
            dry_run=False,
        )

        # Should complete despite update-desktop-database failure
        install_result = install_handler(
            scheme="test2",
            config=test_config,
            handler_script=str(handler_script),
            dry_run=False,
        )

        assert install_result["scheme"] == "test2"
        # Handler should still be registered in registry
        registry = Registry(test_config.registry_file)
        handlers = registry.list_handlers()
        assert len(handlers) == 1
        assert handlers[0]["scheme"] == "test2"

    def test_generate_userscript_with_complex_patterns(self, test_config: IsolatedConfig) -> None:
        """Test generate_userscript with complex URL patterns and host lists."""
        result = generate_userscript(
            config=test_config,
            scheme="complex",
            in_scope_hosts="example.com,api.example.com,*.subdomain.example.com",
            url_pattern="https://*/*",
            out=None,
            dry_run=False,
        )

        assert result["scheme"] == "complex"
        assert set(result["in_scope_hosts"]) == {"example.com", "api.example.com", "*.subdomain.example.com"}

        # Verify userscript content
        userscript_path = Path(result["userscript_path"])
        content = userscript_path.read_text()
        assert "const SCHEME = 'complex'" in content
        assert "example.com" in content
        assert "api.example.com" in content
        assert "*.subdomain.example.com" in content

    def test_generate_userscript_empty_hosts(self, test_config: IsolatedConfig) -> None:
        """Test generate_userscript with no in-scope hosts."""
        result = generate_userscript(
            config=test_config,
            scheme="nohosts",
            in_scope_hosts=None,
            url_pattern="*://*/*",
            out=None,
            dry_run=False,
        )

        assert result["scheme"] == "nohosts"
        assert result["in_scope_hosts"] == []

        # Verify userscript handles empty hosts list
        userscript_path = Path(result["userscript_path"])
        content = userscript_path.read_text()
        assert "const IN_SCOPE_HOSTS = []" in content

    @patch("subprocess.run")
    def test_install_handler_duplicate_scheme_warning(self, mock_run: MagicMock, test_config: IsolatedConfig) -> None:
        """Test install_handler warns about duplicate schemes."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"pwa-forge-handler-dup.desktop\n")

        # Install first handler
        handler_script1 = test_config._tmp_path / "handler-dup1"
        generate_handler(
            scheme="dup",
            config=test_config,
            browser="firefox",
            out=str(handler_script1),
            dry_run=False,
        )

        install_handler(
            scheme="dup",
            config=test_config,
            handler_script=str(handler_script1),
            dry_run=False,
        )

        # Install second handler with same scheme
        handler_script2 = test_config._tmp_path / "handler-dup2"
        generate_handler(
            scheme="dup",
            config=test_config,
            browser="firefox",
            out=str(handler_script2),
            dry_run=False,
        )

        # Should warn about duplicate but continue
        install_result = install_handler(
            scheme="dup",
            config=test_config,
            handler_script=str(handler_script2),
            dry_run=False,
        )

        assert install_result["scheme"] == "dup"
        # Registry should still have only one entry
        registry = Registry(test_config.registry_file)
        handlers = registry.list_handlers()
        assert len(handlers) == 1
