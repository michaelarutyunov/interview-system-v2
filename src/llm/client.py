"""
LLM client abstraction for Anthropic API.

Provides async interface for LLM calls with:
- Structured logging of requests/responses
- Timeout handling
- Usage tracking (tokens)
- Dual client support (main for generation, light for scoring)

Supports two LLM configurations:
- llm_main: For question generation (Claude Sonnet/GPT-4)
- llm_light: For scoring tasks (Claude Haiku/GPT-4o-mini)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
import time

import httpx
import structlog

from src.core.config import settings

log = structlog.get_logger(__name__)


LLMClientType = Literal["main", "light"]


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
    Supports both main and light configurations.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        client_type: LLMClientType = "main",
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: API key (defaults to settings.anthropic_api_key)
            model: Model ID (defaults based on client_type)
            timeout: Request timeout in seconds (defaults based on client_type)
            client_type: "main" for generation, "light" for scoring

        Raises:
            ValueError: If API key is not configured
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.client_type = client_type
        self.base_url = "https://api.anthropic.com/v1"

        # Set model based on client type
        if model:
            self.model = model
        elif client_type == "main":
            self.model = settings.llm_main_model
        else:  # light
            self.model = settings.llm_light_model

        # Set timeout based on client type
        if timeout is not None:
            self.timeout = timeout
        elif client_type == "main":
            self.timeout = settings.llm_main_timeout_seconds
        else:  # light
            self.timeout = settings.llm_light_timeout_seconds

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not configured. "
                "Set it in .env or pass api_key parameter."
            )

        log.info(
            "anthropic_client_initialized",
            client_type=self.client_type,
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
            temperature: Sampling temperature (defaults based on client_type)
            max_tokens: Max tokens (defaults based on client_type)

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

        # Set defaults based on client type
        if max_tokens is None:
            if self.client_type == "main":
                max_tokens = settings.llm_main_max_tokens
            else:
                max_tokens = settings.llm_light_max_tokens

        if temperature is None:
            if self.client_type == "main":
                temperature = settings.llm_main_temperature
            else:
                temperature = settings.llm_light_temperature

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system:
            payload["system"] = system

        payload["temperature"] = temperature

        log.debug(
            "llm_call_start",
            client_type=self.client_type,
            model=self.model,
            prompt_length=len(prompt),
            system_length=len(system) if system else 0,
            temperature=temperature,
            max_tokens=max_tokens,
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
            client_type=self.client_type,
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


def get_llm_client(client_type: LLMClientType = "main") -> LLMClient:
    """
    Factory for LLM client based on configuration.

    Args:
        client_type: "main" for question generation, "light" for scoring tasks

    Returns:
        LLMClient instance (AnthropicClient for v2)

    Raises:
        ValueError: If unknown provider configured
    """
    # Select provider based on client type
    if client_type == "main":
        provider = settings.llm_main_provider
    else:
        provider = settings.llm_light_provider

    if provider == "anthropic":
        return AnthropicClient(client_type=client_type)
    else:
        raise ValueError(f"Unknown LLM provider for {client_type}: {provider}")


def get_main_llm_client() -> LLMClient:
    """
    Factory for main LLM client (question generation).

    Returns:
        LLMClient instance configured for question generation
    """
    return get_llm_client("main")


def get_light_llm_client() -> LLMClient:
    """
    Factory for light LLM client (scoring tasks).

    Returns:
        LLMClient instance configured for scoring tasks
    """
    return get_llm_client("light")
