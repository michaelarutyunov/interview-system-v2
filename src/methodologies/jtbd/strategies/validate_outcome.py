from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    pass


class ValidateOutcomeStrategy(BaseStrategy):
    """Validate if the solution worked and understand success criteria."""

    name = "validate_outcome"
    description = "Verify if job was done and understand success criteria"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "job_identified": 0.3,
            "outcome_clarity": -0.5,
            "situation_depth": 0.2,  # Need context before outcome
            "strategy_repetition_count": -0.2,
        }

    async def generate_focus(self, context, graph_state) -> Optional[str]:
        # Use nodes_by_type to find outcome nodes
        outcome_nodes = (
            graph_state.nodes_by_type.get("outcome", []) +
            graph_state.nodes_by_type.get("benefit", []) +
            graph_state.nodes_by_type.get("job_statement", [])
        )
        if outcome_nodes:
            node = outcome_nodes[-1]
            return node.get("label") if isinstance(node, dict) else node.label
        return None
