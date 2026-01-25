"""Coverage Gap scorer (Tier 2).

Measures how many coverage gaps the focus addresses.
Boosts strategies that fill missing knowledge gaps.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


class CoverageGapScorer(Tier2Scorer):
    """
    Scores candidates based on how many coverage gaps they address.

    Coverage gap types:
    - unmentioned: Element not yet mentioned in interview
    - no_reaction: Element mentioned but no respondent reaction
    - no_comprehension: Element mentioned but unclear understanding
    - unconnected: Element not connected to other graph elements

    Scoring logic:
    - 0 gaps → score ≈ 0.8 (slight penalty, already covered)
    - 1-2 gaps → score ≈ 1.2 (moderate boost)
    - 3+ gaps → score ≈ 1.5 (strong boost, fills many gaps)

    Weight: 0.20-0.25 (high - coverage is primary goal)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Default weight for coverage scorer
        if "weight" not in self.config:
            self.weight = 0.20

        # Gap types to consider
        self.gap_types = self.params.get(
            "gap_types",
            ["unmentioned", "no_reaction", "no_comprehension", "unconnected"],
        )

        # Boost per gap addressed
        self.boost_per_gap = self.params.get("boost_per_gap", 0.15)

        logger.info(
            "CoverageGapScorer initialized",
            weight=self.weight,
            gap_types=self.gap_types,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],  # noqa: ARG001 - reserved for future use
        conversation_history: List[Dict[str, str]],  # noqa: ARG001 - reserved for future use
    ) -> Tier2Output:
        """Score based on coverage gaps addressed by this focus.

        Phase 5 enhancement: Depth-aware scoring.
        - Uncovered element → +2 priority (high)
        - Covered but shallow (depth < 0.5) → +1 priority (medium)

        Args:
            strategy: Strategy being evaluated
            focus: Focus target (may contain element_id)
            graph_state: Current graph state with coverage info
            recent_nodes: Recent nodes from graph
            conversation_history: Conversation history

        Returns:
            Tier2Output with score based on gaps addressed
        """
        # Get element_id from focus if available
        element_id = focus.get("element_id")

        # Count gaps this focus addresses
        gaps_addressed = 0
        gap_details = []

        # Try new coverage_state structure first (Phase 4+)
        if graph_state.coverage_state:
            coverage_state = graph_state.coverage_state
            elements = coverage_state.elements or {}

            if element_id is not None and element_id in elements:
                element_coverage = elements[element_id]

                # Check if element is uncovered (high priority)
                if not element_coverage.covered:
                    gaps_addressed += 2
                    gap_details.append(f"uncovered:{element_id}")
                # Check if element is shallow (medium priority)
                elif element_coverage.depth_score < 0.5:
                    gaps_addressed += 1
                    gap_details.append(
                        f"shallow:{element_id}(depth={element_coverage.depth_score:.2f})"
                    )
        else:
            # Fallback to old coverage_state structure (pre-Phase 4)
            coverage_state = graph_state.properties.get("coverage_state", {})
            elements_seen = set(coverage_state.get("elements_seen", []))
            elements_total = set(coverage_state.get("elements_total", []))

            if element_id and element_id in elements_total:
                # Check if this element is unmentioned
                if element_id not in elements_seen:
                    gaps_addressed += 1
                    gap_details.append(f"unmentioned:{element_id}")

        # Also check strategy type - coverage strategy gets automatic boost
        strategy_type = strategy.get("type_category", "")
        if strategy_type == "coverage" and gaps_addressed == 0:
            # Coverage strategy with no specific gap - still small boost
            # for breadth exploration
            gaps_addressed = 1
            gap_details.append("coverage_exploration")

        # Calculate score based on gaps addressed
        # Base 1.0 (neutral) + boost per gap
        raw_score = 1.0 + (gaps_addressed * self.boost_per_gap)

        # Clamp to range [0.5, 1.8]
        raw_score = max(0.5, min(1.8, raw_score))

        # If no gaps and not a coverage strategy, slight penalty
        if gaps_addressed == 0 and strategy_type != "coverage":
            raw_score = 0.85

        signals = {
            "gaps_addressed": gaps_addressed,
            "gap_details": gap_details,
            "element_id": element_id,
            "strategy_type": strategy_type,
        }

        reasoning = f"Addresses {gaps_addressed} coverage gap(s)" + (
            f": {', '.join(gap_details)}" if gap_details else ""
        )

        logger.debug(
            "CoverageGapScorer scored",
            score=raw_score,
            gaps_addressed=gaps_addressed,
            reasoning=reasoning,
        )

        return self.make_output(
            raw_score=raw_score, signals=signals, reasoning=reasoning
        )
