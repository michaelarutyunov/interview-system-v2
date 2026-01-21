"""Tests for exception hierarchy."""

import pytest


def test_exception_hierarchy():
    """All exceptions inherit from InterviewSystemError."""
    from src.core.exceptions import (
        InterviewSystemError,
        ConfigurationError,
        LLMError,
        LLMTimeoutError,
        SessionError,
        SessionNotFoundError,
        ExtractionError,
        GraphError,
    )

    assert issubclass(ConfigurationError, InterviewSystemError)
    assert issubclass(LLMError, InterviewSystemError)
    assert issubclass(LLMTimeoutError, LLMError)
    assert issubclass(SessionError, InterviewSystemError)
    assert issubclass(SessionNotFoundError, SessionError)
    assert issubclass(ExtractionError, InterviewSystemError)
    assert issubclass(GraphError, InterviewSystemError)


def test_exceptions_can_be_raised():
    """Exceptions can be raised and caught."""
    from src.core.exceptions import SessionNotFoundError

    with pytest.raises(SessionNotFoundError):
        raise SessionNotFoundError("Session test-123 not found")
