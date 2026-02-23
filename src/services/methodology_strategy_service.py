"""Strategy selection service using YAML-based methodology configs with joint scoring.

Implements D1 architecture for joint strategy-node scoring with signal pools,
phase weights, and node exhaustion detection. Delegates signal detection to
specialized services for single responsibility.

Domain decomposition:
- GlobalSignalDetectionService: Detects graph/LLM/temporal signals from response
- NodeSignalDetectionService: Detects node-level signals with exhaustion tracking

Key concepts:
- Joint strategy-node scoring: Scores (strategy, node) pairs using combined signals
- Phase weights: Multiplicative signal weights per interview phase (early/mid/late)
- Phase bonuses: Additive strategy bonuses per interview phase
- Node exhaustion: Penalty for over-probing the same node
- Signal pools: Shared signal detectors (graph, llm, temporal, meta)
"""

from typing import Tuple, Optional, TYPE_CHECKING, Any, Dict, Union, Sequence
import structlog

from src.core.exceptions import ConfigurationError, ScoringError
from src.methodologies import get_registry
from src.methodologies.scoring import rank_strategy_node_pairs, ScoredCandidate
from src.services.global_signal_detection_service import GlobalSignalDetectionService
from src.services.node_signal_detection_service import NodeSignalDetectionService

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext
    from src.services.node_state_tracker import NodeStateTracker

log = structlog.get_logger(__name__)


class MethodologyStrategyService:
    """Joint strategy-node scoring service using methodology YAML configs.

    Orchestrates D1 architecture for strategy selection by combining global
    signals (graph state, response depth) with node-level signals (exhaustion,
    opportunity) to score (strategy, node) pairs. Applies phase-based weights
    (multiplicative) and bonuses (additive) for adaptive interviewing.

    Signal detection is delegated to specialized services:
    - GlobalSignalDetectionService: graph.*, llm.*, temporal.*, meta.* signals
    - NodeSignalDetectionService: graph.node.*, technique.node.* signals per node

    The service uses methodology configs from YAML files in config/methodologies/
    which define signals, strategies, and phase-specific weights/bonuses.
    """

    def __init__(
        self,
        global_signal_service: Optional[GlobalSignalDetectionService] = None,
        node_signal_service: Optional[NodeSignalDetectionService] = None,
    ):
        """Initialize service with methodology registry and signal detection services.

        Uses dependency injection for signal detection services to support testing
        and flexible composition. Creates default instances if not provided.

        Args:
            global_signal_service: Service for detecting global signals (graph,
                llm, temporal, meta). If None, creates GlobalSignalDetectionService.
            node_signal_service: Service for detecting node-level signals
                (exhaustion, opportunity). If None, creates NodeSignalDetectionService.

        Attributes:
            methodology_registry: Loaded YAML methodology configs from get_registry()
            global_signal_service: Detects methodology-specific global signals
            node_signal_service: Detects node-specific signals per tracked node
        """
        self.methodology_registry = get_registry()
        # Use injected services or create defaults
        self.global_signal_service = global_signal_service or GlobalSignalDetectionService()
        self.node_signal_service = node_signal_service or NodeSignalDetectionService()

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
        Dict[str, Dict[str, Any]],
        list[ScoredCandidate],
    ]:
        """Select best (strategy, node) pair using joint scoring with phase weights.

        Implements D1 architecture for strategy selection by combining global
        signals (response depth, graph metrics) with node-level signals
        (exhaustion, opportunity) to score all (strategy, node) pairs.
        Applies phase-based weights (multiplicative) and bonuses (additive)
        for adaptive interview behavior.

        Detection flow:
        1. Detect global signals (llm.response_depth, graph.*, temporal.*)
        2. Detect node-level signals (graph.node.exhausted, meta.node.opportunity)
        3. Detect interview phase (early/mid/late) for phase weights/bonuses
        4. Score all (strategy, node) pairs using combined signals
        5. Select highest-scoring pair

        Args:
            context: Pipeline context with methodology, node_tracker, recent_utterances
            graph_state: Current knowledge graph state with node/edge counts
            response_text: User's response text for LLM signal analysis

        Returns:
            Tuple of (strategy_name, focus_node_id, alternatives, global_signals, node_signals):
            - strategy_name: Name of selected strategy from YAML config
            - focus_node_id: ID of selected focus node (UUID, not label)
            - alternatives: List of (strategy_name, node_id, score) tuples for
                observability and debugging, sorted by score descending
            - global_signals: Dict of detected global signals (e.g.,
                {"llm.response_depth": "deep", "graph.node_count": 42})
            - node_signals: Dict mapping node_id to per-node signal dict

        Raises:
            ConfigurationError: If methodology not found or has no strategies defined
            ValueError: If node_tracker is not available in context
            ScoringError: If no valid (strategy, node) pairs can be scored
        """
        # Get methodology config from YAML
        methodology_name = context.methodology if context.methodology else "means_end_chain"
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

        # Detect global signals (delegated to GlobalSignalDetectionService)
        global_signals = await self.global_signal_service.detect(
            methodology_name=methodology_name,
            context=context,
            graph_state=graph_state,
            response_text=response_text,
        )

        log.debug(
            "global_signals_detected",
            methodology=methodology_name,
            signals=global_signals,
        )

        # Detect node-level signals (delegated to NodeSignalDetectionService)
        node_signals = await self.node_signal_service.detect(
            context=context,
            graph_state=graph_state,
            response_text=response_text,
            node_tracker=node_tracker,
        )

        log.debug(
            "node_signals_detected",
            methodology=methodology_name,
            node_count=len(node_signals),
        )

        # Detect interview phase
        from src.signals.meta.interview_phase import (
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
        scored_pairs, score_decomposition = rank_strategy_node_pairs(
            strategies=strategies,
            global_signals=global_signals,
            node_signals=node_signals,
            node_tracker=node_tracker,
            phase_weights=phase_weights,
            phase_bonuses=phase_bonuses,
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

        return (
            best_strategy_config.name,
            best_node_id,
            alternatives,
            global_signals,
            node_signals,
            score_decomposition,
        )
