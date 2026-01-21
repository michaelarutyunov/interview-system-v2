"""
LLM client abstraction for Anthropic API.

Provides async interface for LLM calls with:
- Structured logging of requests/responses
- Timeout handling
- Usage tracking (tokens)

Single provider for v2 MVP. Extensible for future providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import time

import httpx
import structlog

from src.core.config import settings

log = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    raw_response: Optional[Dict[str, Any]] = None


class LLMClient(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            prompt: User message/prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content and metadata
        """
        pass


class AnthropicClient(LLMClient):
    """Anthropic Claude API client.

    Uses httpx for async HTTP calls to the Messages API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: API key (defaults to settings.anthropic_api_key)
            model: Model ID (defaults to settings.llm_model)
            timeout: Request timeout in seconds (defaults to settings.llm_timeout_seconds)

        Raises:
            ValueError: If API key is not configured
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.llm_model
        self.base_url = "https://api.anthropic.com/v1"
        self.timeout = timeout or settings.llm_timeout_seconds

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not configured. "
                "Set it in .env or pass api_key parameter."
            )

        log.info(
            "anthropic_client_initialized",
            model=self.model,
            timeout=self.timeout,
        )

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Call Anthropic Messages API.

        Args:
            prompt: User message
            system: Optional system prompt
            temperature: Sampling temperature (defaults to settings.llm_temperature)
            max_tokens: Max tokens (defaults to settings.llm_max_tokens)

        Returns:
            LLMResponse with content and usage stats

        Raises:
            httpx.HTTPStatusError: On API errors (4xx, 5xx)
            httpx.TimeoutException: On timeout
        """
        start = time.perf_counter()

        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system:
            payload["system"] = system

        if temperature is not None:
            payload["temperature"] = temperature
        else:
            payload["temperature"] = settings.llm_temperature

        log.debug(
            "llm_call_start",
            model=self.model,
            prompt_length=len(prompt),
            system_length=len(system) if system else 0,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.perf_counter() - start) * 1000

        # Extract content from response
        content = ""
        if data.get("content"):
            content = data["content"][0].get("text", "")

        usage = {
            "input_tokens": data.get("usage", {}).get("input_tokens", 0),
            "output_tokens": data.get("usage", {}).get("output_tokens", 0),
        }

        log.info(
            "llm_call_complete",
            model=self.model,
            latency_ms=round(latency_ms, 2),
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )

        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            usage=usage,
            latency_ms=latency_ms,
            raw_response=data,
        )


def get_llm_client() -> LLMClient:
    """
    Factory for LLM client based on configuration.

    Returns:
        LLMClient instance (AnthropicClient for v2)

    Raises:
        ValueError: If unknown provider configured
    """
    provider = settings.llm_provider

    if provider == "anthropic":
        return AnthropicClient()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
