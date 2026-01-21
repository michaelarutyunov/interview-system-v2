# Logging Standards

## Configuration

All logging uses `structlog` with context-bound loggers.

```python
from src.core.logging import get_logger

log = get_logger(__name__)
```

## Event Logging Standards

| Event | Level | Required Fields |
|-------|-------|-----------------|
| Request received | INFO | endpoint, method, session_id |
| LLM call start | DEBUG | provider, model, prompt_tokens |
| LLM call complete | INFO | provider, model, latency_ms, tokens_used |
| LLM call failed | ERROR | provider, model, error_type, error_message |
| Extraction complete | INFO | session_id, turn_number, concept_count |
| Strategy selected | INFO | session_id, turn_number, strategy, scores |
| Session created | INFO | session_id, methodology, concept_id |
| Session completed | INFO | session_id, turns, coverage, duration_seconds |
| Database query | DEBUG | query, table, rows_affected |
| Error | ERROR | error_type, error_message, context |

## Binding Context

Always bind relevant context to loggers.

```python
# Bind request-scoped context
from src.core.logging import bind_context

bind_context(session_id=session.id, request_id=request_id)

# Or bind to a specific logger instance
log = log.bind(session_id=session.id, turn_number=turn.number)
```

## Level Guidelines

- **DEBUG**: Detailed diagnostics (database queries, LLM prompts, token counts)
- **INFO**: Normal operations (requests, responses, completions)
- **WARNING**: Recoverable issues (fallbacks, retries, deprecated usage)
- **ERROR**: Errors that affect operation (API failures, validation errors)
- **CRITICAL**: System-wide failures (service unavailable, data corruption)

## Do Not Log

- Passwords, API keys, or secrets
- Large payloads (log size/offset instead)
- PII in production (anonymize or hash)
- Full request bodies in production (log metadata only)

## Examples

### Basic Logging

```python
from src.core.logging import get_logger

log = get_logger(__name__)

# Info level - normal operations
log.info("session_created", session_id=session.id, methodology=session.methodology)

# Error level - with context
log.error(
    "llm_call_failed",
    provider="openai",
    model="gpt-4",
    error_type=str(type(e).__name__),
    error_message=str(e),
)
```

### With Context Binding

```python
from src.core.logging import bind_context, get_logger

log = get_logger(__name__)

# Bind request-scoped context
bind_context(session_id=session.id, user_id=user.id)

# All subsequent logs include this context
log.info("processing_turn", turn_number=turn.number)

# Clear context when done
clear_context()
```

### Structured Data

```python
# Always log structured data as keyword arguments
log.info(
    "extraction_complete",
    session_id=session.id,
    turn_number=turn.number,
    concept_count=len(concepts),
    concepts=[c.name for c in concepts],
)

# NOT: log.info(f"Extraction complete with {len(concepts)} concepts")
```

## Testing Logging

When testing code that logs, use `caplog` or structlog's testing utilities:

```python
import structlog
from src.core.logging import configure_logging, get_logger

def test_something_logs_correctly(caplog):
    configure_logging()
    log = get_logger("test")

    log.info("test_event", key="value")

    # Assert log was called
    assert any("test_event" in record.getMessage() for record in caplog.records)
```
