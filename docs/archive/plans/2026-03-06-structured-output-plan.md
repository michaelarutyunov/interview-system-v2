# Structured Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add provider-native structured output (JSON mode) to LLM clients, eliminating malformed JSON errors and ~80 lines of repair code across 3 call sites.

**Architecture:** Optional `response_format` parameter on `LLMClient.complete()`. OpenAI-compatible clients pass it as a payload field; Anthropic translates it to tool_use. Call sites opt in per-request; free-text calls are unaffected.

**Tech Stack:** Python, httpx, Anthropic Messages API (tool_use), OpenAI-compatible chat/completions API (response_format)

**Design doc:** `docs/plans/2026-03-06-structured-output-design.md`

---

### Task 1: Add `response_format` to abstract `LLMClient.complete()`

**Files:**
- Modify: `src/llm/client.py:70-99` (abstract base class)

**Step 1: Add parameter to ABC**

In `src/llm/client.py`, add `response_format` to the abstract `complete()` signature:

```python
# Line 74-83: Add response_format parameter
@abstractmethod
async def complete(
    self,
    prompt: str,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    effort: Optional[str] = None,
    timeout: Optional[float] = None,
    session_id: Optional[str] = None,
    response_format: Optional[Dict[str, Any]] = None,
) -> LLMResponse:
```

Update the docstring to document the new parameter:

```
response_format: Optional structured output config. For OpenAI-compatible:
    {"type": "json_object"}. For Anthropic: {"type": "json_schema",
    "schema": {<JSON Schema>}}. None for free-text (default).
```

**Step 2: Commit**

```bash
git add src/llm/client.py
git commit -m "feat: add response_format parameter to LLMClient ABC"
```

---

### Task 2: Implement `response_format` in `OpenAICompatibleClient`

**Files:**
- Modify: `src/llm/client.py:421-617` (OpenAICompatibleClient.complete)

**Step 1: Write the failing test**

Create `tests/llm/test_structured_output.py`:

```python
"""Tests for structured output support in LLM clients."""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from src.llm.client import KimiClient, LLMResponse


@pytest.fixture
def kimi_client():
    """Create a KimiClient with test API key."""
    return KimiClient(
        model="test-model",
        temperature=0.3,
        max_tokens=500,
        timeout=10.0,
        client_type="slot_scoring",
        api_key="test-key",
    )


def _mock_openai_response(content: str) -> httpx.Response:
    """Build a fake httpx.Response with OpenAI-compatible JSON body."""
    return httpx.Response(
        status_code=200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "test-model",
        },
        request=httpx.Request("POST", "https://test"),
    )


@pytest.mark.asyncio
async def test_openai_json_mode_adds_response_format(kimi_client):
    """response_format is included in the API payload when provided."""
    captured_payload = {}

    async def mock_post(url, headers=None, json=None):
        captured_payload.update(json)
        return _mock_openai_response('{"key": "value"}')

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        await kimi_client.complete(
            prompt="test",
            response_format={"type": "json_object"},
        )

    assert captured_payload["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_openai_no_response_format_by_default(kimi_client):
    """response_format is NOT in payload when not provided."""
    captured_payload = {}

    async def mock_post(url, headers=None, json=None):
        captured_payload.update(json)
        return _mock_openai_response("free text response")

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        await kimi_client.complete(prompt="test")

    assert "response_format" not in captured_payload
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/llm/test_structured_output.py -v
```

Expected: FAIL — `complete()` doesn't accept `response_format` yet in concrete class.

**Step 3: Implement in OpenAICompatibleClient**

In `src/llm/client.py`, modify `OpenAICompatibleClient.complete()`:

1. Add `response_format` parameter to signature (line ~430):

```python
async def complete(
    self,
    prompt: str,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    effort: Optional[str] = None,
    timeout: Optional[float] = None,
    session_id: Optional[str] = None,
    response_format: Optional[Dict[str, Any]] = None,
) -> LLMResponse:
```

2. After building the payload dict (after line ~488), add:

```python
if response_format is not None:
    payload["response_format"] = response_format
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/llm/test_structured_output.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm/client.py tests/llm/test_structured_output.py
git commit -m "feat: implement response_format for OpenAI-compatible clients (Kimi/DeepSeek/Grok)"
```

---

### Task 3: Implement `response_format` in `AnthropicClient` via tool_use

**Files:**
- Modify: `src/llm/client.py:157-363` (AnthropicClient.complete)
- Modify: `tests/llm/test_structured_output.py`

**Step 1: Write the failing test**

Append to `tests/llm/test_structured_output.py`:

