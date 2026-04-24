"""Global signal detection service.

Extracts global signal detection from MethodologyStrategyService for single responsibility.

LLM signal detection has been moved to the pipeline: LLMPrefetchStage (Stage 3.1) fires
the LLM batch call, LLMSignalBridgeStage (Stage 4.7) awaits it and emits the contract.
This service now detects non-LLM signals and merges pre-fetched LLM global signals
passed via the `llm_global_signals` parameter.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

import structlog

from src.methodologies import get_registry

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext

log = structlog.get_logger(__name__)


class GlobalSignalDetectionService:
    """Detects global-level signals from response text and graph state.

    Global signals include:
    - response.semantic.llm.response_depth: How detailed the response is (from Stage 4.7 contract)
    - response.semantic.llm.engagement.trend: Trend over recent responses (improving/degrading/stable)
    - graph.* signals: Graph state metrics
    """

    def __init__(self):
        """Initialize with methodology registry."""
        self.methodology_registry = get_registry()
        self._global_trend_signal = None

    def _get_global_trend_signal(self):
        """Lazy import and cache the trend signal."""
        if self._global_trend_signal is None:
            from src.signals.session.llm_response_trend import GlobalResponseTrendSignal

            self._global_trend_signal = GlobalResponseTrendSignal()
        return self._global_trend_signal

    async def detect(
        self,
        methodology_name: str,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
        llm_global_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Detect all global signals for the given context.

        Detects non-LLM global signals via ComposedSignalDetector, then merges
        pre-fetched LLM global signals from Stage 4.7 contract (passed via
        llm_global_signals parameter). Finally, detects the response trend signal
        which depends on response_depth from the LLM signals.

        Args:
            methodology_name: Name of methodology (e.g., "means_end_chain")
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text
            llm_global_signals: Pre-fetched LLM global signals from Stage 4.7 contract.
                When provided, merged into the result instead of making the LLM call here.

        Returns:
            Dict mapping signal_name to value (e.g., {"response.semantic.llm.response_depth": "deep"})
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

        # Detect non-LLM global signals via methodology's signal detector.
        # Note: ComposedSignalDetector is created without _llm_detector, so it
        # skips the LLM batch call block and only detects graph/temporal/meta signals.
        signal_detector = self.methodology_registry.create_signal_detector(config)

        try:
            global_signals = await signal_detector.detect(
                context,
                graph_state,
                response_text,
            )
        except Exception as e:
            log.error(
                "global_signal_detection_failed",
                methodology=methodology_name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

        # Merge pre-fetched LLM global signals from Stage 4.7 contract
        if llm_global_signals:
            global_signals.update(llm_global_signals)
            log.debug(
                "llm_global_signals_merged",
                methodology=methodology_name,
                merged_keys=list(llm_global_signals.keys()),
            )

        log.debug(
            "global_signals_detected",
            methodology=methodology_name,
            signals=global_signals,
        )

        # Update and detect global response trend
        current_depth = global_signals.get(
            "response.semantic.llm.response_depth", "surface"
        )
        trend_signal = self._get_global_trend_signal()

        try:
            trend_result = await trend_signal.detect(
                context, graph_state, response_text, current_depth=current_depth
            )
            global_trend = trend_result.get(
                "response.semantic.llm.engagement.trend", "stable"
            )
            global_signals["response.semantic.llm.engagement.trend"] = global_trend

            log.debug(
                "global_response_trend_detected",
                methodology=methodology_name,
                trend=global_trend,
                history_length=len(trend_signal.response_history),
            )
        except Exception as e:
            log.warning(
                "global_trend_detection_failed",
                methodology=methodology_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            global_signals["response.semantic.llm.engagement.trend"] = "stable"

        return global_signals
