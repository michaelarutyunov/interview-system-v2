"""
Stage 10: Persist scoring data and update session state.

Saves scoring results and updates turn count. Outputs
ScoringPersistenceOutput contract.
"""

from typing import TYPE_CHECKING

import uuid
import aiosqlite

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import ScoringPersistenceOutput
from src.persistence.repositories.session_repo import SessionRepository


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class ScoringPersistenceStage(TurnStage):
    """
    Persist scoring data and update session state.

    Saves to scoring_history table.
    Updates session turn count.
    """

    def __init__(self, session_repo: SessionRepository):
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
            context: Turn context with strategy, signals, graph_state, turn_number

        Returns:
            Modified context with scoring populated
        """
        # Extract scores from graph state
        depth_score = 0.0
        saturation_score = 0.0

        if context.graph_state:
            depth_score = getattr(context.graph_state, "max_depth", 0.0)
            saturation_score = 1.0 - getattr(context.graph_state, "yield_score", 0.0)

        # Save scoring data
        await self._save_scoring(
            session_id=context.session_id,
            turn_number=context.turn_number,
            strategy=context.strategy,
            depth_score=depth_score,
            saturation_score=saturation_score,
        )

        # Save qualitative signals if available
        await self._save_qualitative_signals(context)

        # Save methodology signals if available
        await self._save_methodology_signals(context)

        # Create contract output (single source of truth)
        has_methodology_signals = context.signals is not None

        context.scoring_persistence_output = ScoringPersistenceOutput(
            turn_number=context.turn_number,
            strategy=context.strategy,
            depth_score=depth_score,
            saturation_score=saturation_score,
            has_methodology_signals=has_methodology_signals,
            # timestamp auto-set
        )

        # Update session turn count
        await self._update_turn_count(context)

        log.info(
            "scoring_persisted",
            session_id=context.session_id,
            turn_number=context.turn_number,
            strategy=context.strategy,
            depth_score=depth_score,
            saturation_score=saturation_score,
            has_methodology_signals=has_methodology_signals,
        )

        return context

    async def _save_scoring(
        self,
        session_id: str,
        turn_number: int,
        strategy: str,
        depth_score: float,
        saturation_score: float,
    ):
        """Save scoring data to scoring_history table."""
        scoring_id = str(uuid.uuid4())

        async with aiosqlite.connect(str(self.session_repo.db_path)) as db:
            # Save to scoring_history
            await db.execute(
                """INSERT INTO scoring_history (
                    id, session_id, turn_number,
                    depth_score, saturation_score,
                    novelty_score, richness_score,
                    strategy_selected, strategy_reasoning, scorer_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scoring_id,
                    session_id,
                    turn_number,
                    depth_score,
                    saturation_score,
                    None,  # novelty_score
                    None,  # richness_score
                    strategy,
                    None,  # strategy_reasoning
                    None,  # scorer_details
                ),
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

    async def _save_methodology_signals(self, context: "PipelineContext") -> None:
        """Save methodology-based signals from strategy_selection_output.

        Extracts signals from context.signals (populated by StrategySelectionStage)
        and persists them to the qualitative_signals table for observability.

        This provides traceability for the new signal-based strategy selection.
        """
        if not context.signals:
            return

        # Convert methodology signals to format compatible with qualitative_signals table
        # We're reusing the qualitative_signals table for simplicity
        signal_id = str(uuid.uuid4())
        try:
            # Flatten signals for storage
            # Format: {"graph": {...}, "llm": {...}, "temporal": {...}, "meta": {...}}
            flattened_signals = {}
            for pool_name, pool_signals in context.signals.items():
                if isinstance(pool_signals, dict):
                    flattened_signals[pool_name] = pool_signals
                else:
                    flattened_signals[pool_name] = {"value": pool_signals}

            await self.session_repo.save_qualitative_signals(
                signal_id=signal_id,
                session_id=context.session_id,
                turn_number=context.turn_number,
                signals=flattened_signals,
                llm_model="methodology_signals",
                extraction_latency_ms=0,
                extraction_errors=[],
            )
            log.debug(
                "methodology_signals_saved",
                session_id=context.session_id,
                turn_number=context.turn_number,
                signal_pools=list(context.signals.keys()),
            )
        except Exception as e:
            log.warning(
                "failed_to_save_methodology_signals",
                session_id=context.session_id,
                turn_number=context.turn_number,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _update_turn_count(self, context: "PipelineContext") -> None:
        """Update session turn count, velocity state, and focus history.

        Computes EWMA velocity for surface and canonical graphs.
        Velocity = new nodes discovered this turn.

        Appends a FocusEntry for each turn to track the strategy-node
        decision sequence for post-hoc analysis.

        Note: context.turn_number already represents the current turn number
        (equal to the number of user turns completed so far). We store it
        directly without incrementing.
        """
        from src.domain.models.session import SessionState, FocusEntry

        # EWMA smoothing factor (hardcoded, matches theoretical saturation research)
        alpha = 0.4

        # Load current velocity state from ContextLoadingOutput
        clo = context.context_loading_output

        # Surface graph velocity computation
        current_surface = context.graph_state.node_count
        prev_surface = clo.prev_surface_node_count
        surface_delta = max(current_surface - prev_surface, 0)
        new_surface_ewma = (
            alpha * surface_delta + (1 - alpha) * clo.surface_velocity_ewma
        )
        new_surface_peak = max(clo.surface_velocity_peak, float(surface_delta))

        # Canonical graph velocity computation (may be None if disabled)
        cg_state = context.canonical_graph_state
        if cg_state is not None:
            current_canonical = cg_state.concept_count
            prev_canonical = clo.prev_canonical_node_count
            canonical_delta = max(current_canonical - prev_canonical, 0)
            new_canonical_ewma = (
                alpha * canonical_delta + (1 - alpha) * clo.canonical_velocity_ewma
            )
            new_canonical_peak = max(
                clo.canonical_velocity_peak, float(canonical_delta)
            )
        else:
            # Canonical slots disabled — preserve zeros
            current_canonical = 0
            new_canonical_ewma = 0.0
            new_canonical_peak = 0.0

        # Preserve fields that were previously lost
        last_strategy = context.strategy
        mode = getattr(context, "mode", "exploratory")

        # Build focus entry for this turn
        focus = (
            context.strategy_selection_output.focus
            if context.strategy_selection_output
            else None
        )
        focus_node_id = focus.get("focus_node_id") if focus else None

        # Look up node label from node_tracker if node_id is available
        node_label = ""
        if focus_node_id and context.node_tracker:
            node_state = await context.node_tracker.get_state(focus_node_id)
            if node_state:
                node_label = node_state.label

        entry = FocusEntry(
            turn=context.turn_number,
            node_id=focus_node_id or "",
            label=node_label,
            strategy=context.strategy,
        )

        # Append to existing history loaded at turn start
        updated_history = list(clo.focus_history) + [entry]

        updated_state = SessionState(
            methodology=context.methodology,
            concept_id=context.concept_id,
            concept_name=context.concept_name,
            turn_count=context.turn_number,
            last_strategy=last_strategy,
            mode=mode,
            # Velocity fields
            surface_velocity_ewma=new_surface_ewma,
            surface_velocity_peak=new_surface_peak,
            prev_surface_node_count=current_surface,
            canonical_velocity_ewma=new_canonical_ewma,
            canonical_velocity_peak=new_canonical_peak,
            prev_canonical_node_count=current_canonical,
            # Focus history for tracing strategy-node decisions
            focus_history=updated_history,
        )
        await self.session_repo.update_state(context.session_id, updated_state)
