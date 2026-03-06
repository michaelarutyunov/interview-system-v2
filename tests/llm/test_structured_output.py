"""Tests for structured output support in LLM clients."""

import json
import pytest
import httpx
from unittest.mock import patch

from src.llm.client import KimiClient, AnthropicClient


@pytest.fixture
def kimi_client():
    return KimiClient(
        model="test-model",
        temperature=0.3,
        max_tokens=500,
        timeout=10.0,
        client_type="slot_scoring",
        api_key="test-key",
    )


@pytest.fixture
def anthropic_client():
    return AnthropicClient(
        model="test-model",
        temperature=0.3,
        max_tokens=500,
        timeout=10.0,
        client_type="extraction",
        api_key="test-key",
    )


def _mock_openai_response(content: str) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "test-model",
        },
        request=httpx.Request("POST", "https://test"),
    )


def _mock_anthropic_tool_response() -> httpx.Response:
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
async def test_openai_json_mode_adds_response_format(kimi_client):
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
    captured_payload = {}

    async def mock_post(url, headers=None, json=None):
        captured_payload.update(json)
        return _mock_openai_response("free text")

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        await kimi_client.complete(prompt="test")

    assert "response_format" not in captured_payload


@pytest.mark.asyncio
async def test_anthropic_tool_use_payload(anthropic_client):
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
    captured_payload = {}

    async def mock_post(url, headers=None, json=None):
        captured_payload.update(json)
        return _mock_anthropic_text_response("hello")

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        await anthropic_client.complete(prompt="test")

    assert "tools" not in captured_payload
    assert "tool_choice" not in captured_payload
