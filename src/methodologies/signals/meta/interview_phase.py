"""Interview phase detection signal.

Detects the current interview phase based on graph state:
- early: Initial exploration, building graph structure
- mid: Building depth and connections
- late: Validation and verification
"""

from src.methodologies.signals.common import (
    SignalDetector,
    SignalCostTier,
    RefreshTrigger,
)


class InterviewPhaseSignal(SignalDetector):
    """Detect interview phase based on graph state.

    Uses graph state metrics to determine interview phase:
    - node_count: Total number of nodes in graph
    - max_depth: Maximum depth of the graph
    - orphan_count: Number of orphan nodes (no connections)

    Phase boundaries are configurable per methodology via YAML config.
    Falls back to default boundaries (5/15) if not specified.

    Namespaced signal: meta.interview.phase
    Cost: free (O(1) lookup from graph_state)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "meta.interview.phase"
    description = "Current interview phase: 'early', 'mid', or 'late'. Phase boundaries are configurable per methodology. Used to adjust strategy weights."
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    # Default phase boundaries (fallback if not specified in YAML)
    DEFAULT_BOUNDARIES = {
        "early_max_nodes": 5,
        "mid_max_nodes": 15,
    }

    async def detect(self, context, graph_state, response_text):
        """Detect interview phase from graph state.

        Args:
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text (not used)

        Returns:
            Dict with single key: {self.signal_name: "early" | "mid" | "late"}
        """
        # Get phase boundaries from methodology config
        boundaries = self._get_phase_boundaries(context)

        # Extract graph state metrics
        node_count = getattr(graph_state, "node_count", 0)
        orphan_count = self._get_orphan_count(graph_state)

        # Determine phase using methodology-specific boundaries
        phase = self._determine_phase(
            node_count,
            orphan_count,
            boundaries["early_max_nodes"],
            boundaries["mid_max_nodes"],
        )

        return {self.signal_name: phase}

    def _get_phase_boundaries(self, context) -> dict:
        """Get phase boundaries from methodology config.

        Args:
            context: Pipeline context with methodology property

        Returns:
            Dict with 'early_max_nodes' and 'mid_max_nodes' keys
        """
        # Get boundaries from the first phase that has them defined
        # (all phases should have the same boundaries, but we check in order)
        from src.methodologies.registry import MethodologyRegistry

        try:
            methodology = getattr(context, "methodology", None)
            if not methodology:
                return self.DEFAULT_BOUNDARIES

            registry = MethodologyRegistry()
            config = registry.get_methodology(methodology)

            if config.phases:
                for phase_config in config.phases.values():
                    if phase_config.phase_boundaries:
                        return phase_config.phase_boundaries
        except Exception:
            # Fall back to defaults on any error
            pass

        return self.DEFAULT_BOUNDARIES

    def _determine_phase(
        self,
        node_count: int,
        orphan_count: int,
        early_max_nodes: int,
        mid_max_nodes: int,
    ) -> str:
        """Determine interview phase from graph metrics.

        Args:
            node_count: Total number of nodes
            orphan_count: Number of orphan nodes
            early_max_nodes: Node count threshold for early phase
            mid_max_nodes: Node count threshold for mid phase

        Returns:
            Phase: "early" | "mid" | "late"
        """
        if node_count < early_max_nodes:
            return "early"
        elif node_count < mid_max_nodes or orphan_count > 3:
            return "mid"
        else:
            return "late"

    def _get_orphan_count(self, graph_state) -> int:
        """Get orphan count from graph state.

        Args:
            graph_state: Current knowledge graph state

        Returns:
            Number of orphan nodes (nodes with no connections)
        """
        return getattr(graph_state, "orphan_count", 0)
