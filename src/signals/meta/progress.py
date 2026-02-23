"""Meta progress signals for interview completion estimation.

Provides interview progress metrics that indicate when the conversation
has sufficient coverage to begin closing. Progress is computed from
structural graph signals (chain completion and depth) rather than
raw counts.
"""

from src.core.schema_loader import load_methodology
from src.signals.signal_base import SignalDetector


class InterviewProgressSignal(SignalDetector):
    """Estimate overall interview progress from chain completion and depth.

    Computes a weighted progress score (0.0-1.0) combining two structural
    graph health metrics to determine interview maturity. Higher values
    suggest sufficient coverage for closing strategies.

    Scoring components (weighted average):
    - Chain completion (50%): Ratio of level-1 nodes with complete chains
    - Graph depth (50%): Normalized by ontology level count

    Depth is normalized using the ontology structure: a depth equal to the
    number of ontology levels means full chain depth has been reached.

    DEPRECATED for JTBD: Replaced by meta.conversation.saturation and
    meta.canonical.saturation signals which are methodology-agnostic and
    based on information velocity rather than structural completeness.
    Do NOT add this signal to jobs_to_be_done.yaml signals list or any
    JTBD strategy signal_weights — its absence is intentional and correct.

    Retained in means_end_chain.yaml where chain_completion is meaningful
    for Means-End Chain methodology.

    Namespaced signal: meta.interview_progress
    Cost: low (composes from existing signals in context.signals)
    Refresh: per_turn (recomputed each turn after signal detection)
    """

    signal_name = "meta.interview_progress"
    description = "Overall interview progress from 0-1. 0 = just started, 1 = near completion. Combines chain completion and graph depth. Higher values suggest we can start closing."
    dependencies = [
        "graph.chain_completion.ratio",
        "graph.max_depth",
    ]

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate interview progress from chain completion and depth.

        Composes progress score from two structural graph health metrics.
        Depth is normalized by ontology level count (exact structural bound).

        Args:
            context: Pipeline context with signals dict containing dependency values
            graph_state: Current knowledge graph state (unused, composed from signals)
            response_text: User's response text (unused, composed from signals)

        Returns:
            Dict with meta.interview_progress: float (0.0-1.0)
        """
        # Need signals dict to compose from
        if not hasattr(context, "signals") or not context.signals:
            return {self.signal_name: 0.0}

        signals = context.signals

        # Component 1: Chain completion ratio (0-1), already computed at source
        chain_completion = signals.get("graph.chain_completion.ratio", 0.0)

        # Component 2: Depth normalized by ontology level count
        max_depth = signals.get("graph.max_depth", 0)
        ontology_levels = self._get_ontology_level_count(context)
        depth_score = min(max(max_depth / ontology_levels, 0.0), 1.0)

        # Combine components (weighted average)
        progress = (chain_completion * 0.5) + (depth_score * 0.5)

        return {self.signal_name: progress}

    def _get_ontology_level_count(self, context) -> float:
        """Get the number of ontology levels from methodology config.

        Uses the ontology node type count as the structural maximum for
        depth normalization. Falls back to 5 (common for MEC-style chains).

        Returns:
            Number of ontology levels as a float (for division).
        """
        methodology = getattr(context, "methodology", None)
        if not methodology:
            return 5.0

        try:
            schema = load_methodology(methodology)
            if schema.ontology and schema.ontology.nodes:
                return float(len(schema.ontology.nodes))
        except Exception:
            pass

        return 5.0
