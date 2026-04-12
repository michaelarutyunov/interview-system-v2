"""Strategy selection service using joint scoring architecture.

Implements joint strategy-node selection where all eligible (strategy, node)
pairs are scored simultaneously using combined global and node signals.

Key concepts:
- Joint scoring: All (strategy, node) pairs scored together, best pair wins
- Phase weights: Multiplicative signal weights per interview phase (early/mid/late)
- Phase bonuses: Additive strategy bonuses per interview phase
- Node exhaustion: Penalty for over-probing the same node
- Signal pools: Shared signal detectors (graph, llm, temporal, meta)
"""

from typing import Tuple, Optional, TYPE_CHECKING, Any, Dict
import structlog

from src.core.exceptions import ConfigurationError, ScoringError
from src.methodologies import get_registry
from src.methodologies.scoring import (
    rank_strategies,
    rank_strategy_node_pairs,
    ScoredCandidate,
)
from src.services.global_signal_detection_service import GlobalSignalDetectionService
from src.services.node_signal_detection_service import NodeSignalDetectionService
from src.signals.meta.interview_phase import InterviewPhaseSignal

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext
    from src.services.node_state_tracker import NodeStateTracker

log = structlog.get_logger(__name__)


class MethodologyStrategyService:
    """Strategy selection service using joint scoring architecture.

    Evaluates all eligible (strategy, node) pairs simultaneously and selects
    the globally highest-scoring pair. Node-bound strategies (node_binding='required')
    are scored via rank_strategy_node_pairs(); conversation strategies
    (node_binding='none') are scored via rank_strategies() with node_id=None.

    Signal detection is delegated to specialized services:
    - GlobalSignalDetectionService: graph.*, llm.*, temporal.*, meta.* signals
    - NodeSignalDetectionService: graph.node.*, technique.node.* signals per node
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
        self.global_signal_service = (
            global_signal_service or GlobalSignalDetectionService()
        )
        self.node_signal_service = node_signal_service or NodeSignalDetectionService()

    async def select_strategy_and_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> Tuple[
        str,
        Optional[str],
        list[tuple[str, Optional[str], float]],
        Optional[Dict[str, Any]],
        Dict[str, Dict[str, Any]],
        list[ScoredCandidate],
    ]:
        """Select best (strategy, node) pair using joint scoring with phase weights.

        Evaluates all eligible (strategy, node) pairs by combining global signals
        with node-level signals. Selects the globally highest-scoring pair.

        Detection flow:
        1. Detect global signals (llm.response_depth, graph.*, temporal.*)
        2. Detect node-level signals (graph.node.exhausted, meta.node.opportunity)
        3. Detect interview phase (early/mid/late) for phase weights/bonuses
        4. Score all eligible (strategy, node) pairs using combined signals
        5. Select highest-scoring pair

        Args:
            context: Pipeline context with methodology, node_tracker, recent_utterances
            graph_state: Current knowledge graph state with node/edge counts
            response_text: User's response text for LLM signal analysis

        Returns:
            Tuple of (strategy_name, focus_node_id, alternatives, global_signals,
            node_signals, decomposition):
            - strategy_name: Name of selected strategy
            - focus_node_id: UUID of selected focus node, or None for conversation strategies
            - alternatives: List of (strategy, node_id_or_None, score) tuples sorted by score
            - global_signals: Dict of detected global signals
            - node_signals: Dict mapping node_id to per-node signal dict
            - decomposition: List of ScoredCandidate with per-signal breakdown

        Raises:
            ConfigurationError: If methodology not found or has no strategies defined
            ValueError: If node_tracker is not available in context
            ScoringError: If no valid (strategy, node) pairs can be scored
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

        # Expose current-turn global signals on context so node-level detectors
        # (e.g. meta.node.opportunity) can read llm.response_depth for the
        # *current* turn rather than the stale previous-turn context.signals.
        # This attribute is ephemeral — set here, consumed during node detection,
        # not persisted to any contract output.
        context.current_turn_global_signals = global_signals

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

        # --- Joint scoring: evaluate all eligible (strategy, node) pairs ---

        # Partition strategies by node_binding
        node_bound_strategies = [s for s in strategies if s.node_binding == "required"]
        conversation_strategies = [s for s in strategies if s.node_binding == "none"]

        all_ranked: list[tuple[Any, Optional[str], float]] = []
        all_decomposition: list[ScoredCandidate] = []

        # Score node-bound strategies via joint scoring
        if node_bound_strategies:
            ranked_pairs, pair_decomposition = rank_strategy_node_pairs(
                node_bound_strategies,
                global_signals,
                node_signals,
                node_tracker=node_tracker,
                phase_weights=phase_weights,
                phase_bonuses=phase_bonuses,
            )
            all_ranked.extend(ranked_pairs)
            all_decomposition.extend(pair_decomposition)

            log.info(
                "joint_scoring_complete",
                methodology=methodology_name,
                node_bound_count=len(node_bound_strategies),
                pairs_scored=len(ranked_pairs),
            )

        # Score conversation strategies via global-only scoring
        if conversation_strategies:
            ranked_conv, conv_decomposition = rank_strategies(
                conversation_strategies,
                global_signals,
                phase_weights=phase_weights,
                phase_bonuses=phase_bonuses,
                return_decomposition=True,
            )
            # Convert (StrategyConfig, score) → (StrategyConfig, None, score)
            for strat, score in ranked_conv:
                all_ranked.append((strat, None, score))
            all_decomposition.extend(conv_decomposition)

            log.info(
                "conversation_scoring_complete",
                methodology=methodology_name,
                conversation_count=len(conversation_strategies),
            )

        # Sort merged candidates by score descending
        all_ranked.sort(key=lambda x: x[2], reverse=True)

        if not all_ranked:
            log.error(
                "no_ranked_candidates",
                methodology=methodology_name,
                node_bound_count=len(node_bound_strategies),
                conversation_count=len(conversation_strategies),
                exc_info=True,
            )
            raise ScoringError(
                f"No valid (strategy, node) pairs could be scored for "
                f"methodology '{methodology_name}'. "
                f"Node-bound strategies: {len(node_bound_strategies)}, "
                f"Conversation strategies: {len(conversation_strategies)}."
            )

        best_strategy_config, best_node_id, best_score = all_ranked[0]

        # --- Threshold fallback check ---
        score_threshold = 0.0
        if config.chain_completion and isinstance(config.chain_completion, dict):
            score_threshold = float(
                config.chain_completion.get("score_threshold", 0.0)
            )

        if best_score < score_threshold:
            global_fatigue = global_signals.get("llm.global_response_trend") == "fatigued"
            engagement = global_signals.get("llm.engagement", 1.0)
            low_engagement = isinstance(engagement, (int, float)) and engagement < 0.3

            fallback_strategy_name: str | None = None
            if global_fatigue or low_engagement:
                fallback_strategy_name = "revitalize"

            if fallback_strategy_name:
                # Find the fallback in the ranked list
                fallback_pair = next(
                    (
                        (s, nid, sc)
                        for s, nid, sc in all_ranked
                        if s.name == fallback_strategy_name
                    ),
                    None,
                )
                if fallback_pair:
                    log.info(
                        "strategy_threshold_fallback",
                        methodology=methodology_name,
                        best_score=best_score,
                        threshold=score_threshold,
                        fallback_strategy=fallback_strategy_name,
                        reason="global_fatigue_or_low_engagement",
                    )
                    best_strategy_config, best_node_id, best_score = fallback_pair
                else:
                    log.debug(
                        "strategy_threshold_below_but_no_fallback",
                        methodology=methodology_name,
                        best_score=best_score,
                        threshold=score_threshold,
                    )

        # Assign rank and selected flags to decomposition
        ranked_order = {
            (s.name, nid): i
            for i, (s, nid, _) in enumerate(all_ranked)
        }
        for candidate in all_decomposition:
            key = (candidate.strategy, candidate.node_id if candidate.node_id else None)
            rank = ranked_order.get(key, len(all_ranked))
            candidate.rank = rank + 1
            candidate.selected = rank == 0

        # Build alternatives as uniform 3-tuples
        alternatives = [(s.name, nid, score) for s, nid, score in all_ranked]

        focus_node_id = best_node_id

        log.info(
            "strategy_selected",
            methodology=methodology_name,
            strategy=best_strategy_config.name,
            node_id=focus_node_id,
            score=best_score,
            node_binding=best_strategy_config.node_binding,
            alternatives_count=len(alternatives),
            top_3_alternatives=alternatives[:3],
            decomposition_count=len(all_decomposition),
        )

        return (
            best_strategy_config.name,
            focus_node_id,
            alternatives,
            global_signals,
            node_signals,
            all_decomposition,
        )
