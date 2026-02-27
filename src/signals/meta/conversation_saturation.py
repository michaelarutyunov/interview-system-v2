"""Conversation saturation signal from extraction yield ratio.

Measures how much extractable content the respondent is producing compared
to their peak turn. High saturation means the respondent's answers are
yielding fewer new surface nodes than their best turn — responses are
drying up regardless of engagement quality.
"""

from src.signals.signal_base import SignalDetector


class ConversationSaturationSignal(SignalDetector):
    """Extraction yield ratio: current surface node yield vs peak.

    Formula: saturation = 1.0 - min(current_delta / peak, 1.0)

    Output: 0.0 (matching or exceeding peak extraction) to 1.0 (zero extraction).
    Instantaneous per-turn, no smoothing.

    Namespaced signal: meta.conversation.saturation
    Cost: low (reads from ContextLoadingOutput and graph_state)
    Refresh: per_turn
    """

    signal_name = "meta.conversation.saturation"
    description = "Extraction yield ratio: 0=extracting at peak rate, 1=zero extraction. Compares this turn's new surface nodes to the session's peak extraction turn."
    dependencies = []

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        clo = context.context_loading_output
        peak = clo.surface_velocity_peak

        # Current turn's surface node delta
        prev_surface = clo.prev_surface_node_count
        current_surface = graph_state.node_count if graph_state else 0
        surface_delta = max(current_surface - prev_surface, 0)

        if peak > 0:
            yield_ratio = surface_delta / peak
        else:
            yield_ratio = 1.0  # first turn, no peak yet — not saturated

        saturation = 1.0 - min(yield_ratio, 1.0)
        return {self.signal_name: round(saturation, 4)}
