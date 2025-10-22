"""Template rendering for PWA Forge artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from pwa_forge.utils.logger import get_logger

__all__ = ["TemplateEngine", "get_template_engine"]

logger = get_logger(__name__)


class TemplateEngine:
    """Jinja2-based template rendering engine."""

    def __init__(self) -> None:
        """Initialize the template engine."""
        self.env = Environment(
            loader=PackageLoader("pwa_forge", "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Add custom filters
        self.env.filters["expandpath"] = self._filter_expand_path

    def _filter_expand_path(self, path: str | Path) -> str:
        """Jinja2 filter to expand user paths.

        Args:
            path: Path to expand.

        Returns:
            Expanded path as string.
        """
        return str(Path(path).expanduser().resolve())

    def render_desktop_file(self, **context: Any) -> str:
        """Render a .desktop file template.

        Args:
            **context: Template variables.

        Returns:
            Rendered .desktop file content.
        """
        template = self.env.get_template("desktop.j2")
        return template.render(**context)

    def render_wrapper_script(self, **context: Any) -> str:
        """Render a wrapper script template.

        Args:
            **context: Template variables.

        Returns:
            Rendered wrapper script content.
        """
        template = self.env.get_template("wrapper.j2")
        return template.render(**context)

    def render_handler_script(self, **context: Any) -> str:
        """Render a URL scheme handler script template.

        Args:
            **context: Template variables.

        Returns:
            Rendered handler script content.
        """
        template = self.env.get_template("handler-script.j2")
        return template.render(**context)

    def render_handler_desktop(self, **context: Any) -> str:
        """Render a URL scheme handler .desktop file template.

        Args:
            **context: Template variables.

        Returns:
            Rendered handler .desktop file content.
        """
        template = self.env.get_template("handler-desktop.j2")
        return template.render(**context)

    def render_userscript(self, **context: Any) -> str:
        """Render a userscript template.

        Args:
            **context: Template variables.

        Returns:
            Rendered userscript content.
        """
        template = self.env.get_template("userscript.j2")
        return template.render(**context)

    def render_template(self, template_name: str, **context: Any) -> str:
        """Render an arbitrary template by name.

        Args:
            template_name: Name of the template file.
            **context: Template variables.

        Returns:
            Rendered template content.
        """
        template = self.env.get_template(template_name)
        return template.render(**context)


# Singleton instance
_template_engine: TemplateEngine | None = None


def get_template_engine() -> TemplateEngine:
    """Get the singleton template engine instance.

    Returns:
        TemplateEngine instance.
    """
    global _template_engine
    if _template_engine is None:
        _template_engine = TemplateEngine()
    return _template_engine
