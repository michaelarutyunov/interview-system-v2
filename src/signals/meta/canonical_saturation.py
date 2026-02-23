"""Canonical saturation signal from canonical graph velocity.

Parallel to ConversationSaturationSignal but uses canonical (deduplicated)
concept velocity. Enables empirical comparison — hypothesis is that
conversational graph may produce better results.
"""

from src.signals.signal_base import SignalDetector


class CanonicalSaturationSignal(SignalDetector):
    """Estimate interview saturation from canonical graph velocity.

    Computes saturation score (0.0-1.0) using the same formula as
    ConversationSaturationSignal but reads from canonical graph state.

    Returns empty dict if canonical slots are disabled (feature flag).

    Namespaced signal: meta.canonical.saturation
    Cost: low (reads from ContextLoadingOutput and canonical_graph_state)
    Refresh: per_turn
    """

    signal_name = "meta.canonical.saturation"
    description = "Interview saturation from canonical graph: 0=still learning, 1=saturated. Combines canonical concept velocity decay (primary), canonical edge density (graph richness), and turn floor."
    dependencies = []

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate canonical saturation from velocity, density, and turns.

        Args:
            context: Pipeline context with ContextLoadingOutput and
                canonical_graph_state
            graph_state: Current knowledge graph state (unused, uses canonical)
            response_text: User's response text (unused)

        Returns:
            Dict with meta.canonical.saturation: float (0.0-1.0)
            Returns empty dict if canonical_graph_state is None.
        """
        # Load canonical velocity state from ContextLoadingOutput
        clo = context.context_loading_output
        ewma = clo.canonical_velocity_ewma
        peak = clo.canonical_velocity_peak

        # Check if canonical graph is available
        cg_state = context.canonical_graph_state
        if cg_state is None:
            # Canonical slots disabled — signal not applicable
            return {}

        # Component 1: velocity decay (primary, 60%)
        if peak > 0:
            velocity_decay = 1.0 - (ewma / peak)
        else:
            velocity_decay = 0.0
        velocity_decay = max(0.0, min(1.0, velocity_decay))

        # Component 2: canonical edge density (25%)
        concept_count = cg_state.concept_count
        edge_count = cg_state.edge_count
        if concept_count > 0:
            raw_density = edge_count / concept_count
            edge_density_norm = min(raw_density / 2.0, 1.0)
        else:
            edge_density_norm = 0.0

        # Component 3: turn floor (15%)
        turn_floor = min(context.turn_number / 15.0, 1.0)

        saturation = 0.60 * velocity_decay + 0.25 * edge_density_norm + 0.15 * turn_floor

        return {self.signal_name: round(saturation, 4)}
