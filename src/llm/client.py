"""
LLM client abstraction for multiple LLM providers.

Provides async interface for LLM calls with:
- Structured logging of requests/responses
- Timeout handling
- Usage tracking (tokens)
- Three-client architecture (extraction, scoring, generation)

Supported providers:
- anthropic: Claude models (Sonnet, Haiku)
- kimi: Moonshot AI models
- deepseek: DeepSeek models
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
import time

import httpx
import structlog

from src.core.config import settings

log = structlog.get_logger(__name__)


LLMClientType = Literal["extraction", "scoring", "generation"]


# =============================================================================
# Default configurations for each client type
# =============================================================================

# These defaults document the recommended configuration for each task.
# Override via environment variables (LLM_EXTRACTION_PROVIDER, etc.) if needed.

EXTRACTION_DEFAULTS = dict(
    provider="anthropic",
    model="claude-sonnet-4-6",
    temperature=0.3,  # Lower for structured, consistent extraction
    max_tokens=2048,  # Higher for complex graph outputs
    timeout=30.0,
    effort="medium",  # Complex agentic reasoning (coding/agentics)
)

SCORING_DEFAULTS = dict(
    provider="kimi",
    model="kimi-k2-0905-preview",
    temperature=0.3,
    max_tokens=512,
    timeout=30.0,  # K2 is larger model, needs more time
)

GENERATION_DEFAULTS = dict(
    provider="anthropic",
    model="claude-sonnet-4-6",
    temperature=0.7,  # Higher for creative question variations
    max_tokens=1024,
    timeout=30.0,
    effort="low",  # Conversational, speed matters (non-coding)
)

# Map client types to their defaults
DEFAULTS_MAP: Dict[LLMClientType, Dict[str, Any]] = {
    "extraction": EXTRACTION_DEFAULTS,
    "scoring": SCORING_DEFAULTS,
    "generation": GENERATION_DEFAULTS,
}


# =============================================================================
# Response and Base Classes
# =============================================================================


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
        effort: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            prompt: User message/prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            effort: Effort level for Sonnet 4.6 ("low", "medium", "high")
            timeout: Optional timeout override in seconds (uses default if None)

        Returns:
            LLMResponse with content and metadata
        """
        pass


# =============================================================================
# Anthropic Client
# =============================================================================