```python
from src.llm.client import AnthropicClient


@pytest.fixture
def anthropic_client():
    """Create an AnthropicClient with test API key."""
    return AnthropicClient(
        model="test-model",
        temperature=0.3,
        max_tokens=500,
        timeout=10.0,
        client_type="extraction",
        api_key="test-key",
    )


def _mock_anthropic_tool_response() -> httpx.Response:
    """Build a fake Anthropic tool_use response."""
    return httpx.Response(
        status_code=200,
        json={
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "structured_output",
                    "input": {"concepts": [], "relationships": []},
                }
            ],
            "model": "test-model",
            "usage": {"input_tokens": 15, "output_tokens": 25},
        },
        request=httpx.Request("POST", "https://test"),
    )


def _mock_anthropic_text_response(content: str) -> httpx.Response:
    """Build a fake Anthropic text response."""
    return httpx.Response(
        status_code=200,
        json={
            "content": [{"type": "text", "text": content}],
            "model": "test-model",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        },
        request=httpx.Request("POST", "https://test"),
    )


@pytest.mark.asyncio
async def test_anthropic_tool_use_payload(anthropic_client):
    """response_format with schema translates to tools + tool_choice in payload."""
    captured_payload = {}
    schema = {
        "type": "object",
        "properties": {"concepts": {"type": "array"}},
        "required": ["concepts"],
    }

    async def mock_post(url, headers=None, json=None):
        captured_payload.update(json)
        return _mock_anthropic_tool_response()

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        await anthropic_client.complete(
            prompt="test",
            response_format={"type": "json_schema", "schema": schema},
        )

    assert "tools" in captured_payload
    assert captured_payload["tools"][0]["name"] == "structured_output"
    assert captured_payload["tools"][0]["input_schema"] == schema
    assert captured_payload["tool_choice"] == {"type": "any"}


@pytest.mark.asyncio
async def test_anthropic_tool_use_extracts_input_as_json_string(anthropic_client):
    """Tool use response input dict is serialized to JSON string in content."""
    schema = {"type": "object", "properties": {"concepts": {"type": "array"}}}

    async def mock_post(url, headers=None, json=None):
        return _mock_anthropic_tool_response()

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        result = await anthropic_client.complete(
            prompt="test",
            response_format={"type": "json_schema", "schema": schema},
        )

    parsed = json.loads(result.content)
    assert parsed == {"concepts": [], "relationships": []}


@pytest.mark.asyncio
async def test_anthropic_no_tools_without_response_format(anthropic_client):
    """Without response_format, payload has no tools."""
    captured_payload = {}

    async def mock_post(url, headers=None, json=None):
        captured_payload.update(json)
        return _mock_anthropic_text_response("hello")

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        await anthropic_client.complete(prompt="test")

    assert "tools" not in captured_payload
    assert "tool_choice" not in captured_payload
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/llm/test_structured_output.py -v
```

Expected: FAIL — AnthropicClient doesn't handle `response_format` yet.

**Step 3: Implement in AnthropicClient**

In `src/llm/client.py`, modify `AnthropicClient.complete()`:

1. Add `response_format` parameter to signature (line ~164):

```python
async def complete(
    self,
    prompt: str,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    effort: Optional[str] = None,
    timeout: Optional[float] = None,
    session_id: Optional[str] = None,
    response_format: Optional[Dict[str, Any]] = None,
) -> LLMResponse:
```

2. After building the payload dict (after the `if system:` block, ~line 221), add:

```python
# Structured output via tool_use
if response_format is not None and "schema" in response_format:
    payload["tools"] = [
        {
            "name": "structured_output",
            "description": "Return structured data matching the schema",
            "input_schema": response_format["schema"],
        }
    ]
    payload["tool_choice"] = {"type": "any"}
```

3. Modify the content extraction block (line ~267-269). Replace:

```python
content = ""
if data.get("content"):
    content = data["content"][0].get("text", "")
```

With:

```python
content = ""
if data.get("content"):
    first_block = data["content"][0]
    if first_block.get("type") == "tool_use":
        # Structured output: serialize tool input to JSON string
        content = json.dumps(first_block.get("input", {}))
    else:
        content = first_block.get("text", "")
```

4. Add `import json` at the top of the file (if not already present).

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/llm/test_structured_output.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm/client.py tests/llm/test_structured_output.py
git commit -m "feat: implement structured output for Anthropic via tool_use"
```

---

### Task 4: Wire structured output into canonical slot service

**Files:**
- Modify: `src/services/canonical_slot_service.py:168-259` (_llm_propose_slots_batched)
- Modify: `src/services/canonical_slot_service.py:261-323` (_parse_batched_proposals)

**Step 1: Add `response_format` to the LLM call**

In `_llm_propose_slots_batched()`, modify the `self.llm.complete()` call at line ~251:

```python
response = await self.llm.complete(
    prompt=prompt,
    system=system,
    temperature=0.3,
    max_tokens=2000,
    timeout=60.0,
    response_format={"type": "json_object"},
)
```

**Step 2: Simplify `_parse_batched_proposals()`**

Remove the markdown fence stripping (lines 276-284). The method becomes:

```python
def _parse_batched_proposals(self, raw_response: str) -> Dict[str, List[Dict]]:
    """Parse batched LLM JSON response into per-type proposal lists.

    Args:
        raw_response: JSON string from LLM (guaranteed valid by structured output)

    Returns:
        Map of node_type → List[proposal dicts] (slot_name, description, surface_node_ids)

    Raises:
        ValueError: If response has unexpected structure
    """
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON from batched slot discovery LLM: {e}\n"
            f"Raw response: {raw_response[:500]}"
        )

    if not isinstance(data, dict) or "groupings" not in data:
        raise ValueError(
            f'Expected {{"groupings": {{...}}}} structure, '
            f"got: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
        )

    groupings = data["groupings"]
    if not isinstance(groupings, dict):
        raise ValueError(
            f"groupings must be a dict, got {type(groupings).__name__}"
        )

    result: Dict[str, List[Dict]] = {}
    for node_type, type_data in groupings.items():
        if not isinstance(type_data, dict) or "proposed_slots" not in type_data:
            raise ValueError(
                f"node_type '{node_type}' missing 'proposed_slots' key"
            )
        proposals = type_data["proposed_slots"]
        if not isinstance(proposals, list):
            raise ValueError(f"proposed_slots for '{node_type}' must be a list")
        for i, proposal in enumerate(proposals):
            for key in ("slot_name", "description", "surface_node_ids"):
                if key not in proposal:
                    raise ValueError(
                        f"Proposal {i} for '{node_type}' missing required key '{key}'"
                    )
        result[node_type] = proposals

    return result
