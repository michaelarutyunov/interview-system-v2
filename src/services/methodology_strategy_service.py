"""
Strategy selection service using methodology-specific modules.

Replaces the two-tier scoring system with direct signal->strategy scoring.

This service integrates with the methodology modules created in Phases 2 and 3
to provide strategy selection based on methodology-specific signals.
"""

from typing import List, Tuple, Optional, TYPE_CHECKING, Any, Dict
import structlog

from src.methodologies import get_methodology
from src.methodologies.scoring import rank_strategies

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext

log = structlog.get_logger(__name__)


class MethodologyStrategyService:
    """Strategy selection using methodology modules.

    This service replaces the two-tier scoring engine with a cleaner,
    methodology-specific approach where each methodology defines its own
    signals and strategies with direct signal->strategy scoring.
    """

    async def select_strategy(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> Tuple[str, Optional[str], List[Tuple[str, float]], Optional[Dict[str, Any]]]:
        """
        Select best strategy for current context.

        This method:
        1. Detects signals using the methodology-specific signal detector
        2. Scores all strategies using the methodology-specific scoring
        3. Returns the best strategy with focus and alternatives for observability

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
        # Get methodology module
        methodology_name = (
            context.methodology.name if context.methodology else "means_end_chain"
        )
        module = get_methodology(methodology_name)

        if not module:
            log.warning(
                "methodology_not_found",
                name=methodology_name,
                available=self._list_available(),
            )
            # Fallback to default strategy
            return "ladder_deeper", None, [], None

        # Detect signals
        signal_detector = module.get_signal_detector()
        signals = await signal_detector.detect(context, graph_state, response_text)

        # Convert signals to dict for observability
        signals_dict = (
            signals.model_dump() if hasattr(signals, "model_dump") else dict(signals)
        )

        log.debug(
            "signals_detected",
            methodology=methodology_name,
            signals=signals_dict,
        )

        # Get strategies for this methodology
        strategies = module.get_strategies()

        if not strategies:
            log.warning(
                "no_strategies_defined",
                methodology=methodology_name,
            )
            # Fallback
            return "ladder_deeper", None, [], signals_dict

        # Rank strategies by signal scores
        ranked = rank_strategies(strategies, signals)

        # Select best strategy
        best_strategy_class, best_score = ranked[0]

        # Get focus for selected strategy
        strategy_instance = best_strategy_class()
        focus = await strategy_instance.generate_focus(context, graph_state)

        # Build alternatives for observability
        alternatives = [(s.name, score) for s, score in ranked]

        log.info(
            "strategy_selected",
            methodology=methodology_name,
            strategy=best_strategy_class.name,
            score=best_score,
            focus=focus,
            alternatives_count=len(alternatives),
            top_3_alternatives=alternatives[:3],
        )

        return best_strategy_class.name, focus, alternatives, signals_dict

    def _list_available(self) -> List[str]:
        """List available methodologies for error messages."""
        from src.methodologies import list_methodologies

        return list_methodologies()
