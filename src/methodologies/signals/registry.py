"""Signal detector registry for composing signals from pools.

Maps namespaced signal names to detector classes and handles
dynamic signal detection.
"""

import structlog
from typing import TYPE_CHECKING, Any, Optional, Union

from src.core.exceptions import ScorerFailureError

log = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from src.services.turn_pipeline.context import PipelineContext
    from src.services.node_state_tracker import NodeStateTracker
else:
    NodeStateTracker = object


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

    # Mapping of signal names to detector classes or factory functions
    # Regular signals: signal_name -> detector_class
    # Node-level signals: signal_name -> (detector_class, "node_level")
    _signal_registry: dict[str, Union[type, tuple]] = {}
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
            ChainCompletionSignal,
            # Canonical graph signals (Phase 4, bead 3pna)
            CanonicalConceptCountSignal,
            CanonicalEdgeDensitySignal,
            CanonicalExhaustionScoreSignal,
            # Node-level signals
            NodeExhaustedSignal,
            NodeExhaustionScoreSignal,
            NodeYieldStagnationSignal,
            NodeFocusStreakSignal,
            NodeIsCurrentFocusSignal,
            NodeRecencyScoreSignal,
            NodeIsOrphanSignal,
            NodeEdgeCountSignal,
            NodeHasOutgoingSignal,
        )
        from src.methodologies.signals.llm import (
            ResponseDepthSignal,
            SentimentSignal,
            UncertaintySignal,
            AmbiguitySignal,
            HedgingLanguageSignal,
        )
        from src.methodologies.signals.temporal import (
            StrategyRepetitionCountSignal,
            TurnsSinceChangeSignal,
        )
        from src.methodologies.signals.meta import (
            InterviewProgressSignal,
            InterviewPhaseSignal,
            NodeOpportunitySignal,
        )
        from src.methodologies.signals.technique import (
            NodeStrategyRepetitionSignal,
        )

        # Regular signals (no dependencies)
        regular_signals = [
            # Graph
            GraphNodeCountSignal,
            GraphEdgeCountSignal,
            OrphanCountSignal,
            GraphMaxDepthSignal,
            GraphAvgDepthSignal,
            DepthByElementSignal,
            ChainCompletionSignal,
            # Canonical graph (Phase 4, bead 3pna)
            CanonicalConceptCountSignal,
            CanonicalEdgeDensitySignal,
            CanonicalExhaustionScoreSignal,
            # LLM
            ResponseDepthSignal,
            SentimentSignal,
            UncertaintySignal,
            AmbiguitySignal,
            HedgingLanguageSignal,
            # Note: GlobalResponseTrendSignal is session-scoped and managed separately
            # Temporal
            StrategyRepetitionCountSignal,
            TurnsSinceChangeSignal,
            # Meta
            InterviewProgressSignal,
            InterviewPhaseSignal,
        ]

        # Node-level signals (require NodeStateTracker)
        node_level_signals = [
            # Node-level: Exhaustion
            NodeExhaustedSignal,
            NodeExhaustionScoreSignal,
            NodeYieldStagnationSignal,
            # Node-level: Engagement
            NodeFocusStreakSignal,
            NodeIsCurrentFocusSignal,
            NodeRecencyScoreSignal,
            # Node-level: Relationships
            NodeIsOrphanSignal,
            NodeEdgeCountSignal,
            NodeHasOutgoingSignal,
            # Technique
            NodeStrategyRepetitionSignal,
            # Meta (node-level)
            NodeOpportunitySignal,
        ]

        # Register regular signals
        for signal_class in regular_signals:
            detector = signal_class()
            cls._signal_registry[detector.signal_name] = signal_class

        # Register node-level signals with marker
        for signal_class in node_level_signals:
            # Create a temporary instance to get the signal name
            # We'll create the actual instance later with NodeStateTracker
            temp_detector = signal_class.__new__(signal_class)
            temp_detector.signal_name = signal_class.signal_name
            cls._signal_registry[temp_detector.signal_name] = (
                signal_class,
                "node_level",
            )

        cls._initialized = True

    @classmethod
    def get_known_signal_names(cls) -> set[str]:
        """Return the set of all registered signal names.

        Initializes the registry if needed. Used by MethodologyRegistry
        for YAML config validation.
        """
        cls._register_signals()
        return set(cls._signal_registry.keys())

    def __init__(
        self,
        signal_names: list[str],
        node_tracker: Optional["NodeStateTracker"] = None,
    ):
        """Initialize composed detector.

        Args:
            signal_names: List of namespaced signal names to detect
            node_tracker: NodeStateTracker instance (required for node-level signals)
        """
        self._register_signals()
        self.signal_names = signal_names
        self.node_tracker = node_tracker

        # Create detector instances
        self.detectors: list[Any] = []
        for signal_name in signal_names:
            if signal_name not in self._signal_registry:
                raise ValueError(f"Unknown signal: {signal_name}")

            registry_entry = self._signal_registry[signal_name]

            # Check if this is a node-level signal
            if isinstance(registry_entry, tuple) and registry_entry[1] == "node_level":
                # Node-level signal: (signal_class, "node_level")
                signal_class = registry_entry[0]
                if self.node_tracker is None:
                    raise ValueError(
                        f"NodeStateTracker required for node-level signal: {signal_name}"
                    )
                self.detectors.append(signal_class(self.node_tracker))
            else:
                # Regular signal: signal_class
                self.detectors.append(registry_entry())  # type: ignore

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

            try:
                signals = await detector.detect(context, graph_state, response_text)
                all_signals.update(signals)
            except Exception as e:
                log.error(
                    "signal_detector_failed",
                    signal_name=detector.signal_name,
                    error=str(e),
                    exc_info=True,
                )
                raise ScorerFailureError(
                    f"Signal detector '{detector.signal_name}' failed: {e}"
                ) from e

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
            try:
                signals = await detector.detect(
                    temp_context, graph_state, response_text
                )
                all_signals.update(signals)
            except Exception as e:
                log.error(
                    "signal_detector_failed",
                    signal_name=detector.signal_name,
                    error=str(e),
                    exc_info=True,
                )
                raise ScorerFailureError(
                    f"Signal detector '{detector.signal_name}' failed: {e}"
                ) from e

        return all_signals
