"""Registry management for PWA Forge applications."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Platform-specific imports for file locking
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


class RegistryError(Exception):
    """Base exception for registry operations."""


class AppNotFoundError(RegistryError):
    """Raised when an app is not found in the registry."""


class AppExistsError(RegistryError):
    """Raised when attempting to add an app that already exists."""


class Registry:
    """Manage the PWA Forge application registry.

    The registry is a JSON file that maintains an index of all managed PWAs
    and URL scheme handlers. It provides thread-safe CRUD operations with
    file locking.
    """

    def __init__(self, registry_path: Path) -> None:
        """Initialize registry at the specified path.

        Args:
            registry_path: Path to the registry JSON file.
        """
        self.registry_path = registry_path
        self._lock_path = registry_path.with_suffix(".lock")

    @contextmanager
    def _lock(self) -> Iterator[None]:
        """Acquire exclusive lock on registry file.

        Uses platform-specific locking mechanisms:
        - Unix/Linux/macOS: fcntl.flock
        - Windows: msvcrt.locking

        Yields:
            None - context is locked for the duration of the block.
        """
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._lock_path, "w") as lock_file:
            try:
                if sys.platform == "win32":
                    # Windows: lock the entire file
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    # Unix-like systems: use fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                logger.debug(f"Acquired lock on {self._lock_path}")
                yield
            finally:
                if sys.platform == "win32":
                    # Windows: unlock the file
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    # Unix-like systems: unlock
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                logger.debug(f"Released lock on {self._lock_path}")

    def _read(self) -> dict[str, Any]:
        """Read registry data with lock.

        Returns:
            Registry data as a dictionary.
        """
        with self._lock():
            if not self.registry_path.exists():
                logger.debug("Registry file does not exist, returning empty registry")
                return {"version": 1, "apps": [], "handlers": []}

            try:
                content = self.registry_path.read_text()
                data: dict[str, Any] = json.loads(content)
                logger.debug(f"Read registry with {len(data.get('apps', []))} apps")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in registry file: {e}")
                raise RegistryError(f"Corrupted registry file: {e}") from e

    def _write(self, data: dict[str, Any]) -> None:
        """Write registry data with lock.

        Args:
            data: Registry data to write.
        """
        with self._lock():
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(data, indent=2)
            self.registry_path.write_text(content)
            logger.debug(f"Wrote registry with {len(data.get('apps', []))} apps")

    def list_apps(self) -> list[dict[str, Any]]:
        """List all registered PWAs.

        Returns:
            List of app entries.
        """
        data = self._read()
        apps: list[dict[str, Any]] = data.get("apps", [])
        return apps

    def get_app(self, app_id: str) -> dict[str, Any]:
        """Get a specific PWA by ID.

        Args:
            app_id: Application identifier.

        Returns:
            App entry dictionary.

        Raises:
            AppNotFoundError: If app is not found.
        """
        apps = self.list_apps()
        for app in apps:
            if app.get("id") == app_id:
                logger.debug(f"Found app: {app_id}")
                return app

        logger.warning(f"App not found: {app_id}")
        raise AppNotFoundError(f"PWA '{app_id}' not found in registry")

    def add_app(self, app_data: dict[str, Any]) -> None:
        """Add a new PWA to the registry.

        Args:
            app_data: App entry to add (must include 'id' field).

        Raises:
            AppExistsError: If app with same ID already exists.
            ValueError: If app_data is missing required fields.
        """
        if "id" not in app_data:
            raise ValueError("app_data must include 'id' field")

        app_id = app_data["id"]

        # Atomic read-check-write within a single lock to prevent race conditions
        with self._lock():
            # Read current registry
            if not self.registry_path.exists():
                data: dict[str, Any] = {"version": 1, "apps": [], "handlers": []}
            else:
                try:
                    content = self.registry_path.read_text()
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in registry file: {e}")
                    raise RegistryError(f"Corrupted registry file: {e}") from e

            # Check if app already exists
            apps: list[dict[str, Any]] = data.get("apps", [])
            for app in apps:
                if app.get("id") == app_id:
                    raise AppExistsError(f"PWA '{app_id}' already exists in registry")

            # Add app to registry
            apps.append(app_data)
            data["apps"] = apps

            # Write atomically
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(data, indent=2)
            self.registry_path.write_text(content)
            logger.info(f"Added app to registry: {app_id}")

    def update_app(self, app_id: str, updates: dict[str, Any]) -> None:
        """Update an existing PWA entry.

        Args:
            app_id: Application identifier.
            updates: Fields to update.

        Raises:
            AppNotFoundError: If app is not found.
        """
        data = self._read()
        apps = data.get("apps", [])

        for i, app in enumerate(apps):
            if app.get("id") == app_id:
                apps[i].update(updates)
                apps[i]["modified"] = datetime.now().isoformat()
                self._write(data)
                logger.info(f"Updated app in registry: {app_id}")
                return

        raise AppNotFoundError(f"PWA '{app_id}' not found in registry")

    def remove_app(self, app_id: str) -> dict[str, Any]:
        """Remove a PWA from the registry.

        Args:
            app_id: Application identifier.

        Returns:
            The removed app entry.

        Raises:
            AppNotFoundError: If app is not found.
        """
        data = self._read()
        apps = data.get("apps", [])

        for i, app in enumerate(apps):
            if app.get("id") == app_id:
                removed_app: dict[str, Any] = apps[i]
                data["apps"] = apps[:i] + apps[i + 1 :]
                self._write(data)
                logger.info(f"Removed app from registry: {app_id}")
                return removed_app

        raise AppNotFoundError(f"PWA '{app_id}' not found in registry")

    def list_handlers(self) -> list[dict[str, Any]]:
        """List all registered URL scheme handlers.

        Returns:
            List of handler entries.
        """
        data = self._read()
        handlers: list[dict[str, Any]] = data.get("handlers", [])
        return handlers

    def get_handler(self, scheme: str) -> dict[str, Any]:
        """Get a specific handler by scheme.

        Args:
            scheme: URL scheme (e.g., 'ff').

        Returns:
            Handler entry dictionary.

        Raises:
            RegistryError: If handler is not found.
        """
        handlers = self.list_handlers()
        for handler in handlers:
            if handler.get("scheme") == scheme:
                logger.debug(f"Found handler for scheme: {scheme}")
                return handler

        raise RegistryError(f"Handler for scheme '{scheme}' not found in registry")

    def add_handler(self, handler_data: dict[str, Any]) -> None:
        """Add a new URL scheme handler to the registry.

        Args:
            handler_data: Handler entry to add (must include 'scheme' field).

        Raises:
            RegistryError: If handler with same scheme already exists.
            ValueError: If handler_data is missing required fields.
        """
        if "scheme" not in handler_data:
            raise ValueError("handler_data must include 'scheme' field")

        scheme = handler_data["scheme"]

        # Check if handler already exists
        handlers = self.list_handlers()
        for handler in handlers:
            if handler.get("scheme") == scheme:
                raise RegistryError(f"Handler for scheme '{scheme}' already exists in registry")

        # Add handler to registry
        data = self._read()
        if "handlers" not in data:
            data["handlers"] = []
        data["handlers"].append(handler_data)
        self._write(data)
        logger.info(f"Added handler to registry: {scheme}")

    def remove_handler(self, scheme: str) -> dict[str, Any]:
        """Remove a URL scheme handler from the registry.

        Args:
            scheme: URL scheme.

        Returns:
            The removed handler entry.

        Raises:
            RegistryError: If handler is not found.
        """
        data = self._read()
        handlers = data.get("handlers", [])

        for i, handler in enumerate(handlers):
            if handler.get("scheme") == scheme:
                removed_handler: dict[str, Any] = handlers[i]
                data["handlers"] = handlers[:i] + handlers[i + 1 :]
                self._write(data)
                logger.info(f"Removed handler from registry: {scheme}")
                return removed_handler

        raise RegistryError(f"Handler for scheme '{scheme}' not found in registry")
