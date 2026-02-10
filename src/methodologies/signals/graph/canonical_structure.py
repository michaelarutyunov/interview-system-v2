"""
Canonical graph structure signals - concept count, edge density, exhaustion.

These signals operate on the canonical (deduplicated) graph rather than
the surface graph, providing more stable metrics for strategy selection.
"""

from typing import TYPE_CHECKING

import structlog

from src.methodologies.signals.common import (
    SignalDetector,
    SignalCostTier,
    RefreshTrigger,
)

if TYPE_CHECKING:
    from src.services.turn_pipeline.context import PipelineContext

log = structlog.get_logger(__name__)


class CanonicalConceptCountSignal(SignalDetector):
    """Number of deduplicated canonical concepts (active slots).

    Namespaced signal: graph.canonical_concept_count
    Cost: free (O(1) lookup from pre-computed state)
    Refresh: per_turn (computed by StateComputationStage)

    Lower than surface node_count because paraphrases are merged into
    canonical slots. Reduces noise from respondent language variation.
    """

    signal_name = "graph.canonical_concept_count"
    description = (
        "Number of deduplicated canonical concepts (active slots). "
        "Lower than surface node_count because paraphrases are merged. "
        "Counts stable latent concepts rather than surface language variations."
    )
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(
        self, context: "PipelineContext", graph_state, response_text
    ) -> dict:
        """
        Return canonical concept count from canonical graph state.

        Args:
            context: Pipeline context with canonical_graph_state property
            graph_state: Surface graph state (unused)
            response_text: LLM response text (unused)

        Returns:
            {signal_name: concept_count} if canonical_graph_state exists, else {}

        Note:
            Reads from context.canonical_graph_state (convenience property).
            Returns {} if canonical_graph_state is None (canonical slots disabled).
            - Logs at DEBUG level (expected when canonical disabled, not a warning)
        """
        cg_state = context.canonical_graph_state

        if cg_state is None:
            log.debug(
                "canonical_graph_state_not_available",
                signal=self.signal_name,
            )
            return {}

        return {self.signal_name: cg_state.concept_count}


class CanonicalEdgeDensitySignal(SignalDetector):
    """Edge-to-concept ratio in canonical graph.

    Namespaced signal: graph.canonical_edge_density
    Cost: free (O(1) lookup from pre-computed state)
    Refresh: per_turn (computed by StateComputationStage)

    Higher values indicate more connected structure among deduplicated
    concepts. Replaces coverage breadth signal (not relevant for exploration).

    Note:
        Computes edge_count / concept_count, capped at 0.0 for empty graphs.
    """

    signal_name = "graph.canonical_edge_density"
    description = (
        "Edge-to-concept ratio in canonical graph. Higher = more connected structure. "
        "Uses deduplicated concepts, so reflects relationship density among stable concepts "
        "rather than surface paraphrases."
    )
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(
        self, context: "PipelineContext", graph_state, response_text
    ) -> dict:
        """
        Return canonical edge density from canonical graph state.

        Args:
            context: Pipeline context with canonical_graph_state property
            graph_state: Surface graph state (unused)
            response_text: LLM response text (unused)

        Returns:
            {signal_name: edge_density} if canonical_graph_state exists, else {}

        Note:
            edge_density = edge_count / concept_count if concept_count > 0, else 0.0.
            Reads from context.canonical_graph_state (convenience property).
            - Returns {} if canonical_graph_state is None (canonical slots disabled)
        """
        cg_state = context.canonical_graph_state

        if cg_state is None:
            log.debug(
                "canonical_graph_state_not_available",
                signal=self.signal_name,
            )
            return {}

        concept_count = cg_state.concept_count
        edge_count = cg_state.edge_count

        density = edge_count / concept_count if concept_count > 0 else 0.0

        return {self.signal_name: density}


