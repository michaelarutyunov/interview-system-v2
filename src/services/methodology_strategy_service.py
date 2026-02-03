"""
Strategy selection service using YAML-based methodology configs.

Uses signal pools and YAML configs for methodology-specific strategy selection.
Phase 3 (D1): Uses joint strategy-node scoring with node exhaustion detection.
"""

from typing import Tuple, Optional, TYPE_CHECKING, Any, Dict, Union, Sequence
import structlog

from src.core.exceptions import ConfigurationError, ScoringError, ScorerFailureError
from src.methodologies import get_registry
from src.methodologies.scoring import rank_strategy_node_pairs
from src.methodologies.signals.llm.global_response_trend import (
    GlobalResponseTrendSignal,
)

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext
    from src.services.node_state_tracker import NodeStateTracker

log = structlog.get_logger(__name__)


class MethodologyStrategyService:
    """Strategy selection using YAML methodology configs.

    This service uses:
    - YAML configs for methodology definitions (signals + strategies)
    - Composed signal detectors from shared pools
    - Joint strategy-node scoring with node exhaustion detection (D1 architecture)

    Phase 3: The legacy select_strategy() method has been removed.
    All selection now uses select_strategy_and_focus() for joint scoring.
    """

    def __init__(self):
        """Initialize service with registries."""
        self.methodology_registry = get_registry()
        # Session-scoped global response trend tracking
        self.global_trend_signal = GlobalResponseTrendSignal()

    async def select_strategy_and_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> Tuple[
        str,
        Optional[str],
        Sequence[Union[Tuple[str, float], Tuple[str, str, float]]],
        Optional[Dict[str, Any]],
    ]:
        """
        Select best (strategy, node) pair using joint scoring.

        This method implements D1 architecture from the node exhaustion design:
        1. Detect global signals (response depth, graph state, etc.)
        2. Detect node-level signals for all tracked nodes
        3. Score all (strategy, node) pairs using combined signals
        4. Select best pair

        Args:
            context: Pipeline context with methodology, recent_turns, node_tracker
            graph_state: Current knowledge graph state
            response_text: User's response text for signal analysis

        Returns:
            Tuple of (strategy_name, focus_node_id, alternatives, global_signals)
            - strategy_name: Name of selected strategy
            - focus_node_id: ID of selected focus node (not label)
            - alternatives: List of (strategy_name, node_id, score) for observability
            - global_signals: Dict of global detected signals for observability
        """
        # Get methodology config from YAML
        methodology_name = (
            context.methodology if context.methodology else "means_end_chain"
        )
        config = self.methodology_registry.get_methodology(methodology_name)

        if not config:
            available = self.methodology_registry.list_methodologies()
            log.error(
                "methodology_not_found",
                name=methodology_name,
                available=available,
                exc_info=True,
            )
            raise ConfigurationError(
                f"Methodology '{methodology_name}' not found in registry. "
                f"Available methodologies: {available}. "
                f"Check that the methodology YAML file exists in src/methodologies/config/ "
                f"and is properly registered."
            )

        # Get NodeStateTracker from context
        node_tracker: Optional["NodeStateTracker"] = (
            context.node_tracker if hasattr(context, "node_tracker") else None
        )

        if not node_tracker:
            log.error(
                "node_tracker_not_available",
                methodology=methodology_name,
                error="NodeStateTracker is required for D1 architecture",
            )
            # Raise error since node_tracker is required for joint scoring
            raise ValueError(
                "NodeStateTracker is required for select_strategy_and_focus. "
                "Ensure node_tracker is set in PipelineContext."
            )

        # Create signal detector and detect global signals
        signal_detector = self.methodology_registry.create_signal_detector(config)
        global_signals = await signal_detector.detect(
            context, graph_state, response_text
        )

        log.debug(
            "global_signals_detected",
            methodology=methodology_name,
            signals=global_signals,
        )

        # Update and detect global response trend
        current_depth = global_signals.get("llm.response_depth", "surface")
        trend_result = await self.global_trend_signal.detect(
            context, graph_state, response_text, current_depth=current_depth
        )
        global_trend = trend_result.get("llm.global_response_trend", "stable")

        # Add trend to global_signals
        global_signals["llm.global_response_trend"] = global_trend

        log.debug(
            "global_response_trend_detected",
            methodology=methodology_name,
            trend=global_trend,
            history_length=len(self.global_trend_signal.response_history),
        )

        # Detect node-level signals for all tracked nodes
        node_signals = await self._detect_node_signals(
            config, context, graph_state, response_text, node_tracker
        )

        log.debug(
            "node_signals_detected",
            methodology=methodology_name,
            node_count=len(node_signals),
        )

        # Detect interview phase
        from src.methodologies.signals.meta.interview_phase import (
            InterviewPhaseSignal,
        )

        phase_signal = InterviewPhaseSignal()
        phase_result = await phase_signal.detect(context, graph_state, response_text)
        current_phase = phase_result.get("meta.interview.phase", "early")

        log.info(
            "interview_phase_detected",
            methodology=methodology_name,
            phase=current_phase,
        )

        # Get phase weights from config
        phase_weights = None
        phase_bonuses = None
        if config.phases and current_phase in config.phases:
            phase_weights = config.phases[current_phase].signal_weights
            phase_bonuses = config.phases[current_phase].phase_bonuses
            log.debug(
                "phase_weights_loaded",
                phase=current_phase,
                weights=phase_weights,
                bonuses=phase_bonuses,
            )

        # Get strategies from config
        strategies = config.strategies

        if not strategies:
            log.error(
                "no_strategies_defined",
                methodology=methodology_name,
                exc_info=True,
            )
            raise ConfigurationError(
                f"No strategies defined for methodology '{methodology_name}'. "
                f"Check the methodology YAML configuration in src/methodologies/config/ "
                f"to ensure at least one strategy is defined under the 'strategies' key."
            )

        # Score all (strategy, node) pairs using joint scoring
        scored_pairs = rank_strategy_node_pairs(
            strategies=strategies,
            global_signals=global_signals,
            node_signals=node_signals,
            node_tracker=node_tracker,
            phase_weights=phase_weights,
            phase_bonuses=phase_bonuses,
            signal_norms=config.signal_norms,
        )

        if not scored_pairs:
            log.error(
                "no_scored_pairs",
                methodology=methodology_name,
                strategy_count=len(strategies),
                node_count=len(node_signals),
                exc_info=True,
            )
            raise ScoringError(
                f"No valid (strategy, node) pairs could be scored for methodology '{methodology_name}'. "
                f"Strategies available: {len(strategies)}, Nodes with signals: {len(node_signals)}. "
                f"Check that signal weights and strategy configurations are valid. "
                f"Node signals may be empty if no nodes are being tracked by NodeStateTracker."
            )

        # Select best pair
        best_strategy_config, best_node_id, best_score = scored_pairs[0]

        # Build alternatives for observability (include node_id)
        alternatives = [(s.name, node_id, score) for s, node_id, score in scored_pairs]

        log.info(
            "strategy_and_node_selected",
            methodology=methodology_name,
            strategy=best_strategy_config.name,
            node_id=best_node_id,
            score=best_score,
            alternatives_count=len(alternatives),
            top_3_alternatives=alternatives[:3],
        )

        return best_strategy_config.name, best_node_id, alternatives, global_signals

    async def _detect_node_signals(
        self,
        config: Any,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
        node_tracker: "NodeStateTracker",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect node-level signals for all tracked nodes.

        Args:
            config: Methodology config
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text
            node_tracker: NodeStateTracker instance

        Returns:
            Dict mapping node_id to dict of signal_name: value
        """
        from src.methodologies.signals.graph.node_exhaustion import (
            NodeExhaustedSignal,
            NodeExhaustionScoreSignal,
            NodeYieldStagnationSignal,
        )
        from src.methodologies.signals.graph.node_engagement import (
            NodeFocusStreakSignal,
            NodeIsCurrentFocusSignal,
            NodeRecencyScoreSignal,
        )
        from src.methodologies.signals.graph.node_relationships import (
            NodeIsOrphanSignal,
            NodeEdgeCountSignal,
            NodeHasOutgoingSignal,
        )
        from src.methodologies.signals.technique.node_strategy_repetition import (
            NodeStrategyRepetitionSignal,
        )

        # Get all tracked nodes
        all_states = node_tracker.get_all_states()

        if not all_states:
            log.debug("no_tracked_nodes_for_signals")
            return {}

        # Initialize node signals dict
        node_signals: Dict[str, Dict[str, Any]] = {
            node_id: {} for node_id in all_states.keys()
        }

        # List of node signal detectors to run
        # These detectors take node_tracker in their constructor
        signal_detectors = [
            NodeExhaustedSignal(node_tracker),
            NodeExhaustionScoreSignal(node_tracker),
            NodeYieldStagnationSignal(node_tracker),
            NodeFocusStreakSignal(node_tracker),
            NodeIsCurrentFocusSignal(node_tracker),
            NodeRecencyScoreSignal(node_tracker),
            NodeIsOrphanSignal(node_tracker),
            NodeEdgeCountSignal(node_tracker),
            NodeHasOutgoingSignal(node_tracker),
            NodeStrategyRepetitionSignal(node_tracker),
        ]

        # Detect all node signals
        for detector in signal_detectors:
            try:
                detected = await detector.detect(context, graph_state, response_text)

                # Merge results into node_signals
                for node_id, signal_value in detected.items():
                    if node_id in node_signals:
                        node_signals[node_id][detector.signal_name] = signal_value

            except Exception as e:
                log.error(
                    "node_signal_detection_failed",
                    signal=detector.signal_name,
                    error=str(e),
                    exc_info=True,
                )
                raise ScorerFailureError(
                    f"Node signal detector '{detector.signal_name}' failed during detection. "
                    f"Original error: {type(e).__name__}: {e}. "
                    f"Check that the signal detector is properly configured and "
                    f"that all required data (context, graph_state, node_tracker) is available."
                ) from e

        return node_signals
