"""Unit tests for logging utilities."""

from __future__ import annotations

import logging
from pathlib import Path

from pwa_forge.utils import logger


class TestSetupLogging:
    """Test logging configuration."""

    def test_setup_logging_default(self) -> None:
        """Test default logging setup."""
        logger.setup_logging()
        log = logging.getLogger("pwa_forge")
        assert log.level == logging.DEBUG
        assert len(log.handlers) == 1  # Console handler only
        assert isinstance(log.handlers[0], logging.StreamHandler)

    def test_setup_logging_with_file(self, tmp_path: Path) -> None:
        """Test logging setup with file output."""
        log_file = tmp_path / "test.log"
        logger.setup_logging(log_file=log_file)
        log = logging.getLogger("pwa_forge")
        assert len(log.handlers) == 2  # Console and file handlers
        assert log_file.exists()

    def test_setup_logging_without_console(self, tmp_path: Path) -> None:
        """Test logging setup without console output."""
        log_file = tmp_path / "test.log"
        logger.setup_logging(console=False, log_file=log_file)
        log = logging.getLogger("pwa_forge")
        assert len(log.handlers) == 1  # File handler only
        assert isinstance(log.handlers[0], logging.FileHandler)

    def test_setup_logging_console_only(self) -> None:
        """Test logging setup with console only (no file)."""
        logger.setup_logging(console=True, log_file=None)
        log = logging.getLogger("pwa_forge")
        assert len(log.handlers) == 1  # Console handler only
        assert isinstance(log.handlers[0], logging.StreamHandler)

    def test_setup_logging_custom_levels(self, tmp_path: Path) -> None:
        """Test logging with custom levels."""
        log_file = tmp_path / "test.log"
        logger.setup_logging(level=logging.WARNING, file_level=logging.ERROR, log_file=log_file)
        log = logging.getLogger("pwa_forge")
        console_handler = [h for h in log.handlers if isinstance(h, logging.StreamHandler)][0]
        file_handler = [h for h in log.handlers if isinstance(h, logging.FileHandler)][0]
        assert console_handler.level == logging.WARNING
        assert file_handler.level == logging.ERROR

    def test_setup_logging_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test that logging creates parent directories for log file."""
        log_file = tmp_path / "nested" / "dirs" / "test.log"
        logger.setup_logging(log_file=log_file)
        assert log_file.parent.exists()
        assert log_file.exists()

    def test_setup_logging_clears_existing_handlers(self) -> None:
        """Test that setup_logging removes previous handlers."""
        # First setup
        logger.setup_logging()
        log = logging.getLogger("pwa_forge")
        initial_count = len(log.handlers)
        # Second setup
        logger.setup_logging()
        assert len(log.handlers) == initial_count  # Not doubled


class TestGetLogger:
    """Test logger retrieval."""

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns a Logger instance."""
        log = logger.get_logger("test_module")
        assert isinstance(log, logging.Logger)

    def test_get_logger_adds_namespace(self) -> None:
        """Test that logger names are prefixed with pwa_forge."""
        log = logger.get_logger("test_module")
        assert log.name == "pwa_forge.test_module"

    def test_get_logger_preserves_namespace(self) -> None:
        """Test that existing pwa_forge namespace is not duplicated."""
        log = logger.get_logger("pwa_forge.test_module")
        assert log.name == "pwa_forge.test_module"

    def test_get_logger_same_name_returns_same_instance(self) -> None:
        """Test that the same logger name returns the same instance."""
        log1 = logger.get_logger("test_module")
        log2 = logger.get_logger("test_module")
        assert log1 is log2
