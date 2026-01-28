from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext


class LadderDeeperStrategy(BaseStrategy):
    """
    Continue laddering to reach terminal values.

    Asks "Why does that matter?" to move up the means-end chain.
    """

    name = "ladder_deeper"
    description = "Continue laddering from current concept toward terminal values"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "missing_terminal_value": 0.4,  # High if no values yet
            "response_confidence": 0.2,  # Needs clear response to ladder
            "new_concepts_mentioned": 0.2,  # Good if new concepts emerged
            "strategy_repetition_count": -0.15,  # Discourage stuck in loop
            "ladder_depth": -0.1,  # Less needed if already deep
        }

    async def generate_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
    ) -> Optional[str]:
        """Find the most recent concept to ladder from."""
        # Use recent_nodes from context instead of graph_state.nodes
        # Prefer most recent non-value node
        type_priority = [
            "psychosocial_consequence",
            "functional_consequence",
            "attribute",
        ]

        for node in reversed(context.recent_nodes):
            if node.node_type in type_priority:
                return node.label

        return None
