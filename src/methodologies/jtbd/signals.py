from typing import TYPE_CHECKING
from src.methodologies.base import BaseSignalDetector, SignalState

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext


class JTBDSignalState(SignalState):
    """JTBD-specific signals."""

    # Dimension coverage signals
    job_identified: bool = False
    situation_depth: float = 0.0
    motivation_depth: float = 0.0
    alternatives_explored: float = 0.0
    obstacles_explored: float = 0.0
    outcome_clarity: float = 0.0
    timeline_mapped: bool = False

    # Coverage balance
    coverage_imbalance: float = 0.0  # High = uneven coverage across dimensions
    least_covered_dimension: str = "situation"

    # Response signals
    mentioned_competitor: bool = False
    mentioned_struggle: bool = False
    mentioned_trigger: bool = False


class JTBDSignalDetector(BaseSignalDetector):
    """Signal detection for Jobs-to-be-Done methodology."""

    DIMENSIONS = [
        "situation",
        "motivation",
        "alternatives",
        "obstacles",
        "outcome",
        "timeline",
    ]

    async def detect(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> JTBDSignalState:
        signals = JTBDSignalState()

        # Check for job identification
        signals.job_identified = self._has_job_node(graph_state)

        # Calculate dimension coverage
        dimension_coverage = self._calculate_dimension_coverage(graph_state)
        signals.situation_depth = dimension_coverage.get("situation", 0.0)
        signals.motivation_depth = dimension_coverage.get("motivation", 0.0)
        signals.alternatives_explored = dimension_coverage.get("alternatives", 0.0)
        signals.obstacles_explored = dimension_coverage.get("obstacles", 0.0)
        signals.outcome_clarity = dimension_coverage.get("outcome", 0.0)
        signals.timeline_mapped = dimension_coverage.get("timeline", 0.0) > 0.5

        # Coverage balance
        coverages = list(dimension_coverage.values())
        if coverages:
            mean_coverage = sum(coverages) / len(coverages)
            variance = sum((c - mean_coverage) ** 2 for c in coverages) / len(coverages)
            signals.coverage_imbalance = variance**0.5  # std dev

            # Find least covered
            min_dim = min(dimension_coverage, key=dimension_coverage.get)
            signals.least_covered_dimension = min_dim

        # Response analysis (simplified)
        response_lower = response_text.lower()
        signals.mentioned_competitor = any(
            w in response_lower for w in ["tried", "used to", "before", "instead"]
        )
        signals.mentioned_struggle = any(
            w in response_lower
            for w in ["hard", "difficult", "frustrating", "couldn't"]
        )
        signals.mentioned_trigger = any(
            w in response_lower for w in ["when", "moment", "realized", "decided"]
        )

        # Strategy history
        signals.strategy_repetition_count = self._count_strategy_repetitions(context)
        signals.turns_since_strategy_change = self._turns_since_change(context)

        return signals

    def _has_job_node(self, graph_state: "GraphState") -> bool:
        """Check if core job has been identified."""
        # Check nodes_by_type for job-related node types
        job_types = ("job_statement", "core_job")
        for node_type in job_types:
            if graph_state.nodes_by_type.get(node_type):
                return True
        return False

    def _calculate_dimension_coverage(self, graph_state: "GraphState") -> dict:
        """Calculate coverage for each JTBD dimension."""
        # Map node types to dimensions
        dimension_types = {
            "situation": ["context", "trigger", "circumstance"],
            "motivation": [
                "motivation",
                "desired_outcome",
                "push_factor",
                "pull_factor",
            ],
            "alternatives": ["alternative", "competing_solution", "workaround"],
            "obstacles": ["obstacle", "barrier", "pain_point", "anxiety"],
            "outcome": ["outcome", "success_criteria", "benefit"],
            "timeline": ["timeline", "event", "milestone"],
        }

        coverage = {dim: 0.0 for dim in self.DIMENSIONS}

        # Use nodes_by_type to count nodes per dimension
        for dim, types in dimension_types.items():
            for node_type in types:
                count = len(graph_state.nodes_by_type.get(node_type, []))
                coverage[dim] = min(coverage[dim] + count * 0.25, 1.0)  # Cap at 1.0

        return coverage

    def _count_strategy_repetitions(self, context: "PipelineContext") -> int:
        if not context.strategy_history:
            return 0
        current = context.strategy_history[-1] if context.strategy_history else None
        if not current:
            return 0
        return sum(1 for t in context.strategy_history[-5:] if t == current)

    def _turns_since_change(self, context: "PipelineContext") -> int:
        if not context.strategy_history or len(context.strategy_history) < 2:
            return 0
        current = context.strategy_history[-1]
        count = 0
        for turn in reversed(context.strategy_history):
            if turn == current:
                count += 1
            else:
                break
        return count