class CanonicalExhaustionScoreSignal(SignalDetector):
    """Average exhaustion score across canonical slots.

    Namespaced signal: graph.canonical_exhaustion_score
    Cost: low (O(n) over tracked slots, n < 50 typically)
    Refresh: per_turn

    Aggregates exhaustion scores from all tracked canonical slots using
    the NodeStateTracker. Tracks by canonical_slot_id, so this reflects
    exhaustion of deduplicated concepts rather than surface paraphrases.

    Values range 0.0 (fresh) to 1.0 (fully exhausted).

    Note:
        NodeStateTracker keys by canonical_slot_id.
        Reads average exhaustion from context.node_tracker.states.
        Returns {} if node_tracker is None or has no states.
        - Exhaustion score computed from NodeState attributes (not a pre-computed field):
          * focus_count: must be > 0 for node to have exhaustion
          * turns_since_last_yield: contributes up to 0.4 to score (capped at 10)
          * current_focus_streak: contributes up to 0.3 to score (capped at 5)
          * shallow_ratio: contributes up to 0.3 to score
    """

    signal_name = "graph.canonical_exhaustion_score"
    description = (
        "Average exhaustion score across canonical slots. "
        "Aggregates exhaustion from deduplicated concepts (canonical slots). "
        "Higher values indicate concepts have been thoroughly explored. "
        "Tracks exhaustion of stable concepts rather than surface paraphrases."
    )
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(
        self, context: "PipelineContext", graph_state, response_text
    ) -> dict:
        """
        Return average canonical slot exhaustion score.

        Args:
            context: Pipeline context with node_tracker
            graph_state: Surface graph state (unused)
            response_text: LLM response text (unused)

        Returns:
            {signal_name: avg_exhaustion} if node_tracker exists, else {}

        Note:
            NodeStateTracker keys by canonical_slot_id.
            Computes average exhaustion from context.node_tracker.states.
            Returns {} if node_tracker is None or has no states.
        """
        node_tracker = context.node_tracker

        if node_tracker is None or not node_tracker.states:
            log.debug(
                "node_tracker_not_available",
                signal=self.signal_name,
            )
            return {}

        # Compute average exhaustion across all tracked slots
        exhaustion_scores = [
            self._calculate_exhaustion_score(state)
            for state in node_tracker.states.values()
        ]

        if not exhaustion_scores:
            return {}

        avg_exhaustion = sum(exhaustion_scores) / len(exhaustion_scores)

        return {self.signal_name: avg_exhaustion}

    def _calculate_exhaustion_score(self, state) -> float:
        """Calculate exhaustion score for a node state.

        Args:
            state: NodeState to score

        Returns:
            Exhaustion score from 0.0 (fresh) to 1.0 (exhausted)

        Note:
            Follows NodeExhaustionScoreSignal._calculate_exhaustion_score pattern.
            If never focused, score is 0.0.
            - Factor 1: Turns since last yield (0.0 - 0.4, max at 10 turns)
            - Factor 2: Focus streak (0.0 - 0.3, max at 5 consecutive)
            - Factor 3: Shallow ratio (0.0 - 0.3)
        """
        # If never focused, score is 0.0
        if state.focus_count == 0:
            return 0.0

        # Factor 1: Turns since last yield (0.0 - 0.4, max at 10 turns)
        turns_score = min(state.turns_since_last_yield, 10) / 10.0 * 0.4

        # Factor 2: Focus streak (0.0 - 0.3, max at 5 consecutive)
        streak_score = min(state.current_focus_streak, 5) / 5.0 * 0.3

        # Factor 3: Shallow ratio (0.0 - 0.3)
        shallow_ratio = self._calculate_shallow_ratio(state, recent_count=3)
        shallow_score = shallow_ratio * 0.3

        # Total score
        return turns_score + streak_score + shallow_score

    def _calculate_shallow_ratio(self, state, recent_count: int = 3) -> float:
        """Calculate ratio of shallow responses in recent N responses.

        Args:
            state: NodeState to analyze
            recent_count: Number of recent responses to consider

        Returns:
            Ratio of shallow responses (0.0 - 1.0)

        Note:
            Follows NodeSignalDetector._calculate_shallow_ratio pattern.
            Counts "surface" and "shallow" responses.
            Returns 0.0 if no responses recorded.
        """
        if not state.all_response_depths:
            return 0.0

        # Get last N responses
        recent_responses = state.all_response_depths[-recent_count:]

        # Count shallow responses (surface or shallow)
        shallow_count = sum(
            1 for depth in recent_responses if depth in ("surface", "shallow")
        )

        return shallow_count / len(recent_responses)


# Export all canonical graph signals
__all__ = [
    "CanonicalConceptCountSignal",
    "CanonicalEdgeDensitySignal",
    "CanonicalExhaustionScoreSignal",
]
