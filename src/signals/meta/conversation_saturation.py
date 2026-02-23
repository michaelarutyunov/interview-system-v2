"""Conversation saturation signal from surface graph velocity.

Measures interview saturation using information velocity — the rate at which
new concepts are being discovered. When velocity decays (slowing discovery),
the interview approaches theoretical saturation.

Combines three components:
- 60% velocity decay (primary indicator)
- 25% edge density (graph richness)
- 15% turn floor (minimum duration)
"""

from src.signals.signal_base import SignalDetector


class ConversationSaturationSignal(SignalDetector):
    """Estimate interview saturation from surface graph velocity.

    Computes saturation score (0.0-1.0) combining velocity decay,
    edge density, and turn floor. Higher values indicate the interview
    is approaching theoretical saturation (few new concepts).

    Scoring components (weighted sum):
    - Velocity decay (60%): 1 - (ewma / peak), high when discovery slows
    - Edge density (25%): edges/nodes normalized to 2.0, measures richness
    - Turn floor (15%): turn_number / 15, prevents early saturation signal

    Namespaced signal: meta.conversation.saturation
    Cost: low (reads from ContextLoadingOutput and graph_state)
    Refresh: per_turn
    """

    signal_name = "meta.conversation.saturation"
    description = "Interview saturation from surface graph: 0=still learning, 1=saturated. Combines node velocity decay (primary), edge density (graph richness), and turn floor (minimum duration)."
    dependencies = []

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate conversation saturation from velocity, density, and turns.

        Args:
            context: Pipeline context with ContextLoadingOutput containing
                velocity state (ewma, peak, prev counts)
            graph_state: Current knowledge graph state (for edge density)
            response_text: User's response text (unused)

        Returns:
            Dict with meta.conversation.saturation: float (0.0-1.0)
        """
        # Load velocity state from ContextLoadingOutput
        clo = context.context_loading_output
        ewma = clo.surface_velocity_ewma
        peak = clo.surface_velocity_peak

        # Component 1: velocity decay (primary, 60%)
        # High when new nodes are arriving slower than peak rate
        if peak > 0:
            velocity_decay = 1.0 - (ewma / peak)
        else:
            velocity_decay = 0.0
        velocity_decay = max(0.0, min(1.0, velocity_decay))

        # Component 2: edge density (graph richness, 25%)
        # Plateau at 2.0 edges/node (well-connected graph)
        node_count = graph_state.node_count if graph_state else 0
        edge_count = graph_state.edge_count if graph_state else 0
        if node_count > 0:
            raw_density = edge_count / node_count
            edge_density_norm = min(raw_density / 2.0, 1.0)
        else:
            edge_density_norm = 0.0

        # Component 3: turn floor (absolute minimum, 15%)
        # Prevents early saturation signal on turn 1-2
        turn_floor = min(context.turn_number / 15.0, 1.0)

        saturation = 0.60 * velocity_decay + 0.25 * edge_density_norm + 0.15 * turn_floor

        return {self.signal_name: round(saturation, 4)}
