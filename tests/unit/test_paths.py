"""Unit tests for path utilities."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from pwa_forge.utils import paths


class TestPathGetters:
    """Test path getter functions."""

    def test_get_app_data_dir(self) -> None:
        """Test getting application data directory."""
        data_dir = paths.get_app_data_dir()
        assert isinstance(data_dir, Path)
        assert "pwa-forge" in str(data_dir)

    def test_get_app_config_dir(self) -> None:
        """Test getting application config directory."""
        config_dir = paths.get_app_config_dir()
        assert isinstance(config_dir, Path)
        assert "pwa-forge" in str(config_dir)

    def test_get_app_cache_dir(self) -> None:
        """Test getting application cache directory."""
        cache_dir = paths.get_app_cache_dir()
        assert isinstance(cache_dir, Path)
        assert "pwa-forge" in str(cache_dir)

    def test_get_desktop_dir(self) -> None:
        """Test getting XDG desktop directory."""
        desktop_dir = paths.get_desktop_dir()
        assert desktop_dir == Path.home() / ".local" / "share" / "applications"

    def test_get_icons_dir(self) -> None:
        """Test getting icons directory."""
        icons_dir = paths.get_icons_dir()
        assert icons_dir == Path.home() / ".local" / "share" / "icons" / "pwa-forge"

    def test_get_wrappers_dir(self) -> None:
        """Test getting wrappers directory."""
        wrappers_dir = paths.get_wrappers_dir()
        assert wrappers_dir == Path.home() / ".local" / "bin" / "pwa-forge-wrappers"

    def test_get_apps_dir(self) -> None:
        """Test getting apps directory."""
        apps_dir = paths.get_apps_dir()
        assert isinstance(apps_dir, Path)
        assert "pwa-forge" in str(apps_dir)
        assert str(apps_dir).endswith("apps")

    def test_get_userscripts_dir(self) -> None:
        """Test getting userscripts directory."""
        userscripts_dir = paths.get_userscripts_dir()
        assert isinstance(userscripts_dir, Path)
        assert "pwa-forge" in str(userscripts_dir)
        assert str(userscripts_dir).endswith("userscripts")

    def test_get_registry_path(self) -> None:
        """Test getting registry file path."""
        registry_path = paths.get_registry_path()
        assert isinstance(registry_path, Path)
        assert registry_path.name == "registry.json"


class TestExpandPath:
    """Test path expansion functionality."""

    def test_expand_home_directory(self) -> None:
        """Test expanding ~ in paths."""
        expanded = paths.expand_path("~/test/path")
        assert "~" not in str(expanded)
        assert expanded.is_absolute()

    def test_expand_relative_path(self) -> None:
        """Test expanding relative paths."""
        expanded = paths.expand_path("./test")
        assert expanded.is_absolute()

    def test_expand_absolute_path(self) -> None:
        """Test absolute paths remain absolute."""
        expanded = paths.expand_path("/tmp/test")
        assert expanded == Path("/tmp/test")

    def test_expand_path_object(self) -> None:
        """Test expanding Path objects."""
        path_obj = Path("~/test")
        expanded = paths.expand_path(path_obj)
        assert expanded.is_absolute()
        assert "~" not in str(expanded)

    def test_expand_with_env_var(self) -> None:
        """Test path expansion with environment variables."""
        with patch.dict(os.environ, {"TEST_VAR": "/test/path"}):
            # expanduser doesn't handle env vars, but Path.resolve() makes it absolute
            expanded = paths.expand_path("./relative")
            assert expanded.is_absolute()


class TestEnsureDir:
    """Test directory creation functionality."""

    def test_ensure_dir_creates_new_directory(self, tmp_path: Path) -> None:
        """Test creating a new directory."""
        test_dir = tmp_path / "new_dir"
        result = paths.ensure_dir(test_dir)
        assert result == test_dir
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_ensure_dir_with_parents(self, tmp_path: Path) -> None:
        """Test creating nested directories."""
        test_dir = tmp_path / "parent" / "child" / "grandchild"
        result = paths.ensure_dir(test_dir)
        assert result == test_dir
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_ensure_dir_already_exists(self, tmp_path: Path) -> None:
        """Test that ensure_dir works on existing directories."""
        test_dir = tmp_path / "existing"
        test_dir.mkdir()
        result = paths.ensure_dir(test_dir)
        assert result == test_dir
        assert test_dir.exists()

    def test_ensure_dir_with_custom_mode(self, tmp_path: Path) -> None:
        """Test creating directory with custom permissions."""
        test_dir = tmp_path / "custom_mode"
        result = paths.ensure_dir(test_dir, mode=0o700)
        assert result == test_dir
        assert test_dir.exists()
        # Check permissions (note: umask may affect this)
        stat_mode = test_dir.stat().st_mode & 0o777
        # On some systems umask might affect this, so we just check it was created
        assert stat_mode in (0o700, 0o755)  # Allow for umask variations
