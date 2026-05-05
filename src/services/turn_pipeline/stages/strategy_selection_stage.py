"""
Stage 6: Select strategy.

Selects questioning strategy using methodology-based signal detection with
direct signal-to-strategy scoring. Validates graph_state freshness before
selection to prevent stale state bugs.
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import (
    StrategySelectionInput,
    StrategySelectionOutput,
)
from src.domain.models.identity import SurfaceNodeId
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
            score_decomposition,
        ) = await self._select_strategy_and_node(context)

        # Compute next_turn_node_tracker: sealed tracker + update_focus applied.
        # This is persisted to DB so the NEXT turn starts with the correct previous_focus.
        sealed = context.node_tracker
        next_turn_tracker = sealed
        if focus_node_id:
            # focus_node_id is a surface UUID — directly usable as the tracker key.
            tracking_key = SurfaceNodeId(focus_node_id)
            if tracking_key in sealed.states:
                next_turn_tracker = sealed.update_focus(
                    tracking_key=tracking_key,
                    strategy=strategy,
                    turn_number=context.turn_number,
                )
            else:
                log.warning(
                    "focus_update_skipped_node_not_tracked",
                    focus_node_id=focus_node_id,
                    tracking_key=tracking_key,
                    turn_number=context.turn_number,
                )

        # Track strategy history for diversity tracking
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
        selected_config = next(
            (s for s in methodology_config.strategies if s.name == strategy),
            None,
        )
        generates_closing_question = (
            selected_config.generates_closing_question if selected_config else False
        )
        focus_mode = selected_config.focus_mode if selected_config else "recent_node"

        context.strategy_selection_output = StrategySelectionOutput(
            strategy=strategy,
            focus=focus_dict,
            signals=signals,
            node_signals=node_signals,
            strategy_alternatives=list(alternatives) if alternatives else [],
            generates_closing_question=generates_closing_question,
            focus_mode=focus_mode,
            score_decomposition=score_decomposition,
            next_turn_node_tracker=next_turn_tracker,
        )

        log.info(
            "strategy_selected",
            session_id=context.session_id,
            strategy=strategy,
            focus_node_id=focus_node_id,
            has_methodology_signals=signals is not None,
            alternatives_count=len(alternatives) if alternatives else 0,
        )

        # Preventative: monoculture detector. Same strategy winning ≥3 turns in a row
        # is the canonical signature of base-score-vs-brake asymmetry (CIT revitalize,
        # CJM deepen_stage). See CLAUDE.md known failures #10/#11.
        prior = list(context.strategy_history or [])
        streak = 1
        for past in reversed(prior):
            if past == strategy:
                streak += 1
            else:
                break
        if streak >= 3:
            runner_up_gap: Optional[float] = None
            if alternatives and len(alternatives) >= 2:
                top = (
                    alternatives[0].get("score")
                    if isinstance(alternatives[0], dict)
                    else None
                )
                second = (
                    alternatives[1].get("score")
                    if isinstance(alternatives[1], dict)
                    else None
                )
                if isinstance(top, (int, float)) and isinstance(second, (int, float)):
                    runner_up_gap = round(float(top) - float(second), 4)
            log.warning(
                "strategy_monoculture_detected",
                session_id=context.session_id,
                strategy=strategy,
                streak=streak,
                runner_up_gap=runner_up_gap,
                hint=(
                    "same strategy ≥3 consecutive turns; check repetition brake "
                    "magnitude vs. base score (CLAUDE.md failure modes #10/#11)."
                ),
            )

        return context

    async def _select_strategy_and_node(
        self,
        context: "PipelineContext",
    ) -> tuple[
        str,
        Optional[str],
        List[Dict[str, Any]],
        Optional[Dict[str, Any]],
        Dict[str, Dict[str, Any]],
        list,
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
            score_decomposition,
        ) = await self.methodology_strategy.select_strategy_and_focus(
            context,
            context.graph_state,
            response_text,
        )

        # Note: per-concept quality (elaboration/charge → response_depth) is routed
        # by LLMSignalBridgeStage (Stage 4.7) into NodeStateTracker.append_quality
        # for each extracted concept's node. LLM global signals are merged by
        # GlobalSignalDetectionService.detect() from the Stage 4.7 contract.
        # The previous bridge in MethodologyStrategyService has been removed.

        # Alternatives are already (strategy_name, score) tuples from two-stage selection
        return (
            strategy_name,
            focus_node_id,
            alternatives,
            signals,
            node_signals,
            score_decomposition,
        )
