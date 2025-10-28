"""Unit tests for userscript command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pwa_forge.commands.userscript import (
    UserscriptCommandError,
    generate_userscript,
    install_userscript,
    setup_userscript,
)
from pwa_forge.config import Config
from pwa_forge.registry import Registry


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


class TestInstallUserscript:
    """Test install_userscript function."""

    def test_install_userscript_basic(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test basic userscript installation."""
        # Setup
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.userscripts = tmp_path / "userscripts"
        registry_file = tmp_path / "registry.json"

        # Patch get_app_data_dir to return our test directory
        monkeypatch.setattr("pwa_forge.config.get_app_data_dir", lambda: tmp_path)

        # Create app profile
        app_id = "test-app"
        app_dir = config.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = app_dir / "manifest.yaml"
        manifest_path.write_text("id: test-app\nname: Test App\n")

        # Create registry
        registry = Registry(registry_file)
        registry.add_app({
            "id": app_id,
            "name": "Test App",
            "manifest_path": str(manifest_path),
        })

        # Create userscript
        userscript_path = config.userscripts_dir / "external-links.user.js"
        userscript_path.parent.mkdir(parents=True, exist_ok=True)
        userscript_path.write_text("// Test userscript\nconsole.log('test');")

        # Install
        result = install_userscript(
            app_id=app_id,
            config=config,
            scheme="ff",
            dry_run=False,
        )

        # Verify
        assert result["app_id"] == app_id
        assert result["scheme"] == "ff"
        installed_path = Path(result["installed_path"])
        assert installed_path.exists()
        assert installed_path.read_text() == "// Test userscript\nconsole.log('test');"

        # Verify metadata file
        metadata_file = installed_path.parent / "metadata.json"
        assert metadata_file.exists()
        metadata = json.loads(metadata_file.read_text())
        assert metadata["scheme"] == "ff"
        assert metadata["namespace"] == "pwa-forge"

    def test_install_userscript_dry_run(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test userscript installation in dry-run mode."""
        # Setup
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.userscripts = tmp_path / "userscripts"
        registry_file = tmp_path / "registry.json"

        # Patch get_app_data_dir to return our test directory
        monkeypatch.setattr("pwa_forge.config.get_app_data_dir", lambda: tmp_path)

        # Create app profile
        app_id = "test-app"
        app_dir = config.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = app_dir / "manifest.yaml"
        manifest_path.write_text("id: test-app\nname: Test App\n")

        # Create registry
        registry = Registry(registry_file)
        registry.add_app({
            "id": app_id,
            "name": "Test App",
            "manifest_path": str(manifest_path),
        })

        # Create userscript
        userscript_path = config.userscripts_dir / "external-links.user.js"
        userscript_path.parent.mkdir(parents=True, exist_ok=True)
        userscript_path.write_text("// Test userscript")

        # Install in dry-run mode
        result = install_userscript(
            app_id=app_id,
            config=config,
            scheme="ff",
            dry_run=True,
        )

        # Verify result is returned but files not created
        assert result["app_id"] == app_id
        installed_path = Path(result["installed_path"])
        assert not installed_path.exists()

    def test_install_userscript_app_not_found(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test installation fails when app is not found."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        registry_file = tmp_path / "registry.json"

        # Patch get_app_data_dir to return our test directory
        monkeypatch.setattr("pwa_forge.config.get_app_data_dir", lambda: tmp_path)

        # Create empty registry
        Registry(registry_file)

        # Try to install for non-existent app
        with pytest.raises(UserscriptCommandError, match="not found in registry"):
            install_userscript(
                app_id="nonexistent-app",
                config=config,
                dry_run=False,
            )

    def test_install_userscript_userscript_not_found(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test installation fails when userscript is not found."""
        # Setup
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.userscripts = tmp_path / "userscripts"
        registry_file = tmp_path / "registry.json"

        # Patch get_app_data_dir to return our test directory
        monkeypatch.setattr("pwa_forge.config.get_app_data_dir", lambda: tmp_path)

        # Create app profile
        app_id = "test-app"
        app_dir = config.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = app_dir / "manifest.yaml"
        manifest_path.write_text("id: test-app\nname: Test App\n")

        # Create registry
        registry = Registry(registry_file)
        registry.add_app({
            "id": app_id,
            "name": "Test App",
            "manifest_path": str(manifest_path),
        })

        # Don't create userscript - should fail
        with pytest.raises(UserscriptCommandError, match="Userscript not found"):
            install_userscript(
                app_id=app_id,
                config=config,
                dry_run=False,
            )

    def test_install_userscript_custom_path(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test installation with custom userscript path."""
        # Setup
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.userscripts = tmp_path / "userscripts"
        registry_file = tmp_path / "registry.json"

        # Patch get_app_data_dir to return our test directory
        monkeypatch.setattr("pwa_forge.config.get_app_data_dir", lambda: tmp_path)

        # Create app profile
        app_id = "test-app"
        app_dir = config.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = app_dir / "manifest.yaml"
        manifest_path.write_text("id: test-app\nname: Test App\n")

        # Create registry
        registry = Registry(registry_file)
        registry.add_app({
            "id": app_id,
            "name": "Test App",
            "manifest_path": str(manifest_path),
        })

        # Create custom userscript
        custom_script = tmp_path / "custom.user.js"
        custom_script.write_text("// Custom userscript")

        # Install with custom path
        result = install_userscript(
            app_id=app_id,
            config=config,
            scheme="ext",
            userscript_path=str(custom_script),
            dry_run=False,
        )

        # Verify
        assert result["scheme"] == "ext"
        installed_path = Path(result["installed_path"])
        assert installed_path.exists()
        assert installed_path.read_text() == "// Custom userscript"


class TestSetupUserscript:
    """Test setup_userscript function."""

    def test_setup_userscript_complete_flow(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test complete setup flow: generate, install extension, and inject script."""
        # Setup
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.userscripts = tmp_path / "userscripts"
        registry_file = tmp_path / "registry.json"

        # Patch get_app_data_dir to return our test directory
        monkeypatch.setattr("pwa_forge.config.get_app_data_dir", lambda: tmp_path)

        # Create app profile
        app_id = "test-app"
        app_dir = config.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = app_dir / "manifest.yaml"
        manifest_path.write_text("id: test-app\nname: Test App\n")

        # Create registry
        registry = Registry(registry_file)
        registry.add_app({
            "id": app_id,
            "name": "Test App",
            "manifest_path": str(manifest_path),
        })

        # Setup
        result = setup_userscript(
            app_id=app_id,
            config=config,
            scheme="ff",
            in_scope_hosts="example.com",
            dry_run=False,
        )

        # Verify results
        assert result["app_id"] == app_id
        assert result["scheme"] == "ff"
        assert result["extension_installed"] is True

        # Verify userscript was created
        userscript_path = Path(result["userscript_path"])
        assert userscript_path.exists()
        content = userscript_path.read_text()
        assert "ff" in content
        assert "example.com" in content

        # Verify userscript was installed to profile
        installed_path = Path(result["installed_path"])
        assert installed_path.exists()

        # Verify extension was created
        extension_path = Path(result["extension_path"])
        assert extension_path.exists()
        assert (extension_path / "manifest.json").exists()
        assert (extension_path / "background.js").exists()
        assert (extension_path / "content.js").exists()

        # Verify extension manifest
        manifest = json.loads((extension_path / "manifest.json").read_text())
        assert manifest["name"] == "Violentmonkey"
        assert manifest["manifest_version"] == 3

    def test_setup_userscript_dry_run(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test setup in dry-run mode."""
        # Setup
        config = Config()
        config.directories.apps = tmp_path / "apps"
        config.directories.userscripts = tmp_path / "userscripts"
        registry_file = tmp_path / "registry.json"

        # Patch get_app_data_dir to return our test directory
        monkeypatch.setattr("pwa_forge.config.get_app_data_dir", lambda: tmp_path)

        # Create app profile
        app_id = "test-app"
        app_dir = config.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = app_dir / "manifest.yaml"
        manifest_path.write_text("id: test-app\nname: Test App\n")

        # Create registry
        registry = Registry(registry_file)
        registry.add_app({
            "id": app_id,
            "name": "Test App",
            "manifest_path": str(manifest_path),
        })

        # Setup in dry-run mode
        result = setup_userscript(
            app_id=app_id,
            config=config,
            scheme="ff",
            in_scope_hosts="example.com",
            dry_run=True,
        )

        # Verify result is returned but files not created
        assert result["app_id"] == app_id
        assert result["extension_installed"] is True  # Dry-run still returns True

        # Verify files were NOT created
        userscript_path = Path(result["userscript_path"])
        assert not userscript_path.exists()

        installed_path = Path(result["installed_path"])
        assert not installed_path.exists()

        extension_path = Path(result["extension_path"])
        assert not extension_path.exists()

    def test_setup_userscript_app_not_found(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test setup fails when app is not found."""
        config = Config()
        config.directories.apps = tmp_path / "apps"
        registry_file = tmp_path / "registry.json"

        # Patch get_app_data_dir to return our test directory
        monkeypatch.setattr("pwa_forge.config.get_app_data_dir", lambda: tmp_path)

        # Create empty registry
        Registry(registry_file)

        # Try to setup for non-existent app
        with pytest.raises(UserscriptCommandError, match="not found in registry"):
            setup_userscript(
                app_id="nonexistent-app",
                config=config,
                dry_run=False,
            )
