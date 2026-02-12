"""Global signal detection service.

Extracts global signal detection from MethodologyStrategyService for single responsibility.
"""

from typing import TYPE_CHECKING, Any, Dict

import structlog

from src.methodologies import get_registry

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext

log = structlog.get_logger(__name__)


class GlobalSignalDetectionService:
    """Detects global-level signals from response text and graph state.

    Global signals include:
    - llm.response_depth: How detailed the response is
    - llm.global_response_trend: Trend over recent responses (improving/degrading/stable)
    - graph.* signals: Graph state metrics
    """

    def __init__(self):
        """Initialize with methodology registry."""
        self.methodology_registry = get_registry()
        self._global_trend_signal = None

    def _get_global_trend_signal(self):
        """Lazy import and cache the trend signal."""
        if self._global_trend_signal is None:
            from src.signals.llm.global_response_trend import GlobalResponseTrendSignal
            self._global_trend_signal = GlobalResponseTrendSignal()
        return self._global_trend_signal

    async def detect(
        self,
        methodology_name: str,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> Dict[str, Any]:
        """
        Detect all global signals for the given context.

        Args:
            methodology_name: Name of methodology (e.g., "means_end_chain")
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text

        Returns:
            Dict mapping signal_name to value (e.g., {"llm.response_depth": "deep"})
        """
        config = self.methodology_registry.get_methodology(methodology_name)
        if not config:
            available = self.methodology_registry.list_methodologies()
            log.error(
                "methodology_not_found",
                name=methodology_name,
                available=available,
                exc_info=True,
            )
            from src.core.exceptions import ConfigurationError

            raise ConfigurationError(
                f"Methodology '{methodology_name}' not found in registry. "
                f"Available methodologies: {available}. "
                f"Check that the methodology YAML file exists in config/methodologies/ "
                f"and is properly registered."
            )

        # Detect global signals via methodology's signal detector
        signal_detector = self.methodology_registry.create_signal_detector(config)
        global_signals = await signal_detector.detect(context, graph_state, response_text)

        log.debug(
            "global_signals_detected",
            methodology=methodology_name,
            signals=global_signals,
        )

        # Update and detect global response trend
        current_depth = global_signals.get("llm.response_depth", "surface")
        trend_signal = self._get_global_trend_signal()
        trend_result = await trend_signal.detect(
            context, graph_state, response_text, current_depth=current_depth
        )
        global_trend = trend_result.get("llm.global_response_trend", "stable")
        global_signals["llm.global_response_trend"] = global_trend

        log.debug(
            "global_response_trend_detected",
            methodology=methodology_name,
            trend=global_trend,
            history_length=len(trend_signal.response_history),
        )

        return global_signals
