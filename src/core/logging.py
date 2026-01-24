"""
Structured logging configuration using structlog.

Provides consistent, structured logging across the application with:
- JSON output in production
- Pretty console output in development
- Context binding for request tracing
"""

import logging
from typing import List

import structlog
from structlog.typing import Processor

from src.core.config import settings


def configure_logging() -> None:
    """
    Configure structlog for the application.

    Call this once at application startup, before any logging.
    """

    # Shared processors for all outputs
    shared_processors: List[Processor] = [
        # Add context from contextvars (for request-scoped context)
        structlog.contextvars.merge_contextvars,
        # Add log level to event dict
        structlog.processors.add_log_level,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso"),
        # Add extra attributes from stdlib logger
        structlog.stdlib.ExtraAdder(),
    ]

    if settings.debug:
        # Development: pretty console output with colors
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]
    else:
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            # Format exceptions as dicts
            structlog.processors.dict_tracebacks,
            # Render as JSON
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Bound structlog logger

    Usage:
        from src.core.logging import get_logger

        log = get_logger(__name__)
        log.info("something_happened", key="value")
    """
    return structlog.get_logger(name)


def bind_context(**kwargs) -> None:
    """
    Bind context variables that will be included in all subsequent logs.

    Useful for request-scoped context like session_id:

        bind_context(session_id=session.id, request_id=request_id)

    Context is cleared when the async task completes.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
