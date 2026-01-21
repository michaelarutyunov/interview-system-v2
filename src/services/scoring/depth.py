"""Depth scorer - balances depth vs breadth based on interview phase.

Boosts depth in late phase, breadth in early phase.
"""

from typing import Any, Dict

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.base import ScorerBase, ScorerOutput


# Default configuration values
DEFAULT_EARLY_BREADTH_BOOST = 1.5
DEFAULT_LATE_DEPTH_BOOST = 1.4
DEFAULT_PHASE_THRESHOLDS = [0.3, 0.7]
DEFAULT_ESTIMATED_TOTAL_TURNS = 20


logger = structlog.get_logger(__name__)


class DepthScorer(ScorerBase):
    """
    Balance depth vs breadth based on interview phase.

    Algorithm:
    1. Calculate phase: turn_count / estimated_total_turns
    2. Early phase (< 0.3): boost breadth
    3. Middle phase (0.3-0.7): neutral
    4. Late phase (> 0.7): boost depth for chain completion

    Scoring:
    - 1.0 = neutral (middle phase)
    - early_breadth_boost (e.g., 1.5) = early phase, boost breadth
    - late_depth_boost (e.g., 1.4) = late phase, boost depth

    Configuration parameters:
    - early_breadth_boost: Boost for breadth in early phase (default: 1.5)
    - late_depth_boost: Boost for depth in late phase (default: 1.4)
    - phase_thresholds: [early_end, late_start] (default: [0.3, 0.7])
    - estimated_total_turns: Expected interview length (default: 20)
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.early_breadth_boost = self.params.get("early_breadth_boost", DEFAULT_EARLY_BREADTH_BOOST)
        self.late_depth_boost = self.params.get("late_depth_boost", DEFAULT_LATE_DEPTH_BOOST)
        self.phase_thresholds = self.params.get("phase_thresholds", DEFAULT_PHASE_THRESHOLDS)
        self.estimated_total = self.params.get("estimated_total_turns", DEFAULT_ESTIMATED_TOTAL_TURNS)

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list[Dict[str, Any]],
    ) -> ScorerOutput:
        """
        Score based on interview phase.

        Args:
            strategy: Strategy dict with 'type_category'
            focus: Focus dict (unused for depth scorer)
            graph_state: Graph state with turn_count and max_depth
            recent_nodes: Recent nodes (unused for depth scorer)

        Returns:
            ScorerOutput with phase-based score
        """
        score = 1.0
        signals = {}
        reasons = []

        # Calculate phase
        turn_count = graph_state.properties.get("turn_count", 1)
        phase = turn_count / self.estimated_total

        signals["turn_count"] = turn_count
        signals["phase"] = phase
        signals["max_depth"] = graph_state.max_depth

        # Determine phase category
        early_threshold, late_threshold = self.phase_thresholds
        is_early = phase < early_threshold
        is_middle = early_threshold <= phase <= late_threshold
        is_late = phase > late_threshold

        signals["is_early"] = is_early
        signals["is_middle"] = is_middle
        signals["is_late"] = is_late

        # Apply phase-based adjustments
        if is_early:
            # Early phase: boost breadth/coverage
            if strategy.get("type_category") in ["breadth", "coverage"]:
                score *= self.early_breadth_boost
                reasons.append(
                    f"Early phase (turn {turn_count}/{self.estimated_total}) - breadth encouraged"
                )

        elif is_late:
            # Late phase: boost depth for chain completion
            if strategy.get("type_category") == "depth":
                score *= self.late_depth_boost
                reasons.append(
                    f"Late phase (turn {turn_count}/{self.estimated_total}) - depth encouraged"
                )

        if not reasons:
            reasoning = f"Middle phase (turn {turn_count}/{self.estimated_total})"
        else:
            reasoning = "; ".join(reasons)

        logger.debug(
            "DepthScorer output",
            strategy_id=strategy.get("id"),
            phase=phase,
            score=score,
        )

        return self.make_output(score, signals, reasoning)
