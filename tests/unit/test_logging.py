"""Tests for logging module."""

import pytest
import structlog


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
