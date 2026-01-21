"""Tests for logging configuration."""

import logging
import pytest
import structlog

from src.core.logging import configure_logging, get_logger


class TestLoggingConfiguration:
    """Tests for logging setup."""

    def test_configure_logging_sets_up_structlog(self):
        """configure_logging() sets up structlog properly."""
        configure_logging()
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_get_logger_returns_bound_logger(self):
        """get_logger() returns a BoundLogger (or proxy)."""
        logger = get_logger("test_module")
        # get_logger returns a BoundLoggerLazyProxy which acts as a BoundLogger
        assert logger is not None
        # Verify it has the logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_logger_can_bind_context(self):
        """Logger can bind context variables."""
        logger = get_logger("test")
        bound_logger = logger.bind(session_id="test-123", turn_number=5)
        bound_logger.info("test_message")


def test_configure_logging():
    """Logging configuration runs without error."""
    from src.core.logging import configure_logging

    # Should not raise
    configure_logging()


def test_get_logger():
    """get_logger returns a bound logger."""
    from src.core.logging import configure_logging, get_logger

    configure_logging()
    log = get_logger("test")

    assert log is not None
    # Should be callable for logging
    assert callable(log.info)
    assert callable(log.error)


def test_logger_bind():
    """Logger can bind context."""
    from src.core.logging import configure_logging, get_logger

    configure_logging()
    log = get_logger("test")

    # Bind should return a new logger
    bound = log.bind(session_id="test-123")
    assert bound is not None


def test_context_binding():
    """Context variables can be bound and cleared."""
    from src.core.logging import configure_logging, bind_context, clear_context

    configure_logging()

    # Should not raise
    bind_context(request_id="req-123")
    clear_context()
