"""
Stage 10: Persist scoring data and update session state.

ADR-008 Phase 3: Save scoring results and update turn count.
"""
from typing import TYPE_CHECKING

import uuid
import aiosqlite
import json

import structlog

from ..base import TurnStage


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class ScoringPersistenceStage(TurnStage):
    """
    Persist scoring data and update session state.

    Saves to scoring_history and scoring_candidates tables.
    Updates session turn count.
    """

    def __init__(self, session_repo):
        """
        Initialize stage.

        Args:
            session_repo: SessionRepository instance
        """
        self.session_repo = session_repo

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Save scoring data and update session turn count.

        Args:
            context: Turn context with strategy, selection_result, turn_number

        Returns:
            Modified context with scoring populated
        """
        # Build scoring dict
        scoring = {
            "coverage": 0.0,  # Phase 3: computed by CoverageScorer
            "depth": 0.0,  # Phase 3: computed by DepthScorer
            "saturation": 0.0,  # Phase 3: computed by SaturationScorer
        }

        await self._save_scoring(
            session_id=context.session_id,
            turn_number=context.turn_number,
            strategy=context.strategy,
            scoring=scoring,
            selection_result=context.selection_result,
        )

        context.scoring = scoring

        # Update session turn count
        await self._update_turn_count(context)

        log.info(
            "scoring_persisted",
            session_id=context.session_id,
            turn_number=context.turn_number,
            strategy=context.strategy,
        )

        return context

    async def _save_scoring(
        self,
        session_id: str,
        turn_number: int,
        strategy: str,
        scoring: dict,
        selection_result=None,
    ):
        """Save scoring data to scoring_history table and all candidates to scoring_candidates."""
        scoring_id = str(uuid.uuid4())

        # Extract scoring details from two-tier result if available
        scorer_details = {}
        if selection_result and selection_result.scoring_result:
            scorer_details = {
                "tier1_results": [
                    {
                        "scorer_id": t.scorer_id,
                        "is_veto": t.is_veto,
                        "reasoning": t.reasoning,
                        "signals": t.signals,
                    }
                    for t in selection_result.scoring_result.tier1_outputs
                ],
                "tier2_results": [
                    {
                        "scorer_id": t.scorer_id,
                        "raw_score": t.raw_score,
                        "weight": t.weight,
                        "contribution": t.contribution,
                        "reasoning": t.reasoning,
                        "signals": t.signals,
                    }
                    for t in selection_result.scoring_result.tier2_outputs
                ],
                "final_score": selection_result.scoring_result.final_score,
                "vetoed_by": selection_result.scoring_result.vetoed_by,
            }

        async with aiosqlite.connect(str(self.session_repo.db_path)) as db:
            # Save winner to scoring_history (legacy)
            await db.execute(
                """INSERT INTO scoring_history (
                    id, session_id, turn_number,
                    coverage_score, depth_score, saturation_score,
                    strategy_selected, strategy_reasoning, scorer_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scoring_id,
                    session_id,
                    turn_number,
                    scoring.get("coverage", 0.0),
                    scoring.get("depth", 0.0),
                    scoring.get("saturation", 0.0),
                    strategy,
                    selection_result.scoring_result.reasoning_trace[-1] if selection_result.scoring_result and selection_result.scoring_result.reasoning_trace else None,
                    json.dumps(scorer_details),
                )
            )

            # Save ALL candidates to scoring_candidates table
            if selection_result:
                # Save the winner
                await self._save_candidate(
                    db=db,
                    session_id=session_id,
                    turn_number=turn_number,
                    strategy_id=selection_result.selected_strategy["id"],
                    strategy_name=selection_result.selected_strategy.get("name", ""),
                    focus=selection_result.selected_focus,
                    final_score=selection_result.final_score,
                    is_selected=True,
                    scoring_result=selection_result.scoring_result,
                )

                # Save alternatives
                for alternative in selection_result.alternative_strategies:
                    await self._save_candidate(
                        db=db,
                        session_id=session_id,
                        turn_number=turn_number,
                        strategy_id=alternative.strategy["id"],
                        strategy_name=alternative.strategy.get("name", ""),
                        focus=alternative.focus,
                        final_score=alternative.score,
                        is_selected=False,
                        scoring_result=alternative.scoring_result,
                    )

            await db.commit()

    async def _save_candidate(
        self,
        db: aiosqlite.Connection,
        session_id: str,
        turn_number: int,
        strategy_id: str,
        strategy_name: str,
        focus: dict,
        final_score: float,
        is_selected: bool,
        scoring_result,
    ):
        """Save a single candidate to the scoring_candidates table."""
        candidate_id = str(uuid.uuid4())

        # Extract Tier 1 and Tier 2 results
        tier1_results = []
        tier2_results = []

        if scoring_result:
            tier1_results = [
                {
                    "scorer_id": t.scorer_id,
                    "is_veto": t.is_veto,
                    "reasoning": t.reasoning,
                    "signals": t.signals,
                }
                for t in scoring_result.tier1_outputs
            ]
            tier2_results = [
                {
                    "scorer_id": t.scorer_id,
                    "raw_score": t.raw_score,
                    "weight": t.weight,
                    "contribution": t.contribution,
                    "reasoning": t.reasoning,
                    "signals": t.signals,
                }
                for t in scoring_result.tier2_outputs
            ]

        # Build reasoning trace
        reasoning = " | ".join(scoring_result.reasoning_trace) if scoring_result and scoring_result.reasoning_trace else None

        await db.execute(
            """INSERT INTO scoring_candidates (
                id, session_id, turn_number,
                strategy_id, strategy_name, focus_type, focus_description,
                final_score, is_selected, vetoed_by,
                tier1_results, tier2_results, reasoning
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id,
                session_id,
                turn_number,
                strategy_id,
                strategy_name,
                focus.get("focus_type", ""),
                focus.get("focus_description", "")[:500],  # Limit length
                final_score,
                1 if is_selected else 0,
                scoring_result.vetoed_by if scoring_result else None,
                json.dumps(tier1_results),
                json.dumps(tier2_results),
                reasoning,
            )
        )

    async def _update_turn_count(self, context: "PipelineContext"):
        """Update session turn count."""
        from src.domain.models.session import SessionState

        updated_state = SessionState(
            methodology=context.methodology,
            concept_id=context.concept_id,
            concept_name=context.concept_name,
            turn_count=context.turn_number + 1,
            coverage_score=0.0,  # Will be computed on-demand
        )
        await self.session_repo.update_state(context.session_id, updated_state)
