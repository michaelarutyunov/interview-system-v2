"""
Structured logging configuration using structlog.

Provides consistent, structured logging across the application with:
- JSON output in production
- Pretty console output in development
- Context binding for request tracing
- File output to logs/ directory (session-based rotation)
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

import structlog
from structlog.typing import Processor

from src.core.config import settings


def _cull_old_logs(logs_dir: Path, keep: int) -> None:
    """Delete old log files, keeping only the N most recent.

    Args:
        logs_dir: Directory containing log files
        keep: Number of recent log files to retain
    """
    # Find all interview_*.log files
    log_files = sorted(
        logs_dir.glob("interview_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Remove old files beyond the keep limit
    for old_file in log_files[keep:]:
        try:
            os.remove(old_file)
        except OSError:
            pass  # Ignore permission errors, etc.


def configure_logging(log_sessions_to_keep: int = 5) -> None:
    """Configure structlog for the application.

    Call this once at application startup, before any logging.

    Creates a new timestamped log file per session and automatically
    culls old logs, keeping only the most recent N sessions.

    Args:
        log_sessions_to_keep: Number of recent session logs to retain (default: 5)

    Outputs:
        - Console (colored in dev, plain in production)
        - File: logs/interview_YYYYMMDD_HHMMSS.log
    """

    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Cull old logs before creating new one (keep-1 to make room for new file)
    _cull_old_logs(logs_dir, keep=log_sessions_to_keep - 1)

    # Create timestamped log file for this session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"interview_{timestamp}.log"

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

    # Configure stdlib logging for file output
    # Clear any existing handlers first (needed for reconfiguration in tests/long-running processes)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    root_logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    # File handler (new file per session)
    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(file_handler)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
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
    """Clear all bound context variables from the logging context.

    Removes all request-scoped context variables (like session_id, request_id)
    that were bound via bind_context. Call this after async task completion to
    prevent context leakage between requests.
    """
    structlog.contextvars.clear_contextvars()
