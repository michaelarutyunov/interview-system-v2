"""Tests for LLM client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.llm.client import AnthropicClient, LLMResponse, get_llm_client


class TestAnthropicClient:
    """Tests for AnthropicClient."""

    def test_init_with_api_key(self):
        """Client initializes with explicit API key."""
        client = AnthropicClient(api_key="test-key")
        assert client.api_key == "test-key"

    def test_init_without_api_key_raises(self):
        """Client raises if no API key available."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.anthropic_api_key = None
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                AnthropicClient()

    def test_init_uses_settings_defaults(self):
        """Client uses settings for defaults."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.anthropic_api_key = "settings-key"
            mock_settings.llm_model = "claude-sonnet-4-20250514"
            mock_settings.llm_timeout_seconds = 30.0

            client = AnthropicClient()

            assert client.api_key == "settings-key"
            assert client.model == "claude-sonnet-4-20250514"
            assert client.timeout == 30.0

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete() returns LLMResponse on success."""
        mock_response = {
            "content": [{"type": "text", "text": "Hello, world!"}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            MockClient.return_value.__aenter__.return_value = mock_client

            client = AnthropicClient(api_key="test-key")
            response = await client.complete("Say hello")

            assert isinstance(response, LLMResponse)
            assert response.content == "Hello, world!"
            assert response.usage["input_tokens"] == 10
            assert response.usage["output_tokens"] == 5

    @pytest.mark.asyncio
    async def test_complete_with_system_prompt(self):
        """complete() includes system prompt in request."""
        mock_response = {
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 20, "output_tokens": 5},
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            MockClient.return_value.__aenter__.return_value = mock_client

            client = AnthropicClient(api_key="test-key")
            await client.complete("User message", system="You are helpful")

            # Verify system was included in payload
            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            assert payload["system"] == "You are helpful"


class TestGetLLMClient:
    """Tests for get_llm_client factory."""

    def test_returns_anthropic_client(self):
        """Factory returns AnthropicClient for anthropic provider."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm_provider = "anthropic"
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.llm_model = "claude-sonnet-4-20250514"
            mock_settings.llm_timeout_seconds = 30.0

            client = get_llm_client()

            assert isinstance(client, AnthropicClient)

    def test_raises_for_unknown_provider(self):
        """Factory raises for unknown provider."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm_provider = "openai"

            with pytest.raises(ValueError, match="Unknown LLM provider"):
                get_llm_client()


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_response(self):
        """LLMResponse can be created with all fields."""
        response = LLMResponse(
            content="Hello",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 10, "output_tokens": 5},
            latency_ms=150.5,
        )

        assert response.content == "Hello"
        assert response.model == "claude-sonnet-4-20250514"
        assert response.latency_ms == 150.5

    def test_response_defaults(self):
        """LLMResponse has sensible defaults."""
        response = LLMResponse(content="Hi", model="test")

        assert response.usage == {}
        assert response.latency_ms == 0.0
        assert response.raw_response is None
