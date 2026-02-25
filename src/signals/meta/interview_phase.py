"""Interview phase detection signal for adaptive strategy selection.

Detects the current interview phase based on turn number progression.
Phase detection enables methodology-specific signal weights and bonuses
to adjust questioning strategy as the interview progresses.

Phases (automatically calculated from max_turns):
- early: Initial exploration (~10% of max_turns, minimum 1 turn)
- mid: Building depth and connections (early <= turn < max_turns-2)
- late: Validation and verification (last 2 turns reserved)
"""

from src.signals.signal_base import SignalDetector


class InterviewPhaseSignal(SignalDetector):
    """Detect interview phase from turn number for adaptive strategy weights.

    Uses turn number to determine interview phase, enabling
    methodology-specific signal weights and bonuses to adjust questioning
    strategy as the interview progresses.

    Phase boundaries are automatically calculated from max_turns:
    - early: ~10% of max_turns (minimum 1 turn)
    - mid: max_turns - 2 (reserving last 2 turns for late)
    - late: final 2 turns for validation

    Phase outputs drive multiplicative weight adjustments in strategy selection,
    allowing the system to prioritize different strategies based on interview
    maturity (e.g., exploration early, deepening mid, validation late).

    Namespaced signal: meta.interview.phase
    Cost: low (reads context.turn_number and context.max_turns)
    Refresh: per_turn (recomputed each turn)
    """

    signal_name = "meta.interview.phase"
    description = "Current interview phase: 'early', 'mid', or 'late'. Phase boundaries are automatically calculated from max_turns: early=~10%, mid=max_turns-2, late=last 2 turns."

    # Proportional phase allocation constants
    EARLY_PHASE_RATIO = 0.10  # 10% of max_turns for early phase
    LATE_PHASE_TURNS = 2  # Reserve last 2 turns for late phase
    DEFAULT_MAX_TURNS = 20  # Fallback if max_turns not accessible

    @staticmethod
    def calculate_phase_boundaries(max_turns: int) -> dict:
        """Calculate phase boundaries proportionally from max_turns.

        Phase allocation:
        - early: ~10% of max_turns (minimum 1 turn)
        - late: last 2 turns reserved for validation
        - mid: everything in between

        Args:
            max_turns: Total maximum turns for the interview

        Returns:
            Dict with 'early_max_turns' and 'mid_max_turns' keys
        """
        early_max_turns = max(
            1, round(max_turns * InterviewPhaseSignal.EARLY_PHASE_RATIO)
        )
        mid_max_turns = max_turns - InterviewPhaseSignal.LATE_PHASE_TURNS
        return {"early_max_turns": early_max_turns, "mid_max_turns": mid_max_turns}

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect interview phase from turn number.

        Args:
            context: Pipeline context (provides turn_number and max_turns)
            graph_state: Current knowledge graph state (not used)
            response_text: User's response text (not used)

        Returns:
            Dict with phase, phase_reason, and is_late_stage signals:
            {
                "meta.interview.phase": "early" | "mid" | "late",
                "meta.interview.phase_reason": str,
                "meta.interview.is_late_stage": bool,
            }
        """
        # Calculate phase boundaries proportionally from max_turns
        boundaries = self._get_phase_boundaries(context)

        # Extract turn number from pipeline context
        turn_number = getattr(context, "turn_number", 0)

        # Determine phase using methodology-specific boundaries
        phase = self._determine_phase(
            turn_number,
            boundaries["early_max_turns"],
            boundaries["mid_max_turns"],
        )

        # Build phase reason for logging/debugging
        phase_reason = (
            f"turn_number={turn_number}, "
            f"phase={phase}, boundaries=early<{boundaries['early_max_turns']}, "
            f"mid<{boundaries['mid_max_turns']}"
        )

        return {
            self.signal_name: phase,
            "meta.interview.phase_reason": phase_reason,
            "meta.interview.is_late_stage": phase == "late",
        }

    def _get_phase_boundaries(self, context) -> dict:
        """Calculate phase boundaries proportionally from max_turns.

        Phase boundaries are automatically calculated:
        - early: ~10% of max_turns (minimum 1 turn)
        - late: last 2 turns reserved for validation
        - mid: everything in between

        This replaces the old approach of hardcoding boundaries in YAML configs.
        Phases now scale proportionally with interview length.

        Args:
            context: Pipeline context with max_turns property

        Returns:
            Dict with 'early_max_turns' and 'mid_max_turns' keys
        """
        # Get max_turns from context (set by ContextLoadingStage)
        try:
            max_turns = context.max_turns
        except (AttributeError, RuntimeError):
            # Fallback if max_turns not accessible (shouldn't happen in normal flow)
            max_turns = self.DEFAULT_MAX_TURNS

        return self.calculate_phase_boundaries(max_turns)

    def _determine_phase(
        self,
        turn_number: int,
        early_max_turns: int,
        mid_max_turns: int,
    ) -> str:
        """Determine interview phase from turn number.

        Args:
            turn_number: Current turn number in the interview
            early_max_turns: Turn threshold for early phase
            mid_max_turns: Turn threshold for mid phase

        Returns:
            Phase: "early" | "mid" | "late"
        """
        if turn_number < early_max_turns:
            return "early"
        elif turn_number < mid_max_turns:
            return "mid"
        else:
            return "late"
