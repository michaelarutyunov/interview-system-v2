from typing import TYPE_CHECKING
from src.methodologies.base import BaseSignalDetector, SignalState

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext


class MECSignalState(SignalState):
    """MEC-specific signals."""

    # Graph-based signals
    missing_terminal_value: bool = True
    ladder_depth: int = 0
    disconnected_nodes: int = 0
    edge_density: float = 0.0  # edges / nodes ratio

    # Coverage signals
    attributes_explored: int = 0
    consequences_explored: int = 0
    values_explored: int = 0
    coverage_breadth: float = 0.0  # % of concept elements covered

    # Response signals (from LLM analysis)
    new_concepts_mentioned: bool = False
    response_depth: str = "surface"  # surface | moderate | deep


class MECSignalDetector(BaseSignalDetector):
    """Signal detection for Means-End Chain methodology."""

    async def detect(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> MECSignalState:
        signals = MECSignalState()

        # Graph-based signals
        signals.missing_terminal_value = self._check_missing_terminal(graph_state)
        signals.ladder_depth = self._calculate_ladder_depth(graph_state)
        signals.disconnected_nodes = self._count_disconnected(graph_state)
        signals.edge_density = self._calculate_edge_density(graph_state)

        # Coverage signals
        node_counts = self._count_node_types(graph_state)
        signals.attributes_explored = node_counts.get("attribute", 0)
        signals.consequences_explored = node_counts.get(
            "functional_consequence", 0
        ) + node_counts.get("psychosocial_consequence", 0)
        signals.values_explored = node_counts.get(
            "instrumental_value", 0
        ) + node_counts.get("terminal_value", 0)
        signals.coverage_breadth = self._calculate_coverage(context)

        # Response signals (could use LLM for deeper analysis)
        signals.new_concepts_mentioned = (
            len(context.extraction.concepts) > 0 if context.extraction else False
        )
        signals.response_depth = await self._analyze_response_depth(response_text)

        # Strategy history signals (common)
        signals.strategy_repetition_count = self._count_strategy_repetitions(context)
        signals.turns_since_strategy_change = self._turns_since_change(context)

        return signals

    def _check_missing_terminal(self, graph_state: "GraphState") -> bool:
        """Check if graph has no terminal values yet."""
        # Use nodes_by_type from GraphState
        terminal_count = graph_state.nodes_by_type.get("terminal_value", 0)
        instrumental_count = graph_state.nodes_by_type.get("instrumental_value", 0)
        return (terminal_count + instrumental_count) == 0

    def _calculate_ladder_depth(self, graph_state: "GraphState") -> int:
        """Calculate maximum depth of any ladder chain."""
        # Use depth_metrics from GraphState (max_depth field)
        return graph_state.depth_metrics.max_depth

    def _count_disconnected(self, graph_state: "GraphState") -> int:
        """Count nodes with no edges."""
        # Use orphan_count from GraphState
        return graph_state.orphan_count

    def _calculate_edge_density(self, graph_state: "GraphState") -> float:
        """Calculate edge/node ratio."""
        if graph_state.node_count == 0:
            return 0.0
        return graph_state.edge_count / graph_state.node_count

    def _count_node_types(self, graph_state: "GraphState") -> dict:
        """Count nodes by type."""
        # Use nodes_by_type from GraphState
        return dict(graph_state.nodes_by_type)

    def _calculate_coverage(self, context: "PipelineContext") -> float:
        """Calculate concept element coverage breadth."""
        # Use coverage_state from graph_state
        if context.graph_state and context.graph_state.coverage_state:
            coverage_state = context.graph_state.coverage_state
            if coverage_state.elements_total > 0:
                return coverage_state.elements_covered / coverage_state.elements_total
        return 0.0

    def _count_strategy_repetitions(self, context: "PipelineContext") -> int:
        """Count recent uses of current strategy."""
        if not context.strategy_history:
            return 0
        current = context.strategy_history[-1] if context.strategy_history else None
        if not current:
            return 0
        # Count occurrences in last 5 entries
        recent_history = context.strategy_history[-5:]
        return sum(1 for s in recent_history if s == current)

    def _turns_since_change(self, context: "PipelineContext") -> int:
        """Count turns since strategy changed."""
        if not context.strategy_history or len(context.strategy_history) < 2:
            return 0
        current = context.strategy_history[-1]
        count = 0
        for strategy in reversed(context.strategy_history):
            if strategy == current:
                count += 1
            else:
                break
        return count

    async def _analyze_response_depth(self, response_text: str) -> str:
        """Analyze response depth (simplified - could use LLM)."""
        word_count = len(response_text.split())
        if word_count < 10:
            return "surface"
        elif word_count < 30:
            return "moderate"
        return "deep"
