"""
Strategy selection service using YAML-based methodology configs.

Uses signal pools and YAML configs for methodology-specific strategy selection.
"""

from typing import List, Tuple, Optional, TYPE_CHECKING, Any, Dict
import structlog

from src.methodologies import get_registry
from src.methodologies.scoring import rank_strategies
from src.services.focus_selection_service import (
    FocusSelectionService,
    FocusSelectionInput,
)

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext

log = structlog.get_logger(__name__)


class MethodologyStrategyService:
    """Strategy selection using YAML methodology configs.

    This service uses:
    - YAML configs for methodology definitions (signals + strategies)
    - Composed signal detectors from shared pools
    - FocusSelectionService for focus selection
    """

    def __init__(self):
        """Initialize service with registries."""
        self.methodology_registry = get_registry()
        self.focus_service = FocusSelectionService()

    async def select_strategy(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> Tuple[str, Optional[str], List[Tuple[str, float]], Optional[Dict[str, Any]]]:
        """
        Select best strategy for current context.

        This method:
        1. Loads methodology config from YAML
        2. Detects signals using composed signal detector
        3. Scores strategies using YAML-defined weights
        4. Selects focus using FocusSelectionService
        5. Returns best strategy with focus and alternatives

        Args:
            context: Pipeline context with methodology, recent_turns, etc.
            graph_state: Current knowledge graph state
            response_text: User's response text for signal analysis

        Returns:
            Tuple of (strategy_name, focus_node, alternatives, signals)
            - strategy_name: Name of selected strategy
            - focus_node: Optional focus node/label for strategy execution
            - alternatives: List of (strategy_name, score) for observability
            - signals: Optional dict of detected signals for observability
        """
        # Get methodology config from YAML
        methodology_name = (
            context.methodology if context.methodology else "means_end_chain"
        )
        config = self.methodology_registry.get_methodology(methodology_name)

        if not config:
            log.warning(
                "methodology_not_found",
                name=methodology_name,
                available=self.methodology_registry.list_methodologies(),
            )
            # Fallback to default strategy
            return "deepen", None, [], None

        # Create signal detector and detect signals
        signal_detector = self.methodology_registry.create_signal_detector(config)
        signals = await signal_detector.detect(context, graph_state, response_text)

        log.debug(
            "signals_detected",
            methodology=methodology_name,
            signals=signals,
        )

        # Get strategies from config
        strategies = config.strategies

        if not strategies:
            log.warning(
                "no_strategies_defined",
                methodology=methodology_name,
            )
            # Fallback
            return "deepen", None, [], signals

        # Rank strategies by signal scores
        ranked = rank_strategies(strategies, signals)

        # Select best strategy
        best_strategy_config, best_score = ranked[0]

        # Get focus using FocusSelectionService
        focus_input = FocusSelectionInput(
            strategy=best_strategy_config.name,
            graph_state=graph_state,
            recent_nodes=context.recent_nodes
            if hasattr(context, "recent_nodes")
            else [],
            signals=signals,
        )
        focus = await self.focus_service.select(focus_input)

        # Build alternatives for observability
        alternatives = [(s.name, score) for s, score in ranked]

        log.info(
            "strategy_selected",
            methodology=methodology_name,
            strategy=best_strategy_config.name,
            score=best_score,
            focus=focus,
            alternatives_count=len(alternatives),
            top_3_alternatives=alternatives[:3],
        )

        return best_strategy_config.name, focus, alternatives, signals
