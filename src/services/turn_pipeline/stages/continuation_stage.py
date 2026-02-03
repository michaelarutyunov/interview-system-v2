"""
Stage 7: Determine continuation.

ADR-008 Phase 3: Decide if interview should continue or end.
Phase 6: Output ContinuationOutput contract.
Domain Encapsulation: Focus selection delegated to FocusSelectionService.
"""

from dataclasses import dataclass
from typing import Dict, TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import ContinuationOutput
from src.services.focus_selection_service import FocusSelectionService


if TYPE_CHECKING:
    from ..context import PipelineContext
    from src.services.question_service import QuestionService
log = structlog.get_logger(__name__)

# =============================================================================
# Saturation thresholds (tune these as needed)
# =============================================================================
MIN_TURN_FOR_SATURATION = 5  # Don't check saturation before this turn
CONSECUTIVE_ZERO_YIELD_THRESHOLD = 5  # Turns with 0 new nodes+edges
CONSECUTIVE_SHALLOW_THRESHOLD = 4  # Turns with only shallow responses
DEPTH_PLATEAU_THRESHOLD = 6  # Turns at same max_depth
NODE_EXHAUSTION_YIELD_GAP = 3  # turns_since_last_yield to consider exhausted


@dataclass
class _SessionSaturationState:
    """Per-session rolling state for saturation detection."""

    consecutive_zero_yield: int = 0
    consecutive_shallow: int = 0
    prev_max_depth: int = -1
    consecutive_depth_plateau: int = 0


class ContinuationStage(TurnStage):
    """
    Determine if interview should continue.

    Populates PipelineContext.should_continue and PipelineContext.focus_concept.

    Saturation detection (Approach A): tracking is self-contained in this stage
    using per-session rolling state derived from PipelineContext data available
    at Stage 7 (graph_update_output, graph_state, node_tracker).

    Future improvement (Approach B): move saturation computation into
    StateComputationStage (Stage 5) by populating the existing
    SaturationMetrics model (chao1_ratio, new_info_rate, etc.) on GraphState.
    This would let other stages and signals also consume saturation data, and
    would enable richer species-richness estimators (Chao1). See
    src/domain/models/knowledge_graph.py:SaturationMetrics for the model.
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
        self._tracking: Dict[str, _SessionSaturationState] = {}

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Determine if we should continue and select focus concept.

        Args:
            context: Turn context with turn_number, max_turns, graph_state, strategy

        Returns:
            Modified context with should_continue and focus_concept
        """
        # Update saturation tracking before deciding
        self._update_tracking(context)

        # Determine if we should continue
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

    def _get_tracking(self, session_id: str) -> _SessionSaturationState:
        """Get or create per-session saturation tracking state."""
        if session_id not in self._tracking:
            self._tracking[session_id] = _SessionSaturationState()
        return self._tracking[session_id]

    def _update_tracking(self, context: "PipelineContext") -> None:
        """Update rolling saturation counters from this turn's data."""
        state = self._get_tracking(context.session_id)

        # --- Graph yield tracking ---
        nodes_added = 0
        edges_added = 0
        if context.graph_update_output:
            nodes_added = context.graph_update_output.node_count
            edges_added = context.graph_update_output.edge_count

        if nodes_added + edges_added == 0:
            state.consecutive_zero_yield += 1
        else:
            state.consecutive_zero_yield = 0

        # --- Depth plateau tracking ---
        current_max_depth = 0
        if context.graph_state and context.graph_state.depth_metrics:
            current_max_depth = context.graph_state.depth_metrics.max_depth

        if state.prev_max_depth >= 0 and current_max_depth == state.prev_max_depth:
            state.consecutive_depth_plateau += 1
        else:
            state.consecutive_depth_plateau = 0
        state.prev_max_depth = current_max_depth

        # --- Quality degradation tracking ---
        if context.node_tracker and context.node_tracker.states:
            # Check if the most recent response depths are all shallow/surface
            has_any_deep = False
            for ns in context.node_tracker.states.values():
                if ns.all_response_depths and ns.all_response_depths[-1] == "deep":
                    has_any_deep = True
                    break
            if not has_any_deep:
                state.consecutive_shallow += 1
            else:
                state.consecutive_shallow = 0
        # If no node_tracker, don't increment — we can't assess quality

    def _should_continue(
        self,
        context: "PipelineContext",
    ) -> tuple[bool, str]:
        """
        Determine if interview should continue.

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

        state = self._get_tracking(context.session_id)

        # Graph saturation: no new nodes/edges for N consecutive turns
        if state.consecutive_zero_yield >= CONSECUTIVE_ZERO_YIELD_THRESHOLD:
            log.info(
                "session_ending",
                reason="graph_saturated",
                consecutive_zero_yield=state.consecutive_zero_yield,
                phase=current_phase,
            )
            return False, "graph_saturated"

        # Node exhaustion: all explored nodes are exhausted
        if self._all_nodes_exhausted(context):
            log.info(
                "session_ending",
                reason="all_nodes_exhausted",
                phase=current_phase,
            )
            return False, "all_nodes_exhausted"

        # Quality degradation: consecutive shallow responses
        if state.consecutive_shallow >= CONSECUTIVE_SHALLOW_THRESHOLD:
            log.info(
                "session_ending",
                reason="quality_degraded",
                consecutive_shallow=state.consecutive_shallow,
                phase=current_phase,
            )
            return False, "quality_degraded"

        # Depth plateau: max_depth unchanged for N turns
        if state.consecutive_depth_plateau >= DEPTH_PLATEAU_THRESHOLD:
            log.info(
                "session_ending",
                reason="depth_plateau",
                consecutive_depth_plateau=state.consecutive_depth_plateau,
                phase=current_phase,
            )
            return False, "depth_plateau"

        return True, ""

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
