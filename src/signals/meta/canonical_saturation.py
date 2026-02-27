"""Canonical saturation signal from novelty ratio.

Measures what fraction of this turn's surface extraction was thematically
redundant at the canonical level. High saturation means new surface nodes
are deduplicating into existing canonical slots — the respondent is
elaborating on known themes rather than introducing new ones.
"""

from src.signals.signal_base import SignalDetector


class CanonicalSaturationSignal(SignalDetector):
    """Canonical novelty ratio: new canonical slots / new surface nodes.

    Formula: saturation = 1.0 - min(canonical_delta / surface_delta, 1.0)

    Output: 0.0 (all new themes) to 1.0 (pure deduplication).
    Returns empty dict if canonical slots are disabled.
    Instantaneous per-turn, no smoothing.

    Namespaced signal: meta.canonical.saturation
    Cost: low (reads from ContextLoadingOutput, graph_state, canonical_graph_state)
    Refresh: per_turn
    """

    signal_name = "meta.canonical.saturation"
    description = "Canonical novelty ratio: 0=all extraction is thematically new, 1=pure deduplication into existing canonical slots."
    dependencies = []

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        clo = context.context_loading_output

        # Check if canonical graph is available
        cg_state = context.canonical_graph_state
        if cg_state is None:
            return {}

        # Surface delta this turn
        prev_surface = clo.prev_surface_node_count
        current_surface = graph_state.node_count if graph_state else 0
        surface_delta = max(current_surface - prev_surface, 0)

        # Canonical delta this turn
        prev_canonical = clo.prev_canonical_node_count
        current_canonical = cg_state.concept_count
        canonical_delta = max(current_canonical - prev_canonical, 0)

        if surface_delta > 0:
            novelty_ratio = min(canonical_delta / surface_delta, 1.0)
        else:
            novelty_ratio = 1.0  # no extraction — not saturated

        saturation = 1.0 - novelty_ratio
        return {self.signal_name: round(saturation, 4)}
