"""Strategy selector service.

Orchestrates multi-dimensional strategy selection using the arbitration engine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.arbitration import ArbitrationEngine
from src.services.scoring.base import ScorerOutput


logger = structlog.get_logger(__name__)


@dataclass
class StrategyCandidate:
    """A scored (strategy, focus) combination."""
    strategy: Dict[str, Any]
    focus: Dict[str, Any]
    score: float
    scorer_outputs: List[ScorerOutput] = field(default_factory=list)
    reasoning: List[str] = field(default_factory=list)
    is_vetoed: bool = False


@dataclass
class SelectionResult:
    """Result of strategy selection."""
    selected_strategy: Dict[str, Any]
    selected_focus: Dict[str, Any]
    final_score: float
    scorer_outputs: List[ScorerOutput] = field(default_factory=list)
    scoring_reasoning: List[str] = field(default_factory=list)
    alternative_strategies: List[StrategyCandidate] = field(default_factory=list)
    selection_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Strategy definitions (simplified from v1)
STRATEGIES = [
    {
        "id": "deepen",
        "name": "Deepen Understanding",
        "type_category": "depth",
        "priority_base": 1.0,
        "enabled": True,
    },
    {
        "id": "broaden",
        "name": "Explore Breadth",
        "type_category": "breadth",
        "priority_base": 0.9,
        "enabled": True,
    },
    {
        "id": "cover_element",
        "name": "Cover Stimulus Element",
        "type_category": "coverage",
        "priority_base": 1.1,
        "enabled": True,
    },
]


class StrategyService:
    """
    Orchestrates strategy selection using multi-dimensional scoring.

    Features:
    - Applicability filtering based on state conditions
    - Dynamic focus generation per strategy type
    - Fallback logic when no strategies applicable
    - Top alternatives for transparency
    """

    def __init__(
        self,
        arbitration_engine: ArbitrationEngine,
        config: Dict[str, Any] = None,
    ):
        """
        Initialize strategy selector.

        Args:
            arbitration_engine: Configured arbitration engine with all scorers
            config: Selector configuration
        """
        self.arbitration_engine = arbitration_engine
        self.config = config or {}
        self.strategies = {s["id"]: s for s in STRATEGIES if s.get("enabled", True)}

        # Configuration
        self._alternatives_count = self.config.get("alternatives_count", 3)
        self._alternatives_min_score = self.config.get("alternatives_min_score", 0.3)

        logger.info(
            "StrategyService initialized",
            num_strategies=len(self.strategies),
            strategy_ids=list(self.strategies.keys()),
        )

    async def select(
        self,
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
    ) -> SelectionResult:
        """
        Select the best strategy for the current state.

        Algorithm:
        1. Filter applicable strategies
        2. Generate focuses for each applicable strategy
        3. Score all (strategy, focus) pairs
        4. Select highest-scoring combination
        5. Return result with top alternatives

        Args:
            graph_state: Current graph state
            recent_nodes: List of recent nodes from last N turns

        Returns:
            SelectionResult with selected strategy, focus, and alternatives
        """
        logger.debug(
            "Starting strategy selection",
            turn_count=graph_state.properties.get("turn_count", 0),
        )

        # Score all (strategy, focus) combinations
        candidates: List[StrategyCandidate] = []

        for strategy in self.strategies.values():
            # Generate possible focuses
            focuses = self._get_possible_focuses(strategy, graph_state)

            if not focuses:
                logger.debug(
                    "No focuses generated for strategy",
                    strategy_id=strategy["id"],
                )
                continue

            # Score each (strategy, focus) pair
            for focus in focuses:
                try:
                    score, outputs, reasoning = await self.arbitration_engine.score(
                        strategy, focus, graph_state, recent_nodes
                    )

                    # Check if vetoed
                    is_vetoed = score < self._veto_threshold()

                    candidate = StrategyCandidate(
                        strategy=strategy,
                        focus=focus,
                        score=score,
                        scorer_outputs=outputs,
                        reasoning=reasoning,
                        is_vetoed=is_vetoed,
                    )
                    candidates.append(candidate)

                    logger.debug(
                        "Candidate scored",
                        strategy_id=strategy["id"],
                        focus_type=focus.get("focus_type"),
                        score=score,
                        is_vetoed=is_vetoed,
                    )

                except Exception as e:
                    logger.warning(
                        "Failed to score candidate",
                        strategy_id=strategy["id"],
                        focus_type=focus.get("focus_type"),
                        error=str(e),
                    )
                    continue

        # Handle no valid candidates
        if not candidates:
            logger.warning("No valid candidates - using fallback")
            return await self._get_fallback_result(graph_state, recent_nodes)

        # Sort candidates by score (descending)
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Select top candidate
        top_candidate = candidates[0]

        # Get alternatives (top N, excluding selected, score >= threshold)
        alternatives = [
            c
            for c in candidates[1 : self._alternatives_count + 1]
            if c.score >= self._alternatives_min_score
        ]

        logger.info(
            "Strategy selected",
            strategy_id=top_candidate.strategy["id"],
            focus_type=top_candidate.focus.get("focus_type"),
            score=top_candidate.score,
            num_alternatives=len(alternatives),
            is_vetoed=top_candidate.is_vetoed,
        )

        return SelectionResult(
            selected_strategy=top_candidate.strategy,
            selected_focus=top_candidate.focus,
            final_score=top_candidate.score,
            scorer_outputs=top_candidate.scorer_outputs,
            scoring_reasoning=top_candidate.reasoning,
            alternative_strategies=alternatives,
        )

    def _get_possible_focuses(
        self,
        strategy: Dict[str, Any],
        graph_state: GraphState,
    ) -> List[Dict[str, Any]]:
        """
        Generate possible focus targets for a strategy.

        Focus generation logic per strategy type:
        - deepen: focus on most recent high-confidence node
        - broaden: single open focus
        - cover_element: one focus per uncovered element

        Args:
            strategy: Strategy dict
            graph_state: Current graph state

        Returns:
            List of possible focuses
        """
        strategy_id = strategy["id"]
        focuses: List[Dict[str, Any]] = []

        # Depth strategy: focus on most recent node
        if strategy_id == "deepen":
            # Get recent nodes from graph_state (passed in properties)
            recent_nodes = graph_state.properties.get("recent_nodes", [])
            if recent_nodes:
                # Focus on the most recent node
                last_node = recent_nodes[-1]
                focuses.append({
                    "node_id": last_node.get("id"),
                    "focus_type": "depth_exploration",
                    "focus_description": f"Deepen: {last_node.get('label', 'topic')}",
                    "confidence": 0.8,
                })
            else:
                # Fallback: open depth focus
                focuses.append({
                    "focus_type": "depth_exploration",
                    "focus_description": "Deepen understanding",
                    "confidence": 0.5,
                })

        # Breadth strategy: single open focus
        elif strategy_id == "broaden":
            focuses.append({
                "focus_type": "breadth_exploration",
                "focus_description": "Explore new aspects",
                "confidence": 1.0,
            })

        # Coverage strategy: one focus per uncovered element
        elif strategy_id == "cover_element":
            elements_seen = graph_state.properties.get("elements_seen", set())
            elements_total = graph_state.properties.get("elements_total", [])

            uncovered = [e for e in elements_total if e not in elements_seen]

            for element in uncovered:
                focuses.append({
                    "element_id": element,
                    "focus_type": "coverage_gap",
                    "focus_description": f"Cover: {element}",
                    "confidence": 1.0,
                })

        return focuses

    async def _get_fallback_result(
        self,
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
    ) -> SelectionResult:
        """Return fallback strategy when no candidates available."""
        # Use broaden as fallback
        strategy = self.strategies.get("broaden", STRATEGIES[1])
        focus = {
            "focus_type": "breadth_exploration",
            "focus_description": "Fallback: Explore new aspects",
            "confidence": 0.5,
        }

        score, outputs, reasoning = await self.arbitration_engine.score(
            strategy, focus, graph_state, recent_nodes
        )

        return SelectionResult(
            selected_strategy=strategy,
            selected_focus=focus,
            final_score=score,
            scorer_outputs=outputs,
            scoring_reasoning=reasoning,
        )

    def _veto_threshold(self) -> float:
        """Get global veto threshold from config."""
        return self.config.get("veto_threshold", 0.1)

    def __repr__(self) -> str:
        return (
            f"StrategyService("
            f"num_strategies={len(self.strategies)}, "
            f"alternatives_count={self._alternatives_count})"
        )
