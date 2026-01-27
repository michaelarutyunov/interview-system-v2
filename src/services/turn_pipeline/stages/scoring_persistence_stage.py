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
        # Build scoring dict from tier2 results
        scoring = await self._extract_legacy_scores(context.selection_result)

        await self._save_scoring(
            session_id=context.session_id,
            turn_number=context.turn_number,
            strategy=context.strategy,
            scoring=scoring,
            selection_result=context.selection_result,
        )

        # Save LLM qualitative signals if available
        await self._save_qualitative_signals(context)

        context.scoring = scoring

        # Update session turn count
        await self._update_turn_count(context, scoring)

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
        reasoning_trace_last = None
        if (
            selection_result is not None
            and hasattr(selection_result, "scoring_result")
            and selection_result.scoring_result
        ):
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
            # Extract last reasoning entry
            if selection_result.scoring_result.reasoning_trace:
                reasoning_trace_last = selection_result.scoring_result.reasoning_trace[
                    -1
                ]

        async with aiosqlite.connect(str(self.session_repo.db_path)) as db:
            # Save winner to scoring_history (legacy)
            await db.execute(
                """INSERT INTO scoring_history (
                    id, session_id, turn_number,
                    coverage_score, depth_score, saturation_score,
                    novelty_score, richness_score,
                    strategy_selected, strategy_reasoning, scorer_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scoring_id,
                    session_id,
                    turn_number,
                    scoring.get("coverage", 0.0),
                    scoring.get("depth", 0.0),
                    scoring.get("saturation", 0.0),
                    scoring.get("novelty"),
                    scoring.get("richness"),
                    strategy,
                    reasoning_trace_last,
                    json.dumps(scorer_details),
                ),
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
                if hasattr(selection_result, "alternative_strategies"):
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

    async def _save_qualitative_signals(self, context: "PipelineContext") -> None:
        """Save LLM-extracted qualitative signals from graph_state.

        Extracts signals from graph_state.extended_properties["qualitative_signals"]
        and persists them to the qualitative_signals table.
        """
        if not context.graph_state:
            return

        signals_data = context.graph_state.extended_properties.get(
            "qualitative_signals"
        )
        if not signals_data:
            return

        # Extract signal metadata
        llm_model = signals_data.get("llm_model", "unknown")
        extraction_latency_ms = signals_data.get("extraction_latency_ms", 0)
        extraction_errors = signals_data.get("extraction_errors", [])

        # Extract individual signals
        signals = {}
        for signal_type in [
            "uncertainty",
            "reasoning",
            "emotional",
            "contradiction",
            "knowledge_ceiling",
            "concept_depth",
        ]:
            signal = signals_data.get(signal_type)
            if signal:
                # Handle both dict and model representations
                if hasattr(signal, "model_dump"):
                    signals[signal_type] = signal.model_dump()
                elif isinstance(signal, dict):
                    signals[signal_type] = signal
                else:
                    signals[signal_type] = {"data": signal}

        if signals:  # Only save if we have at least one signal
            signal_id = str(uuid.uuid4())
            try:
                await self.session_repo.save_qualitative_signals(
                    signal_id=signal_id,
                    session_id=context.session_id,
                    turn_number=context.turn_number,
                    signals=signals,
                    llm_model=llm_model,
                    extraction_latency_ms=extraction_latency_ms,
                    extraction_errors=extraction_errors,
                )
                log.debug(
                    "qualitative_signals_saved",
                    session_id=context.session_id,
                    turn_number=context.turn_number,
                    signal_types=list(signals.keys()),
                )
            except Exception as e:
                log.warning(
                    "failed_to_save_qualitative_signals",
                    session_id=context.session_id,
                    turn_number=context.turn_number,
                    error=str(e),
                    error_type=type(e).__name__,
                )

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
        reasoning = (
            " | ".join(scoring_result.reasoning_trace)
            if scoring_result and scoring_result.reasoning_trace
            else None
        )

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
            ),
        )

    async def _update_turn_count(self, context: "PipelineContext", scoring: dict):
        """Update session turn count.

        Note: context.turn_number already represents the current turn number
        (equal to the number of user turns completed so far). We store it
        directly without incrementing.
        """
        from src.domain.models.session import SessionState

        updated_state = SessionState(
            methodology=context.methodology,
            concept_id=context.concept_id,
            concept_name=context.concept_name,
            turn_count=context.turn_number,
            coverage_score=scoring.get("coverage", 0.0),
        )
        await self.session_repo.update_state(context.session_id, updated_state)

    async def _extract_legacy_scores(self, selection_result) -> dict:
        """Extract legacy scoring metrics from tier2 results."""
        coverage_score = 0.0
        depth_score = 0.0
        saturation_score = 0.0
        novelty_score = None
        richness_score = None

        if (
            selection_result is not None
            and hasattr(selection_result, "scoring_result")
            and selection_result.scoring_result
        ):
            for result in selection_result.scoring_result.tier2_outputs:
                scorer_id = result.scorer_id
                signals = result.signals

                if scorer_id == "DepthBreadthBalanceScorer":
                    coverage_score = signals.get("breadth_pct", 0.0)
                    depth_avg = signals.get("depth_avg", 0.0)
                    depth_score = min(1.0, depth_avg / 5.0) if depth_avg else 0.0

                elif scorer_id == "NoveltyScorer":
                    novelty_score = result.raw_score

                elif scorer_id == "EngagementScorer":
                    momentum = signals.get("avg_momentum", 50)
                    richness_score = min(1.0, momentum / 150.0)

                elif scorer_id == "SaturationScorer":
                    saturation_score = result.raw_score

        return {
            "coverage": coverage_score,
            "depth": depth_score,
            "saturation": saturation_score,
            "novelty": novelty_score,
            "richness": richness_score,
        }
