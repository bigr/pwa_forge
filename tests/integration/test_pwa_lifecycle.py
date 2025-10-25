"""Integration tests for PWA lifecycle (add, list, remove)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pwa_forge.commands.add import add_app
from pwa_forge.commands.list_apps import list_apps
from pwa_forge.commands.remove import remove_app
from pwa_forge.config import Config
from pwa_forge.registry import Registry


class IsolatedConfig(Config):
    """Configuration with isolated registry for testing."""

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

    @property
    def registry_file(self) -> Path:
        """Get test registry file path."""
        registry_dir = self._tmp_path / "data"
        registry_dir.mkdir(parents=True, exist_ok=True)
        return registry_dir / "registry.json"


@pytest.fixture  # type: ignore[misc]
def test_config(tmp_path: Path) -> IsolatedConfig:
    """Create a test configuration with temporary directories."""
    return IsolatedConfig(tmp_path)


class TestPWALifecycle:
    """Test complete PWA lifecycle."""

    def test_add_creates_all_artifacts(self, test_config: Config) -> None:
        """Test that add command creates all necessary files."""
        # Add a PWA
        result = add_app(
            url="https://example.com",
            config=test_config,
            name="Example App",
            app_id="example-app",
            browser="chrome",
            dry_run=False,
        )

        # Verify return value
        assert result["id"] == "example-app"
        assert result["name"] == "Example App"
        assert result["url"] == "https://example.com"

        # Verify profile directory was created
        profile_path = Path(result["profile"])
        assert profile_path.exists()
        assert profile_path.is_dir()

        # Verify wrapper script was created
        wrapper_path = Path(result["wrapper"])
        assert wrapper_path.exists()
        assert wrapper_path.is_file()
        # Check it's executable
        assert wrapper_path.stat().st_mode & 0o111

        # Verify wrapper script content
        wrapper_content = wrapper_path.read_text()
        assert "#!/bin/bash" in wrapper_content
        assert "example-app" in wrapper_content
        assert "https://example.com" in wrapper_content

        # Verify desktop file was created
        desktop_path = Path(result["desktop_file"])
        assert desktop_path.exists()
        assert desktop_path.is_file()

        # Verify desktop file content
        desktop_content = desktop_path.read_text()
        assert "[Desktop Entry]" in desktop_content
        assert "Name=Example App" in desktop_content
        assert "Exec=" in desktop_content
        assert "Icon=" in desktop_content

        # Verify manifest was created
        manifest_path = Path(result["manifest"])
        assert manifest_path.exists()
        assert manifest_path.is_file()

        # Verify manifest content
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        assert manifest["id"] == "example-app"
        assert manifest["name"] == "Example App"
        assert manifest["url"] == "https://example.com"
        assert manifest["browser"] == "chrome"
        assert "created" in manifest
        assert "modified" in manifest

        # Verify registry entry
        registry = Registry(test_config.registry_file)
        app = registry.get_app("example-app")
        assert app["id"] == "example-app"
        assert app["name"] == "Example App"
        assert app["status"] == "active"

    def test_add_with_icon(self, test_config: Config, tmp_path: Path) -> None:
        """Test adding PWA with custom icon."""
        # Create a dummy icon file
        icon_source = tmp_path / "test-icon.png"
        icon_source.write_text("fake icon data")

        # Add PWA with icon
        add_app(
            url="https://test.com",
            config=test_config,
            name="Test App",
            app_id="test-app",
            icon=str(icon_source),
            dry_run=False,
        )

        # Verify icon was copied
        icon_dir = test_config.icons_dir
        copied_icon = icon_dir / "test-app.png"
        assert copied_icon.exists()
        assert copied_icon.read_text() == "fake icon data"

    def test_list_shows_added_apps(self, test_config: Config) -> None:
        """Test that list command shows added apps."""
        # Add multiple PWAs
        add_app(
            url="https://app1.com",
            config=test_config,
            name="App One",
            app_id="app1",
            dry_run=False,
        )
        add_app(
            url="https://app2.com",
            config=test_config,
            name="App Two",
            app_id="app2",
            dry_run=False,
        )

        # List apps
        apps = list_apps(test_config, verbose=False, output_format="json")

        # Verify both apps are listed
        assert len(apps) == 2
        app_ids = [app["id"] for app in apps]
        assert "app1" in app_ids
        assert "app2" in app_ids

    def test_remove_cleans_up_files(self, test_config: Config) -> None:
        """Test that remove command cleans up all files."""
        # Add a PWA
        result = add_app(
            url="https://remove-test.com",
            config=test_config,
            name="Remove Test",
            app_id="remove-test",
            dry_run=False,
        )

        # Store paths for verification
        profile_path = Path(result["profile"])
        wrapper_path = Path(result["wrapper"])
        desktop_path = Path(result["desktop_file"])
        manifest_path = Path(result["manifest"])

        # Verify files exist
        assert profile_path.exists()
        assert wrapper_path.exists()
        assert desktop_path.exists()
        assert manifest_path.exists()

        # Remove the PWA (without removing profile)
        remove_app(
            app_id="remove-test",
            config=test_config,
            remove_profile=False,
            dry_run=False,
        )

        # Verify files were removed
        assert not wrapper_path.exists()
        assert not desktop_path.exists()
        assert not manifest_path.exists()

        # Profile should still exist
        assert profile_path.exists()

        # Verify registry entry was removed
        registry = Registry(test_config.registry_file)
        apps = registry.list_apps()
        assert not any(app["id"] == "remove-test" for app in apps)

    def test_remove_with_profile_deletion(self, test_config: Config) -> None:
        """Test that remove command can delete profile directory."""
        # Add a PWA
        result = add_app(
            url="https://profile-test.com",
            config=test_config,
            name="Profile Test",
            app_id="profile-test",
            dry_run=False,
        )

        profile_path = Path(result["profile"])
        assert profile_path.exists()

        # Remove with profile deletion
        remove_app(
            app_id="profile-test",
            config=test_config,
            remove_profile=True,
            dry_run=False,
        )

        # Profile should be deleted
        assert not profile_path.exists()

    def test_add_list_remove_workflow(self, test_config: Config) -> None:
        """Test complete workflow: add → list → remove."""
        # Start with empty registry
        apps = list_apps(test_config, verbose=False, output_format="json")
        assert len(apps) == 0

        # Add PWA
        add_app(
            url="https://workflow.com",
            config=test_config,
            name="Workflow Test",
            app_id="workflow",
            dry_run=False,
        )

        # Verify it appears in list
        apps = list_apps(test_config, verbose=False, output_format="json")
        assert len(apps) == 1
        assert apps[0]["id"] == "workflow"

        # Remove it
        remove_app(
            app_id="workflow",
            config=test_config,
            remove_profile=True,
            dry_run=False,
        )

        # Verify it's gone
        apps = list_apps(test_config, verbose=False, output_format="json")
        assert len(apps) == 0

    def test_registry_persistence(self, test_config: Config) -> None:
        """Test that registry persists across operations."""
        # Add PWA
        add_app(
            url="https://persist.com",
            config=test_config,
            name="Persist Test",
            app_id="persist",
            dry_run=False,
        )

        # Create new registry instance (simulating restart)
        registry = Registry(test_config.registry_file)
        app = registry.get_app("persist")

        assert app["id"] == "persist"
        assert app["name"] == "Persist Test"
        assert app["url"] == "https://persist.com"

    def test_dry_run_creates_no_files(self, test_config: Config) -> None:
        """Test that dry-run mode creates no actual files."""
        # Run add in dry-run mode
        result = add_app(
            url="https://dryrun.com",
            config=test_config,
            name="Dry Run Test",
            app_id="dryrun",
            dry_run=True,
        )

        # Paths are returned but files should not exist
        assert not Path(result["profile"]).exists()
        assert not Path(result["wrapper"]).exists()
        assert not Path(result["desktop_file"]).exists()
        assert not Path(result["manifest"]).exists()

        # Registry should not have the entry
        registry = Registry(test_config.registry_file)
        apps = registry.list_apps()
        assert not any(app["id"] == "dryrun" for app in apps)

    def test_duplicate_id_error(self, test_config: Config) -> None:
        """Test that adding duplicate ID raises error."""
        from pwa_forge.commands.add import AddCommandError

        # Add first PWA
        add_app(
            url="https://dup1.com",
            config=test_config,
            name="Duplicate Test",
            app_id="duplicate",
            dry_run=False,
        )

        # Try to add another with same ID
        with pytest.raises(AddCommandError, match="already exists"):
            add_app(
                url="https://dup2.com",
                config=test_config,
                name="Another App",
                app_id="duplicate",
                dry_run=False,
            )

    def test_remove_nonexistent_error(self, test_config: Config) -> None:
        """Test that removing non-existent app raises error."""
        from pwa_forge.commands.remove import RemoveCommandError

        with pytest.raises(RemoveCommandError, match="not found"):
            remove_app(
                app_id="nonexistent",
                config=test_config,
                dry_run=False,
            )

    def test_manifest_yaml_format(self, test_config: Config) -> None:
        """Test that manifest is valid YAML with expected structure."""
        # Add PWA
        result = add_app(
            url="https://yaml-test.com",
            config=test_config,
            name="YAML Test",
            app_id="yaml-test",
            browser="chromium",
            out_of_scope="same-browser-window",
            dry_run=False,
        )

        # Load and validate manifest
        manifest_path = Path(result["manifest"])
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        # Check required fields
        assert manifest["id"] == "yaml-test"
        assert manifest["name"] == "YAML Test"
        assert manifest["url"] == "https://yaml-test.com"
        assert manifest["browser"] == "chromium"
        assert manifest["out_of_scope"] == "same-browser-window"
        assert manifest["version"] == 1

        # Check computed fields
        assert "profile" in manifest
        assert "wm_class" in manifest
        assert "created" in manifest
        assert "modified" in manifest

    def test_registry_json_format(self, test_config: Config) -> None:
        """Test that registry is valid JSON with expected structure."""
        # Add PWA
        add_app(
            url="https://json-test.com",
            config=test_config,
            name="JSON Test",
            app_id="json-test",
            dry_run=False,
        )

        # Load and validate registry
        registry_path = test_config.registry_file
        with open(registry_path) as f:
            registry_data = json.load(f)

        # Check structure
        assert "version" in registry_data
        assert registry_data["version"] == 1
        assert "apps" in registry_data
        assert isinstance(registry_data["apps"], list)
        assert len(registry_data["apps"]) > 0

        # Find our app entry
        app = next((a for a in registry_data["apps"] if a["id"] == "json-test"), None)
        assert app is not None
        assert app["name"] == "JSON Test"
        assert app["url"] == "https://json-test.com"

    def test_remove_manifest_load_error_handling(self, test_config: Config) -> None:
        """Test that remove handles manifest loading errors gracefully."""
        # Add PWA first
        result = add_app(
            url="https://manifest-error.com",
            config=test_config,
            name="Manifest Error Test",
            app_id="manifest-error",
            dry_run=False,
        )

        manifest_path = Path(result["manifest"])
        # Corrupt the manifest file
        manifest_path.write_text("invalid: yaml: content: [unclosed")

        # Remove should handle the error gracefully and continue
        remove_app(
            app_id="manifest-error",
            config=test_config,
            remove_profile=True,
            dry_run=False,
        )

        # Files should still be removed despite manifest error
        assert not manifest_path.exists()
        assert not Path(result["wrapper"]).exists()
        assert not Path(result["desktop_file"]).exists()

    def test_remove_empty_directory_cleanup(self, test_config: Config) -> None:
        """Test that remove cleans up empty directories."""
        # Add PWA
        result = add_app(
            url="https://cleanup-test.com",
            config=test_config,
            name="Cleanup Test",
            app_id="cleanup-test",
            dry_run=False,
        )

        manifest_path = Path(result["manifest"])
        manifest_dir = manifest_path.parent
        profile_path = Path(result["profile"])

        # Verify directory exists
        assert manifest_dir.exists()

        # Remove with profile deletion (should clean up directory)
        remove_app(
            app_id="cleanup-test",
            config=test_config,
            remove_profile=True,
            dry_run=False,
        )

        # Manifest directory should be removed (it's empty now)
        assert not manifest_dir.exists()
        # Profile directory should also be removed
        assert not profile_path.exists()

    def test_remove_directory_with_files_preserved(self, test_config: Config) -> None:
        """Test that remove preserves directory when it contains files."""
        # Add PWA
        result = add_app(
            url="https://preserve-dir.com",
            config=test_config,
            name="Preserve Dir Test",
            app_id="preserve-dir",
            dry_run=False,
        )

        manifest_path = Path(result["manifest"])
        manifest_dir = manifest_path.parent

        # Add a file to the directory (simulating extra files)
        extra_file = manifest_dir / "extra_file.txt"
        extra_file.write_text("This should prevent directory removal")

        # Remove without profile deletion
        remove_app(
            app_id="preserve-dir",
            config=test_config,
            remove_profile=False,
            dry_run=False,
        )

        # Directory should still exist because it contains extra files
        assert manifest_dir.exists()
        assert extra_file.exists()

    def test_remove_icon_cleanup(self, test_config: Config, tmp_path: Path) -> None:
        """Test that remove can clean up icon files."""
        # Create a fake icon file
        icon_path = tmp_path / "test_icon.svg"
        icon_path.write_text("<svg></svg>")

        # Add PWA with icon
        result = add_app(
            url="https://icon-test.com",
            config=test_config,
            name="Icon Test",
            app_id="icon-test",
            icon=str(icon_path),
            dry_run=False,
        )

        # Verify icon was copied to icons directory
        manifest_path = Path(result["manifest"])
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        copied_icon = Path(manifest["icon"])
        assert copied_icon.exists()

        # Remove with icon cleanup
        remove_app(
            app_id="icon-test",
            config=test_config,
            remove_icon=True,
            dry_run=False,
        )

        # Icon should be removed
        assert not copied_icon.exists()

    def test_remove_dry_run_preserves_files(self, test_config: Config) -> None:
        """Test that remove dry-run mode preserves all files."""
        # Add PWA
        result = add_app(
            url="https://dry-remove.com",
            config=test_config,
            name="Dry Remove Test",
            app_id="dry-remove",
            dry_run=False,
        )

        wrapper_path = Path(result["wrapper"])
        desktop_path = Path(result["desktop_file"])
        manifest_path = Path(result["manifest"])
        profile_path = Path(result["profile"])

        # Remove in dry-run mode
        remove_app(
            app_id="dry-remove",
            config=test_config,
            remove_profile=True,
            remove_icon=True,
            dry_run=True,
        )

        # All files should still exist
        assert wrapper_path.exists()
        assert desktop_path.exists()
        assert manifest_path.exists()
        assert profile_path.exists()

        # Registry should still contain the app
        registry = Registry(test_config.registry_file)
        apps = registry.list_apps()
        assert any(app["id"] == "dry-remove" for app in apps)

    def test_list_apps_yaml_output(self, test_config: Config, capsys) -> None:
        """Test list_apps with YAML output format."""
        # Add a PWA first
        add_app(
            url="https://yaml-list.com",
            config=test_config,
            name="YAML List Test",
            app_id="yaml-list",
            dry_run=False,
        )

        # List in YAML format
        result = list_apps(test_config, verbose=False, output_format="yaml")

        # Should return the apps list
        assert len(result) == 1
        assert result[0]["id"] == "yaml-list"

        # Check that YAML was printed to stdout
        captured = capsys.readouterr()
        assert "yaml-list" in captured.out
        assert "YAML List Test" in captured.out
        assert "https://yaml-list.com" in captured.out

    def test_list_apps_verbose_table_output(self, test_config: Config, capsys) -> None:
        """Test list_apps with verbose table output."""
        # Add a PWA first
        add_app(
            url="https://verbose-list.com",
            config=test_config,
            name="Verbose List Test",
            app_id="verbose-list",
            dry_run=False,
        )

        # List in verbose table format
        result = list_apps(test_config, verbose=True, output_format="table")

        # Should return the apps list
        assert len(result) == 1
        assert result[0]["id"] == "verbose-list"

        # Check that verbose output was printed to stdout
        captured = capsys.readouterr()
        output = captured.out
        assert "ID: verbose-list" in output
        assert "Name: Verbose List Test" in output
        assert "URL: https://verbose-list.com" in output
        assert "Status: active" in output
        assert "Desktop File:" in output
        assert "Wrapper Script:" in output
        assert "Manifest:" in output

    def test_list_apps_empty_registry(self, test_config: Config, capsys) -> None:
        """Test list_apps with empty registry."""
        # List with empty registry
        result = list_apps(test_config, verbose=False, output_format="table")

        # Should return empty list
        assert result == []

        # Should print table header even with no apps
        captured = capsys.readouterr()
        # When there are no apps, table format still prints headers
        lines = captured.out.strip().split("\n")
        if lines and lines[0]:  # If there's output
            assert "ID" in lines[0] or "Name" in lines[0]  # Table headers
        # Empty registry doesn't print "No PWAs found" to stdout, it's just logged


class TestAddCommandIntegration:
    """Comprehensive integration tests for add command."""

    def test_add_with_icon_copy_operation(self, test_config: IsolatedConfig, tmp_path: Path) -> None:
        """Test add command copies icon file."""
        # Create a test icon
        icon_file = tmp_path / "test_icon.png"
        icon_file.write_text("fake png content")

        result = add_app(
            url="https://icon-test.com",
            config=test_config,
            name="Icon Test",
            app_id="icon-test",
            icon=str(icon_file),
            dry_run=False,
        )

        # Verify icon was copied to icons directory
        assert result["icon"] is not None
        copied_icon = Path(result["icon"])
        assert copied_icon.exists()
        assert copied_icon.parent == test_config.directories.icons
        assert copied_icon.read_text() == "fake png content"

    def test_add_with_custom_browser_executable(self, test_config: IsolatedConfig, tmp_path: Path) -> None:
        """Test add with custom browser executable path."""
        # Create a fake browser
        custom_browser = tmp_path / "custom-chrome"
        custom_browser.write_text("#!/bin/bash\necho 'custom browser'\n")
        custom_browser.chmod(0o755)

        # Update config to use custom browser
        test_config.browsers.chrome = str(custom_browser)

        result = add_app(
            url="https://custom-browser.com",
            config=test_config,
            name="Custom Browser Test",
            app_id="custom-browser",
            browser="chrome",
            dry_run=False,
        )

        # Verify wrapper script contains custom browser path
        wrapper_path = Path(result["wrapper"])
        content = wrapper_path.read_text()
        assert str(custom_browser) in content

    def test_add_with_profile_directory_creation(self, test_config: IsolatedConfig) -> None:
        """Test add creates profile directory with correct permissions."""
        result = add_app(
            url="https://profile-test.com",
            config=test_config,
            name="Profile Test",
            app_id="profile-test",
            dry_run=False,
        )

        # Verify profile directory was created
        profile_path = Path(result["profile"])
        assert profile_path.exists()
        assert profile_path.is_dir()

        # Verify it's under the apps directory
        assert profile_path == test_config.directories.apps / "profile-test"

        # Verify permissions are set correctly (0o755 = rwxr-xr-x)
        # This ensures Chrome/Chromium can write to the directory
        mode = profile_path.stat().st_mode
        permissions = mode & 0o777
        assert permissions == 0o755, f"Expected 0o755, got {oct(permissions)}"

    def test_add_with_wm_class_generation(self, test_config: IsolatedConfig) -> None:
        """Test add generates WM class from app name."""
        result = add_app(
            url="https://wm-test.com",
            config=test_config,
            name="My Test App",
            app_id="wm-test",
            dry_run=False,
        )

        # Check manifest contains WM class
        manifest_path = Path(result["manifest"])
        import yaml

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        assert "wm_class" in manifest
        assert manifest["wm_class"] == "MyTestApp"

    def test_add_with_chrome_flags_integration(self, test_config: IsolatedConfig) -> None:
        """Test add integrates chrome flags into wrapper."""
        # Pass chrome flags explicitly
        result = add_app(
            url="https://flags-test.com",
            config=test_config,
            name="Flags Test",
            app_id="flags-test",
            chrome_flags="enable-features=TestFeature,AnotherFeature;disable-features=BadFeature",
            dry_run=False,
        )

        # Verify wrapper contains chrome flags
        wrapper_path = Path(result["wrapper"])
        content = wrapper_path.read_text()
        assert "--enable-features=TestFeature,AnotherFeature" in content
        assert "--disable-features=BadFeature" in content

    def test_add_with_out_of_scope_configuration(self, test_config: IsolatedConfig) -> None:
        """Test add configures out-of-scope behavior."""
        result = add_app(
            url="https://scope-test.com",
            config=test_config,
            name="Scope Test",
            app_id="scope-test",
            out_of_scope="same-browser-window",
            dry_run=False,
        )

        # Check manifest contains out-of-scope setting
        manifest_path = Path(result["manifest"])
        import yaml

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        assert manifest["out_of_scope"] == "same-browser-window"

    def test_add_with_userscript_injection(self, test_config: IsolatedConfig, tmp_path: Path) -> None:
        """Test add configures userscript injection."""
        # Create a fake userscript
        userscript_file = tmp_path / "test.user.js"
        userscript_file.write_text("// Test userscript")

        result = add_app(
            url="https://userscript-test.com",
            config=test_config,
            name="Userscript Test",
            app_id="userscript-test",
            inject_userscript=str(userscript_file),
            dry_run=False,
        )

        # Check manifest contains inject config
        manifest_path = Path(result["manifest"])
        import yaml

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        assert "inject" in manifest
        assert "userscript" in manifest["inject"]

    def test_add_registry_entry_creation(self, test_config: IsolatedConfig) -> None:
        """Test add creates proper registry entry."""
        add_app(
            url="https://registry-test.com",
            config=test_config,
            name="Registry Test",
            app_id="registry-test",
            dry_run=False,
        )

        # Check registry contains the app
        from pwa_forge.registry import Registry

        registry = Registry(test_config.registry_file)
        apps = registry.list_apps()
        app_entry = next((app for app in apps if app["id"] == "registry-test"), None)
        assert app_entry is not None
        assert app_entry["name"] == "Registry Test"
        assert app_entry["url"] == "https://registry-test.com"
        assert app_entry["status"] == "active"
        assert "manifest_path" in app_entry
        assert "desktop_file" in app_entry
        assert "wrapper_script" in app_entry

    def test_add_desktop_file_creation(self, test_config: IsolatedConfig) -> None:
        """Test add creates desktop file with correct content."""
        result = add_app(
            url="https://desktop-test.com",
            config=test_config,
            name="Desktop Test",
            app_id="desktop-test",
            dry_run=False,
        )

        # Check desktop file exists and has correct content
        desktop_path = Path(result["desktop_file"])
        assert desktop_path.exists()
        assert desktop_path.name == "pwa-forge-desktop-test.desktop"  # Check filename

        content = desktop_path.read_text()
        assert "[Desktop Entry]" in content
        assert "Name=Desktop Test" in content
        assert "Exec=" in content  # Should contain exec line
        assert "Icon=" in content  # Should contain icon

    def test_add_error_handling_invalid_url(self, test_config: IsolatedConfig) -> None:
        """Test add handles invalid URLs."""
        import pytest
        from pwa_forge.commands.add import AddCommandError

        with pytest.raises(AddCommandError):
            add_app(
                url="not-a-valid-url",
                config=test_config,
                name="Invalid URL Test",
                app_id="invalid-url",
                dry_run=False,
            )

    def test_add_error_handling_duplicate_id(self, test_config: IsolatedConfig) -> None:
        """Test add handles duplicate app IDs."""
        import pytest
        from pwa_forge.commands.add import AddCommandError

        # Add first app
        add_app(
            url="https://first.com",
            config=test_config,
            name="First App",
            app_id="duplicate-test",
            dry_run=False,
        )

        # Try to add second app with same ID
        with pytest.raises(AddCommandError):
            add_app(
                url="https://second.com",
                config=test_config,
                name="Second App",
                app_id="duplicate-test",
                dry_run=False,
            )

    def test_add_error_handling_firefox_not_supported(self, test_config: IsolatedConfig) -> None:
        """Test add rejects Firefox browser."""
        import pytest
        from pwa_forge.commands.add import AddCommandError

        # Try to add PWA with Firefox (not supported)
        with pytest.raises(AddCommandError, match="Firefox is not supported"):
            add_app(
                url="https://example.com",
                config=test_config,
                name="Firefox Test",
                app_id="firefox-test",
                browser="firefox",
                dry_run=False,
            )

    def test_add_detects_browser_profile_write_failure(
        self, test_config: IsolatedConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test add detects when browser cannot write to profile directory."""
        from pathlib import Path
        from typing import Any
        from unittest.mock import patch

        import pytest
        from pwa_forge.commands.add import AddCommandError

        # Mock write_text to raise PermissionError for test files
        original_write_text = Path.write_text

        def mock_write_text(self: Path, *args: Any, **kwargs: Any) -> None:
            if ".pwa-forge-test" in str(self):
                raise PermissionError("Permission denied")
            return original_write_text(self, *args, **kwargs)

        with (
            patch.object(Path, "write_text", mock_write_text),
            pytest.raises(AddCommandError, match="Browser cannot write to profile directory"),
        ):
            add_app(
                url="https://example.com",
                config=test_config,
                name="Profile Write Test",
                app_id="profile-write-test",
                browser="chrome",
                dry_run=False,
            )