```

**Step 3: Run existing tests**

```bash
uv run pytest tests/ -k "slot" -v
```

Expected: PASS (no tests mock the raw JSON format)

**Step 4: Commit**

```bash
git add src/services/canonical_slot_service.py
git commit -m "feat: wire structured output into canonical slot service, remove fence stripping"
```

---

### Task 5: Wire structured output into extraction service

**Files:**
- Modify: `src/services/extraction_service.py:310` (LLM call)
- Modify: `src/llm/prompts/extraction.py:258-355` (parse function + repair helpers)

**Step 1: Add `response_format` to the LLM call**

In `extraction_service.py`, modify the `self.llm.complete()` call at line ~310:

```python
response = await self.llm.complete(
    prompt=user_prompt,
    system=system_prompt,
    temperature=0.4,
    max_tokens=4000,
    response_format={"type": "json_object"},
)
```

**Step 2: Simplify `parse_extraction_response()` and remove repair helpers**

In `src/llm/prompts/extraction.py`:

1. Delete `_strip_markdown_fences()` (lines 258-267)
2. Delete `_repair_json()` (lines 270-306)
3. Simplify `parse_extraction_response()`:

```python
def parse_extraction_response(response_text: str) -> Dict[str, Any]:
    """
    Parse LLM extraction response into structured data.

    Args:
        response_text: JSON string from LLM (guaranteed valid by structured output)

    Returns:
        Parsed dict with concepts, relationships

    Raises:
        ValueError: If response is not valid JSON or has unexpected structure
    """
    import json

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in extraction response: {e}")

    if not isinstance(data, dict):
        raise ValueError("Extraction response must be a JSON object")

    return {
        "concepts": data.get("concepts", []),
        "relationships": data.get("relationships", []),
    }
```

**Step 3: Run existing tests**

```bash
uv run pytest tests/ -k "extract" -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/services/extraction_service.py src/llm/prompts/extraction.py
git commit -m "feat: wire structured output into extraction service, remove JSON repair code"
```

---

### Task 6: Wire structured output into batch signal detector

**Files:**
- Modify: `src/signals/llm/batch_detector.py:282` (LLM call)
- Modify: `src/signals/llm/batch_detector.py:202-241` (_parse_json_response)

**Step 1: Add `response_format` to the LLM call**

In `batch_detector.py`, modify the `self.llm_client.complete()` call at line ~282:

```python
response = await self.llm_client.complete(
    prompt=prompt,
    response_format={"type": "json_object"},
)
```

**Step 2: Simplify `_parse_json_response()`**

Replace the entire method:

```python
@staticmethod
def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response.

    Args:
        text: JSON string from LLM (guaranteed valid by structured output)

    Returns:
        Parsed dict of signal scores

    Raises:
        json.JSONDecodeError: If response is not valid JSON
    """
    return json.loads(text)
```

**Step 3: Run existing tests**

```bash
uv run pytest tests/ -k "signal" -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/signals/llm/batch_detector.py
git commit -m "feat: wire structured output into batch signal detector, remove JSON repair code"
```

---

### Task 7: Run full test suite and lint

**Step 1: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests PASS

**Step 2: Lint and format**

```bash
ruff check . --fix && ruff format .
```

**Step 3: Check pyright diagnostics**

Use LSP to check for type errors in modified files:
- `src/llm/client.py`
- `src/services/canonical_slot_service.py`
- `src/services/extraction_service.py`
- `src/signals/llm/batch_detector.py`
- `src/llm/prompts/extraction.py`

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "chore: lint and type fixes for structured output"
```

---

### Task 8: Integration smoke test

**Step 1: Run a simulation to verify end-to-end**

```bash
uv run python scripts/run_simulation.py headphones_mec baseline_cooperative 3
```

Expected: Completes 3 turns without JSON parse errors. Check logs for:
- No `extraction_json_repaired` warnings
- No `Scoring JSON repaired` warnings
- Slot discovery completes normally

**Step 2: Final commit and push**

```bash
bd sync
git push
```
