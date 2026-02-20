"""
Stage 6: Select strategy.

Selects questioning strategy using methodology-based signal detection with
direct signal-to-strategy scoring. Validates graph_state freshness before
selection to prevent stale state bugs.
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, Sequence, Union

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import (
    StrategySelectionInput,
    StrategySelectionOutput,
)
from src.services.methodology_strategy_service import MethodologyStrategyService


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class StrategySelectionStage(TurnStage):
    """
    Select questioning strategy using methodology-based signal detection.

    Uses MethodologyStrategyService for direct signal-to-strategy scoring based
    on graph state, recent nodes, and conversation history.

    Populates:
    - PipelineContext.strategy
    - PipelineContext.selection_result (None for methodology-based selection)
    - PipelineContext.focus
    - PipelineContext.signals (methodology-specific signals)
    - PipelineContext.strategy_alternatives (for observability)
    """

    def __init__(self):
        """
        Initialize stage with methodology-based strategy service.

        Note: Strategy selection uses methodology-specific signal detection
        configured in YAML (config/methodologies/*.yaml).
        """
        self.methodology_strategy = MethodologyStrategyService()

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Select strategy using methodology-based signal detection.

        Validates graph_state freshness before selection to prevent stale
        state bugs. Uses methodology-specific signals and direct signal-to-
        strategy scoring.

        Args:
            context: Turn context with graph_state, recent_nodes, recent_utterances

        Returns:
            Modified context with strategy, selection_result, focus, signals, and alternatives
        """
        # Pipeline stage order validation: StateComputationStage (Stage 5) must run first
        if context.state_computation_output is None:
            raise RuntimeError(
                "Pipeline stage order violation: StrategySelectionStage (Stage 6) "
                "requires StateComputationStage (Stage 5) to have run first. "
                "state_computation_output is None."
            )

        # Validate freshness before using graph_state
        # This prevents the stale state bug where graph_state from Stage 1
        # (before extraction) was used in Stage 6
        if context.graph_state and context.graph_state_computed_at:
            try:
                # Create StrategySelectionInput to validate freshness
                # This will raise ValidationError if state is stale
                selection_input = StrategySelectionInput(
                    graph_state=context.graph_state,
                    recent_nodes=context.recent_nodes,
                    extraction=context.extraction,  # type: ignore
                    conversation_history=context.recent_utterances,
                    turn_number=context.turn_number,
                    mode=context.mode,
                    computed_at=context.graph_state_computed_at,
                )
                log.debug(
                    "graph_state_freshness_validated",
                    session_id=context.session_id,
                    computed_at=selection_input.computed_at,
                )
            except Exception as e:
                # Freshness validation failed - state is stale
                log.error(
                    "graph_state_freshness_validation_failed",
                    session_id=context.session_id,
                    error=str(e),
                )
                # For now, log and continue - in future we might want to
                # re-compute state or use fallback behavior
                raise

        # Select strategy using methodology-based signal detection
        (
            strategy,
            focus_node_id,
            alternatives,
            signals,
            node_signals,
        ) = await self._select_strategy_and_node(context)

        # Update node_tracker with the new focus (sets previous_focus for next turn)
        # This must be done AFTER response depth append (which uses previous_focus)
        # and BEFORE the next turn starts
        if context.node_tracker and focus_node_id:
            await context.node_tracker.update_focus(
                node_id=focus_node_id,
                strategy=strategy,
                turn_number=context.turn_number,
            )

        # Track strategy history for diversity tracking
        # This enables the system to avoid repetitive questioning patterns
        if context.graph_state:
            context.graph_state.add_strategy_used(strategy)

        # Wrap node_id in dict format for ContinuationStage compatibility
        focus_dict = {"focus_node_id": focus_node_id} if focus_node_id else None

        # Look up generates_closing_question flag for the selected strategy
        methodology_config = (
            self.methodology_strategy.methodology_registry.get_methodology(
                context.methodology
            )
        )
        generates_closing_question = next(
            (
                s.generates_closing_question
                for s in methodology_config.strategies
                if s.name == strategy
            ),
            False,
        )

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        context.strategy_selection_output = StrategySelectionOutput(
            strategy=strategy,
            focus=focus_dict,
            # selected_at auto-set
            signals=signals,
            node_signals=node_signals,
            strategy_alternatives=list(alternatives) if alternatives else [],
            generates_closing_question=generates_closing_question,
        )

        log.info(
            "strategy_selected",
            session_id=context.session_id,
            strategy=strategy,
            focus_node_id=focus_node_id,
            has_methodology_signals=signals is not None,
            alternatives_count=len(alternatives) if alternatives else 0,
        )

        return context

    async def _select_strategy_and_node(
        self,
        context: "PipelineContext",
    ) -> tuple[
        str,
        Optional[str],
        Sequence[Union[tuple[str, float], tuple[str, str, float]]],
        Optional[Dict[str, Any]],
        Dict[str, Dict[str, Any]],
    ]:
        """
        Select strategy and focus node using joint scoring.

        Uses MethodologyStrategyService.select_strategy_and_focus() for
        joint (strategy, node) scoring.

        Args:
            context: Turn context

        Returns:
            Tuple of (strategy_name, focus_node_id, alternatives, signals)
            - alternatives includes (strategy_name, node_id, score) tuples
        """
        # Get last response text
        response_text = context.user_input or ""

        # Use joint strategy-node scoring
        # graph_state should be available after StateComputationStage
        if context.graph_state is None:
            raise ValueError(
                "Pipeline contract violation: graph_state must be set by "
                "StateComputationStage before StrategySelectionStage"
            )

        # Call new joint scoring method
        (
            strategy_name,
            focus_node_id,
            alternatives,
            signals,
            node_signals,
        ) = await self.methodology_strategy.select_strategy_and_focus(
            context,
            context.graph_state,
            response_text,
        )

        # Update node_tracker with response depth from the detected signals
        # The response_depth belongs to the focus node from the PREVIOUS turn
        # (the node that was asked about when generating the question this response answers)
        log.info(
            "response_depth_append_check",
            has_signals=bool(signals),
            has_node_tracker=bool(context.node_tracker),
            has_previous_focus=bool(
                context.node_tracker and context.node_tracker.previous_focus
            ),
            previous_focus=context.node_tracker.previous_focus
            if context.node_tracker
            else None,
        )
        if signals and context.node_tracker and context.node_tracker.previous_focus:
            response_depth = signals.get("llm.response_depth")
            if response_depth:
                await context.node_tracker.append_response_signal(
                    context.node_tracker.previous_focus,
                    response_depth,
                )
                log.info(
                    "response_depth_appended_to_node",
                    node_id=context.node_tracker.previous_focus,
                    response_depth=response_depth,
                )

        # Convert alternatives from (strategy, node_id, score) to (strategy, score)
        # for backward compatibility with logging
        # The full alternatives are still available in context for debugging
        simplified_alternatives = []
        seen_strategies = set()
        for alt in alternatives:
            # Handle both 2-tuple and 3-tuple formats
            if len(alt) == 3:
                alt_strategy, _alt_node_id, alt_score = alt
            else:
                alt_strategy, alt_score = alt

            if alt_strategy not in seen_strategies:
                simplified_alternatives.append((alt_strategy, alt_score))
                seen_strategies.add(alt_strategy)

        return (
            strategy_name,
            focus_node_id,
            simplified_alternatives,
            signals,
            node_signals,
        )
