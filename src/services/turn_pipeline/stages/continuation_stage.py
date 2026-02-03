"""
Stage 7: Determine continuation.

ADR-008 Phase 3: Decide if interview should continue or end.
Phase 6: Output ContinuationOutput contract.
Domain Encapsulation:
- Focus selection delegated to FocusSelectionService
- Saturation metrics read from StateComputationOutput (computed by Stage 5)
  This stage is now a pure consumer of pre-computed metrics.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import ContinuationOutput
from src.domain.models.knowledge_graph import SaturationMetrics
from src.services.focus_selection_service import FocusSelectionService


if TYPE_CHECKING:
    from ..context import PipelineContext
    from src.services.question_service import QuestionService
log = structlog.get_logger(__name__)

# =============================================================================
# Continuation thresholds
# =============================================================================
MIN_TURN_FOR_SATURATION = 5  # Don't check saturation before this turn
NODE_EXHAUSTION_YIELD_GAP = 3  # turns_since_last_yield to consider exhausted


class ContinuationStage(TurnStage):
    """
    Determine if interview should continue.

    Populates PipelineContext.should_continue and PipelineContext.focus_concept.

    Domain Encapsulation: Saturation metrics are now computed by
    StateComputationStage (Stage 5) and read from context.saturation_metrics.
    This stage only reads the computed values and makes continuation decisions.
    """

    def __init__(
        self,
        question_service: "QuestionService",
        focus_selection_service: FocusSelectionService,
    ):
        """
        Initialize stage.

        Args:
            question_service: QuestionService instance (used for legacy compatibility)
            focus_selection_service: FocusSelectionService for focus resolution
        """
        self.question = question_service
        self.focus_selection = focus_selection_service

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Determine if we should continue and select focus concept.

        Args:
            context: Turn context with turn_number, max_turns, graph_state, strategy

        Returns:
            Modified context with should_continue and focus_concept
        """
        # Determine if we should continue (reads saturation from context)
        should_continue, reason = self._should_continue(context)

        # Select focus concept if continuing
        # All focus selection is delegated to FocusSelectionService
        if should_continue:
            focus_concept = self.focus_selection.resolve_focus_from_strategy_output(
                focus_dict=context.focus,
                recent_nodes=context.recent_nodes,
                strategy=context.strategy,
                graph_state=context.graph_state,
            )
        else:
            focus_concept = ""

        # Create contract output (single source of truth)
        context.continuation_output = ContinuationOutput(
            should_continue=should_continue,
            focus_concept=focus_concept,
            reason=reason,
            turns_remaining=max(0, context.max_turns - context.turn_number),
        )

        # Get phase from signal for logging (unified source of truth)
        current_phase = None
        phase_reason = None
        if context.signals:
            current_phase = context.signals.get("meta.interview.phase")
            phase_reason = context.signals.get("meta.interview.phase_reason")

        log.info(
            "continuation_determined",
            session_id=context.session_id,
            should_continue=should_continue,
            focus_concept=focus_concept if should_continue else None,
            phase=current_phase,
            phase_reason=phase_reason,
            reason=reason if reason else None,
        )

        return context

    def _should_continue(
        self,
        context: "PipelineContext",
    ) -> tuple[bool, str]:
        """
        Determine if interview should continue.

        Domain Encapsulation: Reads saturation metrics from StateComputationOutput
        (computed by Stage 5) instead of maintaining local tracking state.

        Returns:
            Tuple of (should_continue, reason). Reason is empty string if continuing.
        """
        turn_number = context.turn_number
        max_turns = context.max_turns
        strategy = context.strategy

        # Get phase from signal (unified source of truth)
        current_phase = None
        is_late_stage = False
        if context.signals:
            current_phase = context.signals.get("meta.interview.phase")
            is_late_stage = context.signals.get("meta.interview.is_late_stage", False)

        # --- Hard stops (always checked) ---

        if turn_number >= max_turns:
            log.info(
                "session_ending",
                reason="max_turns",
                turn_number=turn_number,
                max_turns=max_turns,
                phase=current_phase,
            )
            return False, "Maximum turns reached"

        if strategy == "close":
            log.info(
                "session_ending",
                reason="close_strategy",
                phase=current_phase,
            )
            return False, "Closing strategy selected"

        # --- Saturation checks (only after minimum turns OR late stage) ---
        # Use phase-based OR turn-based detection for saturation checks
        if turn_number < MIN_TURN_FOR_SATURATION and not is_late_stage:
            return True, ""

        # Read saturation metrics from StateComputationOutput (computed by Stage 5)
        saturation = None
        if context.state_computation_output:
            saturation = context.state_computation_output.saturation_metrics

        # If no saturation metrics available, continue (can't assess saturation)
        if not saturation:
            return True, ""

        # Check is_saturated flag (computed by StateComputationStage)
        if saturation.is_saturated:
            # Determine the specific reason from the metrics
            reason = self._get_saturation_reason(saturation, current_phase)
            return False, reason

        # Node exhaustion: all explored nodes are exhausted
        if self._all_nodes_exhausted(context):
            log.info(
                "session_ending",
                reason="all_nodes_exhausted",
                phase=current_phase,
            )
            return False, "all_nodes_exhausted"

        return True, ""

    def _get_saturation_reason(
        self,
        saturation: SaturationMetrics,
        current_phase: str | None,
    ) -> str:
        """
        Determine the specific saturation reason from metrics.

        Args:
            saturation: SaturationMetrics from StateComputationOutput
            current_phase: Current interview phase for logging

        Returns:
            Reason string for the saturation condition
        """
        # Import thresholds from StateComputationStage (single source of truth)
        from .state_computation_stage import (
            CONSECUTIVE_ZERO_YIELD_THRESHOLD,
            CONSECUTIVE_SHALLOW_THRESHOLD,
            DEPTH_PLATEAU_THRESHOLD,
        )

        # Check each saturation condition and log appropriately
        if saturation.consecutive_low_info >= CONSECUTIVE_ZERO_YIELD_THRESHOLD:
            log.info(
                "session_ending",
                reason="graph_saturated",
                consecutive_zero_yield=saturation.consecutive_low_info,
                phase=current_phase,
            )
            return "graph_saturated"

        if saturation.consecutive_shallow >= CONSECUTIVE_SHALLOW_THRESHOLD:
            log.info(
                "session_ending",
                reason="quality_degraded",
                consecutive_shallow=saturation.consecutive_shallow,
                phase=current_phase,
            )
            return "quality_degraded"

        if saturation.consecutive_depth_plateau >= DEPTH_PLATEAU_THRESHOLD:
            log.info(
                "session_ending",
                reason="depth_plateau",
                consecutive_depth_plateau=saturation.consecutive_depth_plateau,
                phase=current_phase,
            )
            return "depth_plateau"

        # Generic saturation (shouldn't happen if is_saturated is True)
        log.info(
            "session_ending",
            reason="saturated",
            phase=current_phase,
        )
        return "saturated"

    @staticmethod
    def _all_nodes_exhausted(context: "PipelineContext") -> bool:
        """Check if all explored nodes are exhausted (nothing left to explore)."""
        tracker = context.node_tracker
        if not tracker or not tracker.states:
            return False

        explored = [ns for ns in tracker.states.values() if ns.focus_count > 0]
        if not explored:
            return False

        return all(
            ns.turns_since_last_yield >= NODE_EXHAUSTION_YIELD_GAP for ns in explored
        )
