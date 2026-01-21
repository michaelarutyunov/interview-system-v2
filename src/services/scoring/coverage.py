"""Coverage scorer - ensures stimulus elements are addressed.

Boosts coverage strategies when gaps exist in the interview.
"""

from typing import Any, Dict, List

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.base import ScorerBase, ScorerOutput


logger = structlog.get_logger(__name__)


class CoverageScorer(ScorerBase):
    """
    Ensure all stimulus elements are addressed.

    Algorithm:
    1. Check coverage gaps from session config
    2. Boost coverage strategies when gaps exist
    3. Higher boost for more critical gaps

    Scoring:
    - 1.0 = complete coverage (no gaps)
    - gap_boost (e.g., 2.0) = gaps exist, boost coverage strategies

    Configuration parameters:
    - gap_boost: Multiplier for coverage strategies when gaps exist (default: 2.0)
    - coverage_threshold: Coverage ratio below which gaps are considered (default: 0.8)
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.gap_boost = self.params.get("gap_boost", 2.0)
        self.coverage_threshold = self.params.get("coverage_threshold", 0.8)

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
    ) -> ScorerOutput:
        """
        Score based on element coverage.

        Args:
            strategy: Strategy dict with 'type_category'
            focus: Focus dict (unused for coverage scorer)
            graph_state: Graph state with coverage info
            recent_nodes: Recent nodes (unused for coverage scorer)

        Returns:
            ScorerOutput with coverage-based score
        """
        score = 1.0
        signals = {}
        reasons = []

        # Get coverage info from session (passed via graph_state properties)
        # For v2, coverage tracked in session.config.elements_seen
        elements_total = graph_state.properties.get("elements_total", 0)
        elements_seen = graph_state.properties.get("elements_seen", set())

        signals["elements_total"] = elements_total
        signals["elements_seen_count"] = len(elements_seen) if isinstance(elements_seen, set) else 0

        # Calculate coverage ratio
        if elements_total > 0:
            seen_count = len(elements_seen) if isinstance(elements_seen, set) else 0
            coverage_ratio = seen_count / elements_total
        else:
            coverage_ratio = 1.0  # No elements = full coverage

        signals["coverage_ratio"] = coverage_ratio
        signals["has_gaps"] = coverage_ratio < self.coverage_threshold

        # Apply boost for coverage strategies when gaps exist
        if coverage_ratio < self.coverage_threshold:
            if strategy.get("type_category") == "coverage":
                score *= self.gap_boost
                reasons.append(
                    f"Coverage gaps exist ({coverage_ratio:.1%} < {self.coverage_threshold:.1%})"
                )
        else:
            reasons.append(f"Good coverage ({coverage_ratio:.1%})")

        reasoning = "; ".join(reasons) if reasons else "Coverage complete"

        logger.debug(
            "CoverageScorer output",
            strategy_id=strategy.get("id"),
            coverage_ratio=coverage_ratio,
            score=score,
        )

        return self.make_output(score, signals, reasoning)
