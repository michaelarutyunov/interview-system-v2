"""Interview phase detection signal.

Detects the current interview phase based on graph state:
- early: Initial exploration, building graph structure
- mid: Building depth and connections
- late: Validation and verification
"""

from src.core.exceptions import ConfigurationError
from src.methodologies.signals.signal_base import SignalDetector


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
            Dict with phase, phase_reason, and is_late_stage signals:
            {
                "meta.interview.phase": "early" | "mid" | "late",
                "meta.interview.phase_reason": str,
                "meta.interview.is_late_stage": bool,
            }
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

        # Build phase reason for logging/debugging
        phase_reason = (
            f"node_count={node_count}, orphan_count={orphan_count}, "
            f"phase={phase}, boundaries=early<{boundaries['early_max_nodes']}, "
            f"mid<{boundaries['mid_max_nodes']}"
        )

        return {
            self.signal_name: phase,
            "meta.interview.phase_reason": phase_reason,
            "meta.interview.is_late_stage": phase == "late",
        }

    def _get_phase_boundaries(self, context) -> dict:
        """Get phase boundaries from methodology config.

        Args:
            context: Pipeline context with methodology property

        Returns:
            Dict with 'early_max_nodes' and 'mid_max_nodes' keys

        Raises:
            ConfigurationError: If methodology config fails to load due to
                malformed YAML, missing methodology, or registry errors.
                Does NOT raise for valid configs with missing phase_boundaries.
        """
        # Get boundaries from the first phase that has them defined
        # (all phases should have the same boundaries, but we check in order)
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
                        return phase_config.phase_boundaries

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
        elif node_count < mid_max_nodes:
            return "mid"
        else:
            return "late"

        # NOTE: If testing reveals that respondents who are less verbose need
        # additional time in mid-phase before transitioning, the following
        # condition can be added to the mid-phase check:
        #   or orphan_count > 3
        # This keeps the interview in mid-phase while graph structure is
        # still being built (high orphan count indicates incomplete chains).

    def _get_orphan_count(self, graph_state) -> int:
        """Get orphan count from graph state.

        Args:
            graph_state: Current knowledge graph state

        Returns:
            Number of orphan nodes (nodes with no connections)
        """
        return getattr(graph_state, "orphan_count", 0)
