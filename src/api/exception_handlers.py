"""
Global exception handlers for FastAPI.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

import structlog

from src.core.exceptions import (
    InterviewSystemError,
    ConfigurationError,
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    SessionNotFoundError,
    SessionCompletedError,
    ValidationError,
)

log = structlog.get_logger(__name__)


def setup_exception_handlers(app: FastAPI):
    """Register all exception handlers with the FastAPI app."""

    @app.exception_handler(InterviewSystemError)
    async def interview_system_error_handler(
        request: Request,
        exc: InterviewSystemError,
    ) -> JSONResponse:
        """Handle all custom InterviewSystemError exceptions."""
        log_ctx = log.bind(
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
        )

        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        if isinstance(exc, SessionNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, SessionCompletedError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, LLMTimeoutError):
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        elif isinstance(exc, LLMRateLimitError):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS

        log_ctx.warning(
            "request_error",
            message=exc.message,
            status_code=status_code,
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "type": type(exc).__name__,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(
        request: Request,
        exc: ConfigurationError,
    ) -> JSONResponse:
        """Handle configuration errors."""
        log.error(
            "configuration_error",
            path=request.url.path,
            message=exc.message,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "ConfigurationError",
                    "message": "Server configuration error",
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle all unhandled exceptions."""
        log_ctx = log.bind(
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
        )

        log_ctx.error(
            "unhandled_exception",
            message=str(exc),
            exc_info=exc,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred",
                }
            },
        )
