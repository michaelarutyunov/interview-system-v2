from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    pass


class BalanceCoverageStrategy(BaseStrategy):
    """
    Meta-strategy to explore least-covered dimension.

    Delegates to appropriate strategy based on coverage gaps.
    """

    name = "balance_coverage"
    description = "Explore the least-covered JTBD dimension"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "coverage_imbalance": 0.5,  # High when unbalanced
            "job_identified": 0.2,  # Need job first
            "strategy_repetition_count": -0.1,
        }

    async def generate_focus(self, context, graph_state) -> Optional[str]:
        # This would redirect to appropriate strategy based on least_covered_dimension
        # For now, return None (will be handled by question generation)
        return None
