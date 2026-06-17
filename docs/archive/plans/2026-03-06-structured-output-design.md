# Structured Output for LLM Clients

**Date:** 2026-03-06
**Status:** Approved

## Context

Three LLM call sites produce JSON but rely on prompt instructions ("respond with ONLY valid JSON") plus defensive repair code (markdown fence stripping, missing comma regex, truncation recovery). This is fragile and adds latency from repair attempts and retries on malformed output.

## Decision

Add optional `response_format` parameter to `LLMClient.complete()` to enable provider-native structured output.

## Design

### API Change

```python
# LLMClient.complete() gains one optional parameter:
async def complete(
    self,
    prompt: str,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    effort: Optional[str] = None,
    timeout: Optional[float] = None,
    session_id: Optional[str] = None,
    response_format: Optional[Dict[str, Any]] = None,  # NEW
) -> LLMResponse:
```

### Provider Implementations

**OpenAI-Compatible (Kimi, DeepSeek, Grok):**
- When `response_format` provided, add it directly to API payload
- Supports `{"type": "json_object"}` (JSON mode — guaranteed valid JSON)
- No schema enforcement at API level; validation stays in application code

**Anthropic:**
- When `response_format` provided with a `schema` key, translate to tool_use:
  ```python
  payload["tools"] = [{
      "name": "structured_output",
      "description": "Return structured data",
      "input_schema": response_format["schema"]
  }]
  payload["tool_choice"] = {"type": "any"}
  ```
- Extract `content[0]["input"]` (dict) from tool_use response block
- Serialize to JSON string via `json.dumps()` for uniform `LLMResponse.content`

### Call Sites

| Call Site | Client Type | Schema |
|-----------|-------------|--------|
| `extraction_service.py` | `extraction` | concepts + relationships |
| `canonical_slot_service.py` | `slot_scoring` | groupings → proposed_slots |
| `batch_detector.py` | `signal_scoring` | signal_name → {score, rationale} |

Free-text call sites (question_service, synthetic_service) are unaffected — they don't pass `response_format`.

### JSON Repair Code Cleanup

After structured output is wired, the following repair code becomes dead:

| File | Code | Purpose |
|------|------|---------|
| `src/llm/prompts/extraction.py` | `_strip_markdown_fences()`, `_repair_json()` | Fence strip, comma repair, truncation recovery |
| `src/services/canonical_slot_service.py` | Lines 277-284 in `_parse_batched_proposals()` | Fence strip |
| `src/signals/llm/batch_detector.py` | Lines 210-237 in `_parse_json_response()` | Fence strip, comma repair, truncation recovery |

Structural validation (checking required keys, expected types) is retained.

## Downstream Impact

- `LLMResponse.content`: Still a string. Guaranteed valid JSON for structured calls.
- `LLMResponse.raw_response`: Shape changes for Anthropic tool_use responses, but **never read** in codebase.
- Free-text calls: Completely unaffected (no `response_format` passed).
- Tests: No existing tests mock malformed JSON. No breakage expected.

## Consequences

**Positive:**
- Eliminates malformed JSON errors and repair overhead
- Simpler parsing code (remove ~80 lines of repair logic)
- Potentially faster responses (constrained decoding)
- Enables future schema enforcement (Anthropic tool_use validates against schema)

**Negative:**
- Anthropic tool_use adds ~10-20 tokens of overhead per call (tool definition)
- Provider-specific implementation divergence in client code

## Alternatives Considered

1. **Shared JSON repair utility** — Consolidates repair but doesn't solve root cause
2. **response_format at client init level** — Too rigid; some calls on same client need text output
3. **Separate StructuredLLMClient subclass** — Over-engineering for one optional parameter
