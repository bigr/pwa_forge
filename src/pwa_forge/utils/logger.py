"""Logging configuration for PWA Forge."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Final

__all__ = ["setup_logging", "get_logger"]

# Default log format
LOG_FORMAT: Final[str] = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    console: bool = True,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure logging for the application.

    Args:
        level: Console logging level (default: INFO).
        log_file: Optional path to log file. If provided, file logging is enabled.
        console: Whether to enable console logging (default: True).
        file_level: File logging level (default: DEBUG).
    """
    root_logger = logging.getLogger("pwa_forge")
    root_logger.setLevel(logging.DEBUG)  # Capture all levels, handlers will filter

    # Remove existing handlers
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Ensure parent directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__ of the calling module).

    Returns:
        Configured logger instance.
    """
    # Ensure the name is under the pwa_forge namespace
    if not name.startswith("pwa_forge"):
        name = f"pwa_forge.{name}"
    return logging.getLogger(name)
