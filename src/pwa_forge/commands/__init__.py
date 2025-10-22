"""Command implementations for PWA Forge."""

from __future__ import annotations

__all__ = [
    "add_app",
    "list_apps",
    "remove_app",
    "generate_handler",
    "install_handler",
    "generate_userscript",
]

from pwa_forge.commands.add import add_app
from pwa_forge.commands.handler import generate_handler, install_handler
from pwa_forge.commands.list_apps import list_apps
from pwa_forge.commands.remove import remove_app
from pwa_forge.commands.userscript import generate_userscript