class AnthropicClient(LLMClient):
    """Anthropic Claude API client.

    Uses httpx for async HTTP calls to the Messages API.
    """

    def __init__(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
        client_type: LLMClientType,
        api_key: Optional[str] = None,
        effort: Optional[str] = None,
    ):
        """
        Initialize Anthropic client.

        Args:
            model: Model ID (e.g., claude-sonnet-4-6)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            client_type: Client type for logging
            api_key: API key (defaults to settings.anthropic_api_key)
            effort: Default effort level ("low", "medium", "high")

        Raises:
            ValueError: If API key is not configured
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.client_type = client_type
        self.effort = effort
        self.base_url = "https://api.anthropic.com/v1"

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured. Set it in .env.")

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
        effort: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> LLMResponse:
        """
        Call Anthropic Messages API with automatic retry on timeout/rate-limit.

        Args:
            prompt: User message
            system: Optional system prompt
            temperature: Sampling temperature (defaults to init value)
            max_tokens: Max tokens (defaults to init value)
            effort: Effort level for Sonnet 4.6 ("low", "medium", "high")
            timeout: Optional timeout override in seconds (uses default if None)

        Returns:
            LLMResponse with content and usage stats

        Raises:
            LLMTimeoutError: After all retries exhausted on timeout
            LLMRateLimitError: After all retries exhausted on rate limit (429)
            httpx.HTTPStatusError: On other API errors (no retry)
        """
        import asyncio
        from src.core.exceptions import LLMTimeoutError, LLMRateLimitError

        max_retries = 1  # 2 total attempts
        base_delay = 1.0  # seconds

        # Use instance defaults if not provided
        if max_tokens is None:
            max_tokens = self.max_tokens
        if temperature is None:
            temperature = self.temperature
        if effort is None:
            effort = getattr(self, "effort", None)
        if timeout is None:
            timeout = self.timeout

        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

        if system:
            payload["system"] = system

        # Add effort parameter for Sonnet 4.6 (controls output token budget)
        # See: https://platform.claude.com/docs/en/about-claude/models/migration-guide
        if effort is not None:
            # Validate effort values
            valid_efforts = {"low", "medium", "high"}
            if effort not in valid_efforts:
                log.warning(
                    "invalid_effort_value",
                    effort=effort,
                    valid_efforts=valid_efforts,
                    defaulting_to="medium",
                )
                effort = "medium"
            payload["output_config"] = {"effort": effort}

        for attempt in range(max_retries + 1):
            start = time.perf_counter()

            log.debug(
                "llm_call_start",
                provider="anthropic",
                client_type=self.client_type,
                model=self.model,
                prompt_length=len(prompt),
                system_length=len(system) if system else 0,
                temperature=temperature,
                max_tokens=max_tokens,
                effort=effort,  # Log effort level for observability
                attempt=attempt + 1,
                max_retries=max_retries,
            )

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
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
                    provider="anthropic",
                    client_type=self.client_type,
                    model=self.model,
                    latency_ms=round(latency_ms, 2),
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    attempt=attempt + 1,
                )

                return LLMResponse(
                    content=content,
                    model=data.get("model", self.model),
                    usage=usage,
                    latency_ms=latency_ms,
                    raw_response=data,
                )

            except httpx.TimeoutException as e:
                log.warning(
                    "llm_timeout",
                    provider="anthropic",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    timeout_seconds=self.timeout,
                )
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)  # 1s on first retry
                    log.info(
                        "llm_retry_after_timeout",
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise LLMTimeoutError(
                        f"LLM call timed out after {max_retries + 1} attempts "
                        f"(timeout={self.timeout}s)"
                    ) from e

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 429:  # Rate limit
                    log.warning(
                        "llm_rate_limit",
                        provider="anthropic",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    if attempt < max_retries:
                        delay = base_delay * (2**attempt)
                        log.info(
                            "llm_retry_after_rate_limit",
                            delay_seconds=delay,
                            next_attempt=attempt + 2,
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise LLMRateLimitError(
                            f"Rate limit exceeded after {max_retries + 1} attempts"
                        ) from e
                else:
                    # Don't retry other 4xx/5xx errors
                    log.error(
                        "llm_http_error",
                        provider="anthropic",
                        status_code=status_code,
                    )
                    raise

        # Unreachable: loop either returns LLMResponse or raises an exception
        assert False, "unreachable"


# =============================================================================
# OpenAI-Compatible Client Base
# =============================================================================


class OpenAICompatibleClient(LLMClient):
    """
    Base class for OpenAI-compatible API clients.

    Used by providers that follow the OpenAI API format:
    - Kimi (Moonshot AI): https://api.moonshot.cn/v1
    - DeepSeek: https://api.deepseek.com
    """

    def __init__(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
        client_type: LLMClientType,
        base_url: str,
        provider_name: str,
        api_key: str,
    ):
        """
        Initialize OpenAI-compatible client.

        Args:
            model: Model ID
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            client_type: Client type for logging
            base_url: Base URL for the API
            provider_name: Name of the provider for logging
            api_key: API key for the provider
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.client_type = client_type
        self.base_url = base_url
        self.provider_name = provider_name
        self.api_key = api_key

        log.info(
            "openai_compatible_client_initialized",
            provider=self.provider_name,
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
        effort: Optional[str] = None,  # Ignored for OpenAI-compatible APIs
        timeout: Optional[float] = None,
    ) -> LLMResponse:
        """
        Call OpenAI-compatible API with automatic retry on timeout/rate-limit.

        Args:
            prompt: User message
            system: Optional system prompt
            temperature: Sampling temperature (defaults to init value)
            max_tokens: Max tokens (defaults to init value)
            effort: Ignored for OpenAI-compatible APIs (no effort parameter support)
            timeout: Optional timeout override in seconds (uses default if None)

        Returns:
            LLMResponse with content and usage stats

        Raises:
            LLMTimeoutError: After all retries exhausted on timeout
            LLMRateLimitError: After all retries exhausted on rate limit (429)
            httpx.HTTPStatusError: On other API errors (no retry)
        """
        import asyncio
        from src.core.exceptions import LLMTimeoutError, LLMRateLimitError

        max_retries = 1  # 2 total attempts
        base_delay = 1.0  # seconds

        # Use instance defaults if not provided
        if max_tokens is None:
            max_tokens = self.max_tokens
        if temperature is None:
            temperature = self.temperature
        if timeout is None:
            timeout = self.timeout

        # Log if effort was provided but will be ignored
        if effort is not None:
            log.debug(
                "effort_parameter_ignored",
                provider=self.provider_name,
                effort=effort,
                reason="OpenAI-compatible APIs do not support effort parameter",
            )

        # Build messages array
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt in range(max_retries + 1):
            start = time.perf_counter()

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            log.debug(
                "llm_call_start",
                provider=self.provider_name,
                client_type=self.client_type,
                model=self.model,
                prompt_length=len(prompt),
                system_length=len(system) if system else 0,
                temperature=temperature,
                max_tokens=max_tokens,
                attempt=attempt + 1,
                max_retries=max_retries,
            )

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                latency_ms = (time.perf_counter() - start) * 1000

                # Extract content from OpenAI-compatible response
                content = ""
                if data.get("choices"):
                    content = data["choices"][0].get("message", {}).get("content", "")

                usage = {
                    "input_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("completion_tokens", 0),
                }

                log.info(
                    "llm_call_complete",
                    provider=self.provider_name,
                    client_type=self.client_type,
                    model=self.model,
                    latency_ms=round(latency_ms, 2),
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    attempt=attempt + 1,
                )

                return LLMResponse(
                    content=content,
                    model=data.get("model", self.model),
                    usage=usage,
                    latency_ms=latency_ms,
                    raw_response=data,
                )

            except httpx.TimeoutException as e:
                log.warning(
                    "llm_timeout",
                    provider=self.provider_name,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    timeout_seconds=self.timeout,
                )
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    log.info(
                        "llm_retry_after_timeout",
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise LLMTimeoutError(
                        f"LLM call timed out after {max_retries + 1} attempts "
                        f"(timeout={self.timeout}s)"
                    ) from e

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 429:  # Rate limit
                    log.warning(
                        "llm_rate_limit",
                        provider=self.provider_name,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    if attempt < max_retries:
                        delay = base_delay * (2**attempt)
                        log.info(
                            "llm_retry_after_rate_limit",
                            delay_seconds=delay,
                            next_attempt=attempt + 2,
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise LLMRateLimitError(
                            f"Rate limit exceeded after {max_retries + 1} attempts"
                        ) from e
                else:
                    # Don't retry other 4xx/5xx errors
                    log.error(
                        "llm_http_error",
                        provider=self.provider_name,
                        status_code=status_code,
                    )
                    raise

        # Unreachable: loop either returns LLMResponse or raises an exception
        assert False, "unreachable"


# =============================================================================
# Kimi Client
# =============================================================================


class KimiClient(OpenAICompatibleClient):
    """
    Kimi (Moonshot AI) API client.

    API Docs: https://platform.moonshot.ai/docs
    Base URL: https://api.moonshot.ai/v1

    Models (as of 2025):
    - moonshot-v1-8k: 8K context
    - moonshot-v1-32k: 32K context
    - moonshot-v1-128k: 128K context
    """

    def __init__(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
        client_type: LLMClientType,
        api_key: Optional[str] = None,
    ):
        """Initialize Kimi client."""
        api_key = api_key or settings.kimi_api_key
        base_url = "https://api.moonshot.ai/v1"

        if not api_key:
            raise ValueError("KIMI_API_KEY not configured. Set it in .env.")

        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            client_type=client_type,
            base_url=base_url,
            provider_name="kimi",
            api_key=api_key,
        )


# =============================================================================
# DeepSeek Client
# =============================================================================


class DeepSeekClient(OpenAICompatibleClient):
    """
    DeepSeek API client.

    API Docs: https://platform.deepseek.com/api-docs/
    Base URL: https://api.deepseek.com

    Models (as of 2025):
    - deepseek-chat: General purpose chat model
    - deepseek-coder: Code generation model
    """

    def __init__(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
        client_type: LLMClientType,
        api_key: Optional[str] = None,
    ):
        """Initialize DeepSeek client."""
        api_key = api_key or settings.deepseek_api_key
        base_url = "https://api.deepseek.com"

        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured. Set it in .env.")

        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            client_type=client_type,
            base_url=base_url,
            provider_name="deepseek",
            api_key=api_key,
        )


# =============================================================================
# Client Factory Functions
# =============================================================================


def get_llm_client(client_type: LLMClientType) -> LLMClient:
    """
    Factory for LLM client based on client type.

    Uses hardcoded defaults for each client type, with optional
    environment variable overrides (LLM_EXTRACTION_PROVIDER, etc.).

    Args:
        client_type: "extraction", "scoring", or "generation"

    Returns:
        LLMClient instance configured for the specified client type

    Raises:
        ValueError: If unknown provider configured or API key missing
    """
    # Get defaults for this client type
    defaults = DEFAULTS_MAP[client_type]

    # Check for environment override
    env_override_key = f"llm_{client_type}_provider"
    provider = getattr(settings, env_override_key, None) or defaults["provider"]
    model = defaults["model"]
    temperature = defaults["temperature"]
    max_tokens = defaults["max_tokens"]
    timeout = defaults["timeout"]
    effort = defaults.get("effort")  # Optional effort parameter for Sonnet 4.6

    # Create client based on provider
    if provider == "anthropic":
        return AnthropicClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            client_type=client_type,
            effort=effort,
        )
    elif provider == "kimi":
        return KimiClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            client_type=client_type,
        )
    elif provider == "deepseek":
        return DeepSeekClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            client_type=client_type,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider '{provider}' for {client_type}. "
            f"Supported providers: anthropic, kimi, deepseek"
        )


def get_extraction_llm_client() -> LLMClient:
    """
    Factory for extraction LLM client (nodes/edges).

    Returns:
        LLMClient instance configured for extraction tasks
    """
    return get_llm_client("extraction")


def get_scoring_llm_client() -> LLMClient:
    """
    Factory for scoring LLM client (diagnostic signals).

    Returns:
        LLMClient instance configured for scoring tasks
    """
    return get_llm_client("scoring")


def get_generation_llm_client() -> LLMClient:
    """
    Factory for generation LLM client (question generation).

    Returns:
        LLMClient instance configured for question generation
    """
    return get_llm_client("generation")
