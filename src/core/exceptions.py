"""
Custom exception hierarchy for the interview system.

All application exceptions inherit from InterviewSystemError.
"""


class InterviewSystemError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(InterviewSystemError):
    """Invalid or missing configuration."""

    pass


# =============================================================================
# LLM Errors
# =============================================================================


class LLMError(InterviewSystemError):
    """Base for LLM-related errors."""

    pass


class LLMTimeoutError(LLMError):
    """LLM call timed out."""

    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    pass


class LLMContentFilterError(LLMError):
    """Content filtered by LLM provider."""

    pass


class LLMResponseParseError(LLMError):
    """Failed to parse LLM response."""

    pass


class LLMInvalidResponseError(LLMError):
    """LLM returned invalid or unexpected response."""

    pass


# =============================================================================
# Session Errors
# =============================================================================


class SessionError(InterviewSystemError):
    """Session-related error."""

    pass


class SessionNotFoundError(SessionError):
    """Session does not exist."""

    pass


class SessionCompletedError(SessionError):
    """Attempted operation on completed session."""

    pass


class SessionAbandonedError(SessionError):
    """Session was abandoned."""

    pass


# =============================================================================
# Extraction Errors
# =============================================================================


class ExtractionError(InterviewSystemError):
    """Failed to extract concepts from response."""

    pass


class ValidationError(InterviewSystemError):
    """Input validation failed."""

    pass


# =============================================================================
# Graph Errors
# =============================================================================


class GraphError(InterviewSystemError):
    """Knowledge graph operation error."""

    pass


class NodeNotFoundError(GraphError):
    """Node does not exist."""

    pass


class DuplicateNodeError(GraphError):
    """Attempted to create duplicate node."""

    pass


# =============================================================================
# Scoring Errors
# =============================================================================


class ScoringError(InterviewSystemError):
    """Base for scoring-related errors."""

    pass


class ScorerFailureError(ScoringError):
    """Raised when a scorer fails and interview should terminate (MVP fail-fast).

    For MVP single-interview mode, any scorer failure terminates the interview
    immediately with a clear error message. This ensures immediate visibility
    of scoring issues during testing.

    See ADR-009 for rationale and migration path to production resilience.
    """

    pass
