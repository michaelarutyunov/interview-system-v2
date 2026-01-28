"""Signal detector registry for composing signals from pools.

Maps namespaced signal names to detector classes and handles
dynamic signal detection.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.turn_pipeline.context import PipelineContext


class ComposedSignalDetector:
    """Composed signal detector from YAML config.

    Detects all signals for a methodology by composing detectors
    from the shared signal pools.

    Example:
        detector = ComposedSignalDetector([
            "graph.node_count",
            "graph.max_depth",
            "llm.response_depth",
        ])
        signals = await detector.detect(context, graph_state, response_text)
    """

    # Mapping of signal names to detector classes (lazy loaded)
    _signal_registry: dict[str, type] = {}
    _initialized = False

    @classmethod
    def _register_signals(cls):
        """Register all available signals from pools."""
        if cls._initialized:
            return

        # Import all signal classes
        from src.methodologies.signals.graph import (
            GraphNodeCountSignal,
            GraphEdgeCountSignal,
            OrphanCountSignal,
            GraphMaxDepthSignal,
            GraphAvgDepthSignal,
            DepthByElementSignal,
            CoverageBreadthSignal,
            MissingTerminalValueSignal,
        )
        from src.methodologies.signals.llm import (
            ResponseDepthSignal,
            SentimentSignal,
            UncertaintySignal,
            AmbiguitySignal,
        )
        from src.methodologies.signals.temporal import (
            StrategyRepetitionCountSignal,
            TurnsSinceChangeSignal,
        )
        from src.methodologies.signals.meta import InterviewProgressSignal

        # Build registry: signal_name -> detector_class
        for signal_class in [
            # Graph
            GraphNodeCountSignal,
            GraphEdgeCountSignal,
            OrphanCountSignal,
            GraphMaxDepthSignal,
            GraphAvgDepthSignal,
            DepthByElementSignal,
            CoverageBreadthSignal,
            MissingTerminalValueSignal,
            # LLM
            ResponseDepthSignal,
            SentimentSignal,
            UncertaintySignal,
            AmbiguitySignal,
            # Temporal
            StrategyRepetitionCountSignal,
            TurnsSinceChangeSignal,
            # Meta
            InterviewProgressSignal,
        ]:
            detector = signal_class()
            # Register signal_name -> detector class
            cls._signal_registry[detector.signal_name] = signal_class

        cls._initialized = True

    def __init__(self, signal_names: list[str]):
        """Initialize composed detector.

        Args:
            signal_names: List of namespaced signal names to detect
        """
        self._register_signals()
        self.signal_names = signal_names

        # Create detector instances
        self.detectors = []
        for signal_name in signal_names:
            if signal_name not in self._signal_registry:
                raise ValueError(f"Unknown signal: {signal_name}")
            detector_class = self._signal_registry[signal_name]
            self.detectors.append(detector_class())

    async def detect(
        self,
        context: "PipelineContext",
        graph_state: Any,
        response_text: str,
    ) -> dict[str, Any]:
        """Detect all signals.

        Args:
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text

        Returns:
            Dictionary of all detected signals
        """
        all_signals: dict[str, Any] = {}

        # First pass: detect all non-meta signals
        for detector in self.detectors:
            # Skip meta signals (they depend on other signals)
            if detector.signal_name.startswith("meta."):
                continue

            signals = await detector.detect(context, graph_state, response_text)
            all_signals.update(signals)

        # Update context with detected signals for meta signals
        # Note: context.signals is set by the pipeline stage, not here
        # We just pass all_signals to meta detectors directly

        # Second pass: detect meta signals (which depend on other signals)
        for detector in self.detectors:
            if not detector.signal_name.startswith("meta."):
                continue

            # Create a temporary context-like object with signals
            # Meta detectors access context.signals
            class ContextWithSignals:
                def __init__(self, signals_dict):
                    self.signals = signals_dict

            temp_context = ContextWithSignals(all_signals)
            signals = await detector.detect(temp_context, graph_state, response_text)
            all_signals.update(signals)

        return all_signals
