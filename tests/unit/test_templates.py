"""Unit tests for template rendering."""

from __future__ import annotations

from pathlib import Path

from pwa_forge import templates


class TestTemplateEngine:
    """Test TemplateEngine class."""

    def test_initialization(self) -> None:
        """Test template engine initialization."""
        engine = templates.TemplateEngine()
        assert engine.env is not None
        assert "expandpath" in engine.env.filters

    def test_filter_expand_path(self) -> None:
        """Test expandpath filter."""
        engine = templates.TemplateEngine()
        result = engine._filter_expand_path("~/test/path")
        assert "~" not in result
        assert Path(result).is_absolute()

    def test_render_desktop_file(self) -> None:
        """Test rendering desktop file."""
        engine = templates.TemplateEngine()
        result = engine.render_desktop_file(
            name="Test App",
            wrapper_path="/usr/bin/test-wrapper",
            icon_path="/usr/share/icons/test.png",
            categories=["Network", "Utility"],
            wm_class="TestApp",
        )
        assert "[Desktop Entry]" in result
        assert "Name=Test App" in result
        assert "Exec=/usr/bin/test-wrapper %U" in result
        assert "Icon=/usr/share/icons/test.png" in result
        assert "Categories=Network;Utility;" in result
        assert "StartupWMClass=TestApp" in result

    def test_render_desktop_file_with_comment(self) -> None:
        """Test rendering desktop file with custom comment."""
        engine = templates.TemplateEngine()
        result = engine.render_desktop_file(
            name="Test App",
            comment="Custom comment",
            wrapper_path="/usr/bin/test-wrapper",
            icon_path="/usr/share/icons/test.png",
            categories=["Network"],
            wm_class="TestApp",
        )
        assert "Comment=Custom comment" in result

    def test_render_desktop_file_without_comment(self) -> None:
        """Test rendering desktop file without comment uses default."""
        engine = templates.TemplateEngine()
        result = engine.render_desktop_file(
            name="Test App",
            wrapper_path="/usr/bin/test-wrapper",
            icon_path="/usr/share/icons/test.png",
            categories=["Network"],
            wm_class="TestApp",
        )
        assert "Comment=Test App PWA" in result

    def test_render_wrapper_script(self) -> None:
        """Test rendering wrapper script."""
        engine = templates.TemplateEngine()
        result = engine.render_wrapper_script(
            name="Test App",
            id="test-app",
            browser_exec="/usr/bin/chrome",
            wm_class="TestApp",
            ozone_platform="x11",
            url="https://example.com",
            profile="/home/user/.config/pwa-forge/apps/test-app",
            enable_features=["Feature1", "Feature2"],
            disable_features=["BadFeature"],
        )
        assert "#!/bin/bash" in result
        assert "# App: Test App" in result
        assert "# ID: test-app" in result
        assert '--class="TestApp"' in result
        assert "--ozone-platform=x11" in result
        assert '--app="https://example.com"' in result
        assert "--enable-features=Feature1,Feature2" in result
        assert "--disable-features=BadFeature" in result

    def test_render_wrapper_script_without_features(self) -> None:
        """Test rendering wrapper script without feature flags."""
        engine = templates.TemplateEngine()
        result = engine.render_wrapper_script(
            name="Test App",
            id="test-app",
            browser_exec="/usr/bin/chrome",
            wm_class="TestApp",
            ozone_platform="x11",
            url="https://example.com",
            profile="/home/user/.config/pwa-forge/apps/test-app",
        )
        assert "#!/bin/bash" in result
        assert "--enable-features" not in result
        assert "--disable-features" not in result

    def test_render_wrapper_script_with_additional_flags(self) -> None:
        """Test rendering wrapper script with additional flags."""
        engine = templates.TemplateEngine()
        result = engine.render_wrapper_script(
            name="Test App",
            id="test-app",
            browser_exec="/usr/bin/chrome",
            wm_class="TestApp",
            ozone_platform="x11",
            url="https://example.com",
            profile="/home/user/.config/pwa-forge/apps/test-app",
            additional_flags="--custom-flag --another-flag",
        )
        assert "--custom-flag --another-flag" in result

    def test_render_handler_script(self) -> None:
        """Test rendering handler script."""
        engine = templates.TemplateEngine()
        result = engine.render_handler_script(
            scheme="ff",
            browser="firefox",
            browser_exec="/usr/bin/firefox",
        )
        assert "#!/bin/bash" in result
        assert "# Scheme: ff://" in result
        assert "# Target browser: firefox" in result
        assert 'payload="${raw#ff:}"' in result
        assert 'exec "/usr/bin/firefox" --new-window "$decoded"' in result

    def test_render_handler_desktop(self) -> None:
        """Test rendering handler desktop file."""
        engine = templates.TemplateEngine()
        result = engine.render_handler_desktop(
            browser="firefox",
            scheme="ff",
            handler_script="/usr/bin/pwa-forge-handler-ff",
        )
        assert "[Desktop Entry]" in result
        assert "Name=Open in Firefox (ff handler)" in result
        assert "Comment=Handle ff:// URLs" in result
        assert "Exec=/usr/bin/pwa-forge-handler-ff %u" in result
        assert "MimeType=x-scheme-handler/ff;" in result
        assert "NoDisplay=true" in result

    def test_render_handler_desktop_with_icon(self) -> None:
        """Test rendering handler desktop file with custom icon."""
        engine = templates.TemplateEngine()
        result = engine.render_handler_desktop(
            browser="firefox",
            scheme="ff",
            handler_script="/usr/bin/pwa-forge-handler-ff",
            icon="firefox",
        )
        assert "Icon=firefox" in result

    def test_render_handler_desktop_without_icon(self) -> None:
        """Test rendering handler desktop file without icon uses default."""
        engine = templates.TemplateEngine()
        result = engine.render_handler_desktop(
            browser="firefox",
            scheme="ff",
            handler_script="/usr/bin/pwa-forge-handler-ff",
        )
        assert "Icon=web-browser" in result

    def test_render_userscript(self) -> None:
        """Test rendering userscript."""
        engine = templates.TemplateEngine()
        result = engine.render_userscript(
            url_pattern="https://example.com/*",
            in_scope_hosts=["example.com", "www.example.com"],
            scheme="ff",
        )
        assert "// ==UserScript==" in result
        assert "// @name         PWA Forge External Link Handler" in result
        assert "// @match        https://example.com/*" in result
        assert 'const IN_SCOPE_HOSTS = ["example.com", "www.example.com"]' in result
        assert "const SCHEME = 'ff';" in result
        assert "function isExternal(url)" in result

    def test_render_template_generic(self) -> None:
        """Test rendering arbitrary template."""
        engine = templates.TemplateEngine()
        result = engine.render_template(
            "desktop.j2",
            name="Test",
            wrapper_path="/test",
            icon_path="/test.png",
            categories=["Test"],
            wm_class="Test",
        )
        assert "[Desktop Entry]" in result


class TestGetTemplateEngine:
    """Test get_template_engine singleton function."""

    def test_returns_template_engine(self) -> None:
        """Test that get_template_engine returns TemplateEngine instance."""
        engine = templates.get_template_engine()
        assert isinstance(engine, templates.TemplateEngine)

    def test_returns_same_instance(self) -> None:
        """Test that get_template_engine returns the same instance."""
        engine1 = templates.get_template_engine()
        engine2 = templates.get_template_engine()
        assert engine1 is engine2


class TestRenderTemplate:
    """Test render_template function."""

    def test_render_template_function(self) -> None:
        """Test the module-level render_template function."""
        result = templates.render_template(
            "desktop.j2",
            {
                "name": "Test",
                "wrapper_path": "/test",
                "icon_path": "/test.png",
                "categories": ["Test"],
                "wm_class": "Test",
            },
        )
        assert "[Desktop Entry]" in result
        assert "Name=Test" in result
