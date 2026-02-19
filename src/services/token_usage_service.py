"""
Token usage aggregation service for LLM cost tracking.

Collects and aggregates LLM token usage per session, organized by model
and client_type (extraction/scoring/generation). Stores data in-memory
and provides aggregated totals for persistence to session metadata.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import structlog

from src.core.config import settings

log = structlog.get_logger(__name__)


@dataclass
class ClientTypeUsage:
    """Token usage and costs for a specific client_type within a model.

    Attributes:
        input_tokens: Total input tokens used
        output_tokens: Total output tokens used
        input_cost: Total input token cost (USD)
        output_cost: Total output token cost (USD)
    """

    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        """Total cost for this client_type."""
        return self.input_cost + self.output_cost


@dataclass
class ModelUsage:
    """Token usage and costs for a specific model across all client_types.

    Organizes usage by client_type (extraction/scoring/generation).

    Attributes:
        client_types: Dict mapping client_type to ClientTypeUsage
    """

    client_types: Dict[str, ClientTypeUsage] = field(default_factory=dict)

    def record_usage(
        self,
        client_type: str,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
    ) -> None:
        """Record usage for a specific client_type."""
        if client_type not in self.client_types:
            self.client_types[client_type] = ClientTypeUsage()

        usage = self.client_types[client_type]
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.input_cost += input_cost
        usage.output_cost += output_cost


class TokenUsageService:
    """
    In-memory aggregation service for LLM token usage.

    Tracks usage per session, model, and client_type. Provides aggregated
    totals for persistence to session.config["metadata"]["llm_usage"].

    Usage:
        service = TokenUsageService()
        service.record_llm_call(session_id, model, input_tokens, output_tokens, client_type)
        aggregated = service.get_session_usage(session_id)
    """

    def __init__(self):
        """Initialize the service with empty usage tracking."""
        # Nested structure: session_id -> model_name -> ModelUsage
        self._session_usage: Dict[str, Dict[str, ModelUsage]] = {}

    def record_llm_call(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        client_type: str,
    ) -> None:
        """
        Record an LLM call's token usage.

        Calculates costs using pricing from Settings and aggregates
        with existing usage data.

        Args:
            session_id: Session identifier
            model: Model name (e.g., "claude-sonnet-4-6")
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            client_type: Client type ("extraction", "scoring", "generation")
        """
        # Get pricing for this model
        input_price_per_million, output_price_per_million = settings.get_pricing_for_model(
            model
        )

        # Calculate costs (prices are per million tokens)
        input_cost = (input_tokens / 1_000_000) * input_price_per_million
        output_cost = (output_tokens / 1_000_000) * output_price_per_million

        # Initialize session entry if needed
        if session_id not in self._session_usage:
            self._session_usage[session_id] = {}

        # Initialize model entry if needed
        if model not in self._session_usage[session_id]:
            self._session_usage[session_id][model] = ModelUsage()

        # Record usage
        self._session_usage[session_id][model].record_usage(
            client_type=client_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
        )

        log.debug(
            "llm_usage_recorded",
            session_id=session_id,
            model=model,
            client_type=client_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=round(input_cost, 4),
            output_cost=round(output_cost, 4),
        )

    def get_session_usage(self, session_id: str) -> Optional[Dict[str, Dict]]:
        """
        Get aggregated usage for a session, formatted for persistence.

        Returns None if session has no recorded usage.

        Format:
        {
            "model_name": {
                "client_type": {
                    "input_tokens": 123,
                    "output_tokens": 456,
                    "input_cost": 0.0123,
                    "output_cost": 0.0456,
                    "total_cost": 0.0579
                }
            }
        }

        Args:
            session_id: Session identifier

        Returns:
            Nested dict of usage data, or None if no usage recorded
        """
        if session_id not in self._session_usage:
            return None

        result = {}
        for model, model_usage in self._session_usage[session_id].items():
            model_result = {}
            for client_type, usage in model_usage.client_types.items():
                model_result[client_type] = {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "input_cost": round(usage.input_cost, 4),
                    "output_cost": round(usage.output_cost, 4),
                    "total_cost": round(usage.total_cost, 4),
                }
            result[model] = model_result

        return result

    def clear_session(self, session_id: str) -> None:
        """
        Clear usage data for a session.

        Useful after persisting to avoid memory bloat.

        Args:
            session_id: Session identifier
        """
        if session_id in self._session_usage:
            del self._session_usage[session_id]
            log.debug("llm_usage_cleared", session_id=session_id)


# Global singleton instance
_token_usage_service: Optional[TokenUsageService] = None


def get_token_usage_service() -> TokenUsageService:
    """Get the global TokenUsageService singleton instance."""
    global _token_usage_service
    if _token_usage_service is None:
        _token_usage_service = TokenUsageService()
    return _token_usage_service
