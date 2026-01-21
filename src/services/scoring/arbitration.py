"""Arbitration engine for multi-dimensional strategy scoring.

Combines scores from 5 scorers using multiplicative formula to produce
emergent adaptive behavior.
"""

from typing import Any, Dict, Tuple

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.base import ScorerBase, ScorerOutput


logger = structlog.get_logger(__name__)


class ArbitrationEngine:
    """
    Applies multi-dimensional scoring to strategy/focus pairs.

    Combines scores from 5 independent scorers using multiplicative formula:
    final_score = strategy.priority_base × ∏(scorer_output^weight)

    Features:
    - Early exit on per-scorer veto thresholds
    - Transparent scoring provenance (all scores logged)
    - Error handling for failed scorers
    """

    def __init__(self, scorers: list[ScorerBase], config: Dict[str, Any] = None):
        """
        Initialize arbitration engine.

        Args:
            scorers: All 5 scorers (only enabled ones will be used)
            config: Arbitration configuration
        """
        self.scorers = [s for s in scorers if s.enabled]
        self.config = config or {}

        # Configuration
        self._veto_threshold = self.config.get("veto_threshold", 0.1)
        self._score_precision = self.config.get("score_precision", 4)

        logger.info(
            "ArbitrationEngine initialized",
            num_scorers=len(self.scorers),
            enabled_scorers=[s.__class__.__name__ for s in self.scorers],
            veto_threshold=self._veto_threshold,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list[Dict[str, Any]],
    ) -> Tuple[float, list[ScorerOutput], list[str]]:
        """
        Score a strategy/focus combination using all scorers.

        Applies multiplicative scoring formula:
        final_score = strategy.priority_base
        for each scorer:
            weighted_score = raw_score ** scorer.weight
            final_score *= weighted_score
            if final_score < scorer.veto_threshold:
                break  # Per-scorer veto

        Args:
            strategy: Strategy dict with 'priority_base'
            focus: Focus dict
            graph_state: Current graph state
            recent_nodes: List of recent nodes

        Returns:
            Tuple of:
            - final_score: Cumulative multiplicative score
            - scorer_outputs: List of individual scorer results
            - reasoning_steps: Step-by-step score evolution for debugging
        """
        base_score = strategy.get("priority_base", 1.0)
        score = base_score
        outputs = []
        reasoning = [f"Base: {base_score:.{self._score_precision}f}"]

        logger.debug(
            "Starting arbitration",
            strategy_id=strategy.get("id"),
            focus_type=focus.get("focus_type"),
            priority_base=base_score,
        )

        for scorer in self.scorers:
            try:
                # Apply scorer
                output = await scorer.score(strategy, focus, graph_state, recent_nodes)
                outputs.append(output)

                # Score is already weighted by scorer.make_output()
                score *= output.weighted_score

                # Format reasoning step
                step = (
                    f"{output.scorer_name}: "
                    f"{output.raw_score:.{self._score_precision}f}^{output.weight:.1f}="
                    f"{output.weighted_score:.{self._score_precision}f} → "
                    f"cumulative={score:.{self._score_precision}f}"
                )
                reasoning.append(step)

                # Check per-scorer veto threshold
                if score < scorer.veto_threshold:
                    veto_msg = (
                        f"VETOED by {output.scorer_name} "
                        f"(score={score:.{self._score_precision}f} < "
                        f"threshold={scorer.veto_threshold})"
                    )
                    reasoning.append(veto_msg)
                    logger.warning(
                        "Scorer veto triggered",
                        scorer=output.scorer_name,
                        final_score=score,
                        veto_threshold=scorer.veto_threshold,
                        strategy_id=strategy.get("id"),
                    )
                    break

            except Exception as e:
                # Log error but continue with other scorers
                logger.warning(
                    "Scorer failed",
                    scorer=scorer.__class__.__name__,
                    error=str(e),
                    strategy_id=strategy.get("id"),
                )
                reasoning.append(f"{scorer.__class__.__name__}: ERROR - {str(e)}")
                # Continue without this scorer's contribution

        logger.debug(
            "Arbitration complete",
            strategy_id=strategy.get("id"),
            final_score=score,
            num_scorers_applied=len(outputs),
        )

        return score, outputs, reasoning

    def __repr__(self) -> str:
        return (
            f"ArbitrationEngine("
            f"num_scorers={len(self.scorers)}, "
            f"veto_threshold={self._veto_threshold})"
        )
