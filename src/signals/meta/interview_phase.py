"""Interview phase detection signal for adaptive strategy selection.

Detects the current interview phase based on turn number progression.
Phase detection enables methodology-specific signal weights and bonuses
to adjust questioning strategy as the interview progresses.

Phases:
- early: Initial exploration (turn_number < early_max_turns)
- mid: Building depth and connections (early_max_turns <= turn_number < mid_max_turns)
- late: Validation and verification (turn_number >= mid_max_turns)
"""

from src.core.exceptions import ConfigurationError
from src.signals.signal_base import SignalDetector


class InterviewPhaseSignal(SignalDetector):
    """Detect interview phase from turn number for adaptive strategy weights.

    Uses turn number to determine interview phase, enabling
    methodology-specific signal weights and bonuses to adjust questioning
    strategy as the interview progresses.

    Phase detection uses methodology-configurable boundaries:
    - early_max_turns: Threshold for early phase (default: 4)
    - mid_max_turns: Threshold for mid phase (default: 12)

    Phase outputs drive multiplicative weight adjustments in strategy selection,
    allowing the system to prioritize different strategies based on interview
    maturity (e.g., exploration early, deepening mid, validation late).

    Namespaced signal: meta.interview.phase
    Cost: low (reads context.turn_number)
    Refresh: per_turn (recomputed each turn)
    """

    signal_name = "meta.interview.phase"
    description = "Current interview phase: 'early', 'mid', or 'late'. Phase boundaries are configurable per methodology. Used to adjust strategy weights."

    # Default phase boundaries (fallback if not specified in YAML)
    DEFAULT_BOUNDARIES = {
        "early_max_turns": 4,
        "mid_max_turns": 12,
    }

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect interview phase from turn number.

        Args:
            context: Pipeline context (provides turn_number)
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
        # Get phase boundaries from methodology config
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
        """Get phase boundaries from methodology config.

        Supports both new turn-based keys (early_max_turns/mid_max_turns) and
        legacy node-based keys (early_max_nodes/mid_max_nodes) for backwards
        compatibility during the transition. Turn-based keys take precedence.

        Args:
            context: Pipeline context with methodology property

        Returns:
            Dict with 'early_max_turns' and 'mid_max_turns' keys

        Raises:
            ConfigurationError: If methodology config fails to load due to
                malformed YAML, missing methodology, or registry errors.
                Does NOT raise for valid configs with missing phase_boundaries.
        """
        from src.methodologies.registry import MethodologyRegistry

        methodology = getattr(context, "methodology", None)
        if not methodology:
            # No methodology specified - use defaults (valid case)
            return self.DEFAULT_BOUNDARIES

        try:
            registry = MethodologyRegistry()
            config = registry.get_methodology(methodology)

            if config.phases:
                for phase_config in config.phases.values():
                    if phase_config.phase_boundaries:
                        return self._normalize_boundaries(phase_config.phase_boundaries)

            # Config loaded successfully, but no phase boundaries defined
            # This is valid - use defaults
            return self.DEFAULT_BOUNDARIES
        except Exception as e:
            # Actual config loading error (malformed YAML, missing file, etc.)
            # This is a fail-fast violation - raise ConfigurationError
            raise ConfigurationError(
                f"InterviewPhaseSignal failed to load phase config for "
                f"methodology '{methodology}': {e}"
            ) from e

    def _normalize_boundaries(self, boundaries: dict) -> dict:
        """Normalize phase boundaries to turn-based keys.

        Supports both new turn-based keys and legacy node-based keys.
        Turn-based keys take precedence over node-based keys.

        Args:
            boundaries: Raw phase boundaries from YAML config

        Returns:
            Dict with 'early_max_turns' and 'mid_max_turns' keys
        """
        early = boundaries.get(
            "early_max_turns",
            boundaries.get("early_max_nodes", self.DEFAULT_BOUNDARIES["early_max_turns"]),
        )
        mid = boundaries.get(
            "mid_max_turns",
            boundaries.get("mid_max_nodes", self.DEFAULT_BOUNDARIES["mid_max_turns"]),
        )
        return {"early_max_turns": early, "mid_max_turns": mid}

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
