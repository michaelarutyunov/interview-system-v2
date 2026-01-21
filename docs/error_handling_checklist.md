# Error Handling Checklist

This checklist ensures proper error handling across the interview system v2 application.

## API Layer Error Handling

### Exception Handlers

- [x] Global exception handlers registered in `src/main.py`
- [x] `InterviewSystemError` handler with appropriate status codes
- [x] `ConfigurationError` handler (500 - generic message)
- [x] Generic exception handler (500 - generic message)

### Status Code Mapping

- [x] `SessionNotFoundError` → 404 Not Found
- [x] `ValidationError` → 400 Bad Request
- [x] `SessionCompletedError` → 400 Bad Request
- [x] `LLMTimeoutError` → 504 Gateway Timeout
- [x] `LLMRateLimitError` → 429 Too Many Requests
- [x] Other `InterviewSystemError` → 500 Internal Server Error
- [x] `ConfigurationError` → 500 Internal Server Error
- [x] Unhandled exceptions → 500 Internal Server Error

### Response Format

All error responses follow this structure:

```json
{
  "error": {
    "type": "ExceptionClassName",
    "message": "Human-readable error message"
  }
}
```

- [x] All errors include `type` field
- [x] All errors include `message` field
- [x] Configuration errors return generic message (security)
- [x] Custom exceptions preserve their message

## Service Layer Error Handling

### Session Service

- [ ] Raises `SessionNotFoundError` when session doesn't exist
- [ ] Raises `SessionCompletedError` when modifying completed session
- [ ] Raises `ValidationError` for invalid input

### Extraction Service

- [ ] Raises `ExtractionError` on extraction failures
- [ ] Raises `LLMError` on LLM API failures
- [ ] Raises `LLMTimeoutError` on timeouts
- [ ] Raises `LLMRateLimitError` on rate limits

### Question Service

- [ ] Raises `ValidationError` for invalid question data
- [ ] Raises `ExtractionError` on concept extraction failures

### Graph Service

- [ ] Raises `GraphError` on database failures
- [ ] Raises `NodeNotFoundError` when node doesn't exist
- [ ] Raises `DuplicateNodeError` on duplicate creation

## Logging Requirements

### Error Logging

- [x] All exceptions logged with context
- [x] Logs include request path and method
- [x] Logs include exception type
- [x] Logs include error message
- [x] Unhandled exceptions include stack trace (`exc_info=True`)
- [x] Configuration errors logged at ERROR level
- [x] Handled exceptions logged at WARNING level

### Log Context

Each error log should include:
- [x] `path`: Request URL path
- [x] `method`: HTTP method
- [x] `error_type`: Exception class name
- [x] `message`: Error message
- [x] `status_code`: HTTP status code

## Exception Hierarchy

### Base Exception

- [x] `InterviewSystemError`: Base for all custom exceptions
  - [x] Has `message` attribute
  - [x] Inherits from `Exception`

### Configuration Errors

- [x] `ConfigurationError`: Invalid or missing configuration

### LLM Errors

- [x] `LLMError`: Base for LLM-related errors
  - [x] `LLMTimeoutError`: LLM call timed out
  - [x] `LLMRateLimitError`: Rate limit exceeded
  - [x] `LLMContentFilterError`: Content filtered
  - [x] `LLMResponseParseError`: Failed to parse response
  - [x] `LLMInvalidResponseError`: Invalid response

### Session Errors

- [x] `SessionError`: Base for session errors
  - [x] `SessionNotFoundError`: Session doesn't exist
  - [x] `SessionCompletedError`: Session is completed
  - [x] `SessionAbandonedError`: Session was abandoned

### Extraction Errors

- [x] `ExtractionError`: Failed to extract concepts
- [x] `ValidationError`: Input validation failed

### Graph Errors

- [x] `GraphError`: Knowledge graph operation error
  - [x] `NodeNotFoundError`: Node doesn't exist
  - [x] `DuplicateNodeError`: Duplicate node

## Testing Checklist

### Unit Tests

- [x] Test all exception handlers return correct status codes
- [x] Test error response format consistency
- [x] Test custom exception messages are preserved
- [x] Test configuration errors return generic message
- [x] Test unhandled exceptions return generic message

### Integration Tests

- [ ] Test error handling in session creation
- [ ] Test error handling in session retrieval
- [ ] Test error handling in turn submission
- [ ] Test error handling in question generation
- [ ] Test error handling in concept operations

## Security Considerations

- [x] Configuration errors don't expose internal details
- [x] Unhandled exceptions don't expose stack traces to clients
- [x] Error messages are user-friendly
- [x] Sensitive information not leaked in error responses

## Client Response Guidelines

### 400 Bad Request

```json
{
  "error": {
    "type": "ValidationError",
    "message": "Invalid input: field 'question' is required"
  }
}
```

### 404 Not Found

```json
{
  "error": {
    "type": "SessionNotFoundError",
    "message": "Session 'abc123' not found"
  }
}
```

### 429 Too Many Requests

```json
{
  "error": {
    "type": "LLMRateLimitError",
    "message": "Rate limit exceeded, please retry later"
  }
}
```

### 500 Internal Server Error

```json
{
  "error": {
    "type": "InternalServerError",
    "message": "An unexpected error occurred"
  }
}
```

## Monitoring

### Metrics to Track

- [ ] Error rate by exception type
- [ ] Error rate by endpoint
- [ ] LLM timeout rate
- [ ] LLM rate limit occurrences
- [ ] Validation error rate

### Alerts

- [ ] High error rate (> 5%)
- [ ] Configuration errors (should never occur in production)
- [ ] LLM rate limit spikes
- [ ] Unexpected exception spikes

## Implementation Status

**Phase 1 (Core Infrastructure)** - ✅ COMPLETE
- Exception hierarchy defined
- Global exception handlers implemented
- Basic error response format established
- Logging integration complete
- Unit tests for exception handlers

**Phase 2 (Service Layer)** - PENDING
- Implement error handling in all services
- Add integration tests for error scenarios
- Document service-specific error codes

**Phase 3 (Monitoring & Alerting)** - PENDING
- Set up error tracking metrics
- Configure alerts for critical errors
- Create error dashboards

---

Last updated: 2025-01-21
