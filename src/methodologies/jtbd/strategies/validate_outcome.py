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
        for node in graph_state.nodes:
            if node.node_type in ("outcome", "benefit", "job_statement"):
                return node.label
        return None
