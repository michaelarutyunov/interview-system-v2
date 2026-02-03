"""
Unit tests for global exception handlers.
"""

from unittest.mock import Mock
from fastapi import status, FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api.exception_handlers import setup_exception_handlers
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


class TestExceptionHandlerSetup:
    """Tests for exception handler setup function."""

    def test_setup_exception_handlers_registers_handlers(self):
        """Verify setup_exception_handlers registers handlers with FastAPI app."""
        test_app = Mock(spec=FastAPI)
        setup_exception_handlers(test_app)

        # Verify exception_handler was called for each exception type
        assert test_app.exception_handler.called

        # Get the exception types that were registered
        registered_exceptions = []
        for call in test_app.exception_handler.call_args_list:
            args, kwargs = call
            registered_exceptions.append(args[0])

        # Should have handlers for InterviewSystemError, ConfigurationError, and Exception
        assert InterviewSystemError in registered_exceptions
        assert ConfigurationError in registered_exceptions
        assert Exception in registered_exceptions


class TestInterviewSystemErrorHandler:
    """Tests for InterviewSystemError handler."""

    @pytest.mark.asyncio
    async def test_session_not_found_returns_404(self):
        """SessionNotFoundError should return 404 status."""
        # Import the handler function
        from src.api.exception_handlers import setup_exception_handlers

        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-404")
        async def trigger_404():
            raise SessionNotFoundError("Test session not found")

        client = TestClient(test_app)
        response = client.get("/test-404")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "SessionNotFoundError"
        assert data["error"]["message"] == "Test session not found"

    @pytest.mark.asyncio
    async def test_validation_error_returns_400(self):
        """ValidationError should return 400 status."""
        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-400")
        async def trigger_400():
            raise ValidationError("Invalid input data")

        client = TestClient(test_app)
        response = client.get("/test-400")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"]["type"] == "ValidationError"
        assert data["error"]["message"] == "Invalid input data"

    @pytest.mark.asyncio
    async def test_session_completed_returns_400(self):
        """SessionCompletedError should return 400 status."""
        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-completed")
        async def trigger_completed():
            raise SessionCompletedError("Session is already completed")

        client = TestClient(test_app)
        response = client.get("/test-completed")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"]["type"] == "SessionCompletedError"

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_504(self):
        """LLMTimeoutError should return 504 status."""
        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-timeout")
        async def trigger_timeout():
            raise LLMTimeoutError("LLM request timed out")

        client = TestClient(test_app)
        response = client.get("/test-timeout")

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        data = response.json()
        assert data["error"]["type"] == "LLMTimeoutError"

    @pytest.mark.asyncio
    async def test_llm_rate_limit_returns_429(self):
        """LLMRateLimitError should return 429 status."""
        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-rate-limit")
        async def trigger_rate_limit():
            raise LLMRateLimitError("Rate limit exceeded")

        client = TestClient(test_app)
        response = client.get("/test-rate-limit")

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert data["error"]["type"] == "LLMRateLimitError"

    @pytest.mark.asyncio
    async def test_generic_llm_error_returns_500(self):
        """Generic LLMError should return 500 status."""
        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-llm-error")
        async def trigger_llm_error():
            raise LLMError("Generic LLM error")

        client = TestClient(test_app)
        response = client.get("/test-llm-error")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"]["type"] == "LLMError"


class TestConfigurationErrorHandler:
    """Tests for ConfigurationError handler."""

    @pytest.mark.asyncio
    async def test_configuration_error_returns_500_with_generic_message(self):
        """ConfigurationError should return 500 status with generic message."""
        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-config-error")
        async def trigger_config_error():
            raise ConfigurationError("Secret API key missing")

        client = TestClient(test_app)
        response = client.get("/test-config-error")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"]["type"] == "ConfigurationError"
        # Should NOT expose the actual error message for security
        assert data["error"]["message"] == "Server configuration error"
        assert "Secret" not in data["error"]["message"]


class TestGenericExceptionHandler:
    """Tests for generic exception handler."""

    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_500_with_generic_message(self):
        """Unhandled exceptions should return 500 with generic message."""
        test_app = FastAPI(debug=False)  # Disable debug to test exception handler
        setup_exception_handlers(test_app)

        @test_app.get("/test-unhandled")
        async def trigger_unhandled():
            raise ValueError("Something unexpected happened")

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/test-unhandled")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"]["type"] == "InternalServerError"
        assert data["error"]["message"] == "An unexpected error occurred"
        # Should NOT expose the actual exception message
        assert "unexpected happened" not in str(data)


class TestErrorResponseFormat:
    """Tests for error response format consistency."""

    @pytest.mark.asyncio
    async def test_error_response_has_required_fields(self):
        """All error responses should have type and message fields."""
        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-format")
        async def trigger_error():
            raise SessionNotFoundError("Test error")

        client = TestClient(test_app)
        response = client.get("/test-format")

        data = response.json()
        assert "error" in data
        assert "type" in data["error"]
        assert "message" in data["error"]
        assert isinstance(data["error"]["type"], str)
        assert isinstance(data["error"]["message"], str)

    @pytest.mark.asyncio
    async def test_custom_exception_message_preserved(self):
        """Custom exception messages should be preserved in response."""
        test_app = FastAPI()
        setup_exception_handlers(test_app)

        @test_app.get("/test-message")
        async def trigger_error():
            raise SessionNotFoundError("Session abc123 not found in database")

        client = TestClient(test_app)
        response = client.get("/test-message")

        data = response.json()
        assert "Session abc123 not found" in data["error"]["message"]
