"""
Session orchestration service.

ADR-008 Phase 3: Uses TurnPipeline for composable turn processing.

This service provides the main entry point for interview turn processing,
delegating to a pipeline of stages for actual processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from uuid import uuid4

import structlog

from src.core.config import interview_config
from src.core.concept_loader import load_concept
from src.domain.models.extraction import ExtractionResult
from src.domain.models.knowledge_graph import GraphState, KGNode
from src.domain.models.utterance import Utterance
from src.domain.models.turn import Focus
from src.services.extraction_service import ExtractionService
from src.services.graph_service import GraphService
from src.services.question_service import QuestionService

if TYPE_CHECKING:
    pass  # DEPRECATED: Only for type hints
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.persistence.repositories.utterance_repo import UtteranceRepository
from src.services.turn_pipeline import (
    TurnPipeline,
    PipelineContext,
    TurnResult as PipelineTurnResult,
)
from src.services.turn_pipeline.stages import (
    ContextLoadingStage,
    UtteranceSavingStage,
    ExtractionStage,
    GraphUpdateStage,
    StateComputationStage,
    StrategySelectionStage,
    ContinuationStage,
    QuestionGenerationStage,
    ResponseSavingStage,
    ScoringPersistenceStage,
)

log = structlog.get_logger(__name__)


# Re-export TurnResult for backward compatibility
TurnResult = PipelineTurnResult


@dataclass
class SessionContext:
    """
    Context for current session state.

    Loaded at turn start, used throughout pipeline.
    """

    session_id: str
    methodology: str
    concept_id: str
    concept_name: str
    turn_number: int
    mode: str  # Interview mode (exploratory)
    max_turns: int = 20
    recent_utterances: List[Dict[str, str]] = field(default_factory=list)
    graph_state: Optional[GraphState] = None
    recent_nodes: List[KGNode] = field(default_factory=list)


class SessionService:
    """
    Orchestrates interview session turn processing.

    ADR-008 Phase 3: Uses TurnPipeline for composable turn processing.
    Main entry point for processing user input and generating responses.
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        graph_repo: GraphRepository,
        extraction_service: Optional[ExtractionService] = None,
        graph_service: Optional[GraphService] = None,
        question_service: Optional[QuestionService] = None,
        utterance_repo: Optional[UtteranceRepository] = None,
        max_turns: Optional[int] = None,
    ):
        """
        Initialize session service with pipeline.

        Args:
            session_repo: Session repository
            graph_repo: Graph repository
            extraction_service: Extraction service (creates default if None)
            graph_service: Graph service (creates default if None)
            question_service: Question service (creates default if None)
            utterance_repo: Utterance repository (creates default if None)
            max_turns: Maximum turns before forcing close (defaults to interview_config.yaml)
        """
        self.session_repo = session_repo
        self.graph_repo = graph_repo

        # Create services with graph_repo where needed
        self.extraction = extraction_service or ExtractionService()
        self.graph = graph_service or GraphService(graph_repo)

        # Question service needs methodology for opening question generation
        # We'll create it with a default and update it when we have a session
        if question_service:
            self.question = question_service
        else:
            # Create with default methodology, will be updated per session
            self.question = QuestionService(methodology="means_end_chain")

        # Create utterance repo if not provided
        if utterance_repo is None:
            utterance_repo = UtteranceRepository(str(session_repo.db_path))
        self.utterance_repo = utterance_repo

        # Load from centralized interview config (Phase 4: ADR-008)
        self.max_turns = (
            max_turns if max_turns is not None else interview_config.session.max_turns
        )

        # Build pipeline with all stages
        self.pipeline = self._build_pipeline()

        log.info(
            "session_service_initialized",
            max_turns=self.max_turns,
            pipeline_stages=len(self.pipeline.stages),
        )

    def _build_pipeline(self) -> TurnPipeline:
        """
        Build the turn processing pipeline with all stages.

        Returns:
            TurnPipeline configured with all stages
        """
        stages = [
            ContextLoadingStage(
                session_repo=self.session_repo,
                graph_service=self.graph,
            ),
            UtteranceSavingStage(),
            ExtractionStage(
                extraction_service=self.extraction,
            ),
            GraphUpdateStage(
                graph_service=self.graph,
            ),
            StateComputationStage(
                graph_service=self.graph,
            ),
            StrategySelectionStage(),
            ContinuationStage(
                question_service=self.question,
            ),
            QuestionGenerationStage(
                question_service=self.question,
            ),
            ResponseSavingStage(),
            ScoringPersistenceStage(
                session_repo=self.session_repo,
            ),
        ]

        return TurnPipeline(stages=stages)

    async def process_turn(
        self,
        session_id: str,
        user_input: str,
    ) -> TurnResult:
        """
        Process a single interview turn using the pipeline.

        ADR-008 Phase 3: Delegates to TurnPipeline with composable stages.

        Pipeline stages:
        1. ContextLoadingStage - Load session metadata and graph state
        2. UtteranceSavingStage - Save user utterance
        3. ExtractionStage - Extract concepts/relationships
        4. GraphUpdateStage - Update knowledge graph
        5. StateComputationStage - Refresh graph state
        6. StrategySelectionStage - Select questioning strategy
        7. ContinuationStage - Determine if should continue
        8. QuestionGenerationStage - Generate follow-up question
        9. ResponseSavingStage - Save system utterance
        10. ScoringPersistenceStage - Save scoring and update turn count

        Args:
            session_id: Session ID
            user_input: User's response text

        Returns:
            TurnResult with extraction, graph state, next question

        Raises:
            ValueError: If session not found
        """
        log.info("processing_turn", session_id=session_id, input_length=len(user_input))

        # Create initial context
        context = PipelineContext(
            session_id=session_id,
            user_input=user_input,
        )

        # Execute pipeline
        result = await self.pipeline.execute(context)

        log.info(
            "turn_processed",
            session_id=session_id,
            turn_number=result.turn_number,
            strategy=result.strategy_selected,
            should_continue=result.should_continue,
            latency_ms=result.latency_ms,
        )

        return result

    async def _save_scoring(
        self,
        session_id: str,
        turn_number: int,
        strategy: str,
        scoring: Dict[str, Any],
        selection_result: Any = None,
    ):
        """Save scoring data to scoring_history table and all candidates to scoring_candidates."""
        import uuid

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

        # Save winner to scoring_history (legacy)
        await self.session_repo.save_scoring_history(
            scoring_id=scoring_id,
            session_id=session_id,
            turn_number=turn_number,
            depth_score=scoring.get("depth", 0.0),
            saturation_score=scoring.get("saturation", 0.0),
            strategy_selected=strategy,
            strategy_reasoning=selection_result.scoring_result.reasoning_trace[-1]
            if selection_result.scoring_result
            and selection_result.scoring_result.reasoning_trace
            else None,
            scorer_details=scorer_details,
        )

        # Save ALL candidates to scoring_candidates table
        if selection_result:
            # Save the winner
            await self._save_candidate(
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
                    session_id=session_id,
                    turn_number=turn_number,
                    strategy_id=alternative.strategy["id"],
                    strategy_name=alternative.strategy.get("name", ""),
                    focus=alternative.focus,
                    final_score=alternative.score,
                    is_selected=False,
                    scoring_result=alternative.scoring_result,
                )

    async def _save_candidate(
        self,
        session_id: str,
        turn_number: int,
        strategy_id: str,
        strategy_name: str,
        focus: Union[
            "Focus", Dict[str, Any]
        ],  # Accept both typed Focus and dict for compatibility
        final_score: float,
        is_selected: bool,
        scoring_result: Any,
    ):
        """Save a single candidate to the scoring_candidates table."""
        import uuid

        candidate_id = str(uuid.uuid4())

        # Convert Focus to dict if needed
        if isinstance(focus, dict):
            focus_dict: Dict[str, Any] = focus
        elif hasattr(focus, "to_dict"):
            focus_dict: Dict[str, Any] = focus.to_dict()
        elif hasattr(focus, "model_dump"):  # Pydantic v2
            focus_dict: Dict[str, Any] = focus.model_dump()
        else:
            focus_dict: Dict[str, Any] = focus  # type: ignore[assignment]

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

        await self.session_repo.save_scoring_candidate(
            candidate_id=candidate_id,
            session_id=session_id,
            turn_number=turn_number,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            focus_type=focus_dict.get("focus_type", ""),
            focus_description=focus_dict.get("focus_description", "")[
                :500
            ],  # Limit length
            final_score=final_score,
            is_selected=is_selected,
            vetoed_by=scoring_result.vetoed_by if scoring_result else None,
            tier1_results=tier1_results,
            tier2_results=tier2_results,
            reasoning=reasoning,
        )

    async def start_session(
        self,
        session_id: str,
    ) -> str:
        """
        Generate opening question for a session.

        Args:
            session_id: Session ID

        Returns:
            Opening question string
        """
        session = await self.session_repo.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Load concept to get objective and methodology
        concept = load_concept(session.concept_id)

        # Update question service with the correct methodology
        self.question.methodology = concept.methodology

        # Extract objective from concept context
        # Try objective first (new field for exploratory interviews)
        # Fall back to insight for backward compatibility
        # Finally fall back to concept name if neither exists
        if concept.context.objective:
            objective = concept.context.objective
        elif concept.context.insight:
            objective = concept.context.insight
        else:
            objective = concept.name

        question = await self.question.generate_opening_question(
            objective=objective,
        )

        # Save as system utterance (turn 0)
        await self._save_utterance(
            session_id=session_id,
            turn_number=0,
            speaker="system",
            text=question,
        )

        log.info(
            "session_started",
            session_id=session_id,
            concept=concept.name,
            methodology=concept.methodology,
        )

        return question

    async def _load_context(self, session_id: str) -> SessionContext:
        """
        Load session context for turn processing.

        Args:
            session_id: Session ID

        Returns:
            SessionContext with current state
        """
        session = await self.session_repo.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get session config to read max_turns
        config = await self.session_repo.get_config(session_id)
        max_turns = config.get("max_turns", interview_config.session.max_turns)

        # Get recent utterances (use config limit)
        recent_utterances = await self._get_recent_utterances(
            session_id, limit=interview_config.session_service.context_utterance_limit
        )

        # Get graph state
        graph_state = await self.graph.get_graph_state(session_id)

        # Get recent nodes (use config limit)
        recent_nodes = await self.graph.get_recent_nodes(
            session_id, limit=interview_config.session_service.context_node_limit
        )

        return SessionContext(
            session_id=session_id,
            methodology=session.methodology,
            concept_id=session.concept_id,
            concept_name=session.concept_name,
            turn_number=session.state.turn_count or 1,
            mode=session.mode.value,  # NEW: Pass mode from session
            max_turns=max_turns,
            recent_utterances=recent_utterances,
            graph_state=graph_state,
            recent_nodes=recent_nodes,
        )

    async def _save_utterance(
        self,
        session_id: str,
        turn_number: int,
        speaker: str,
        text: str,
    ) -> Utterance:
        """
        Save an utterance to the database.

        Args:
            session_id: Session ID
            turn_number: Turn number
            speaker: "user" or "system"
            text: Utterance text

        Returns:
            Created Utterance
        """
        utterance = Utterance(
            id=str(uuid4()),
            session_id=session_id,
            turn_number=turn_number,
            speaker=speaker,
            text=text,
            discourse_markers=[],
            created_at=datetime.utcnow(),
        )

        return await self.utterance_repo.save(utterance)

    async def _get_recent_utterances(
        self, session_id: str, limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get recent utterances for context.

        Args:
            session_id: Session ID
            limit: Max utterances to return

        Returns:
            List of {"speaker": str, "text": str} dicts
        """
        utterances = await self.utterance_repo.get_recent(session_id, limit=limit)

        return [{"speaker": u.speaker, "text": u.text} for u in utterances]

    def _format_context_for_extraction(self, context: SessionContext) -> str:
        """
        Format context for extraction prompt.

        Args:
            context: Session context

        Returns:
            Context string
        """
        if not context.recent_utterances:
            return ""

        lines = []
        limit = interview_config.session_service.extraction_context_limit
        for utt in context.recent_utterances[-limit:]:
            speaker = "Respondent" if utt["speaker"] == "user" else "Interviewer"
            lines.append(f"{speaker}: {utt['text']}")

        return "\n".join(lines)

    def _select_strategy(
        self,
        graph_state: GraphState,
        turn_number: int,
        extraction: ExtractionResult,
    ) -> str:
        """
        Select questioning strategy.

        Phase 2: Always returns "deepen"
        Phase 3: Full scoring-based selection

        Args:
            graph_state: Current graph state
            turn_number: Current turn number
            extraction: Latest extraction result

        Returns:
            Strategy name
        """
        # Phase 2: Hardcoded deepen
        # Phase 3 will implement full scoring/arbitration

        # Simple heuristics for variety
        if turn_number >= self.max_turns - 2:
            return "close"

        # Default to deepen
        return "deepen"

    def _should_continue(
        self,
        turn_number: int,
        max_turns: int,
        graph_state: GraphState,
        strategy: str,
    ) -> bool:
        """
        Determine if interview should continue.

        Args:
            turn_number: Current turn number
            max_turns: Maximum turns for this session
            graph_state: Current graph state
            strategy: Selected strategy

        Returns:
            True if should continue, False if should end
        """
        # Max turns reached
        if turn_number >= max_turns:
            log.info(
                "session_ending",
                reason="max_turns",
                turn_number=turn_number,
                max_turns=max_turns,
            )
            return False

        # Strategy is close
        if strategy == "close":
            log.info("session_ending", reason="close_strategy")
            return False

        # Future: saturation detected, other termination conditions

        return True

    async def get_status(self, session_id: str) -> dict:
        """
        Get session status including current strategy.

        Args:
            session_id: Session ID

        Returns:
            Dict with turn_number, max_turns,
            status, should_continue, strategy_selected, strategy_reasoning, phase
        """
        session = await self.session_repo.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get session config to read max_turns
        config = await self.session_repo.get_config(session_id)
        max_turns = config.get("max_turns", interview_config.session.max_turns)

        # Get the most recent turn to extract strategy from scoring_history
        strategy_data = await self.session_repo.get_latest_strategy(session_id)
        strategy = strategy_data["strategy"]
        reasoning = strategy_data["reasoning"]

        # Calculate phase based on turn count (deterministic from config)
        turn_count = session.state.turn_count or 0
        exploratory_end = interview_config.phases.exploratory.n_turns or 10
        focused_end = exploratory_end + (interview_config.phases.focused.n_turns or 10)
        if turn_count < exploratory_end:
            phase = "exploratory"
        elif turn_count < focused_end:
            phase = "focused"
        else:
            phase = "closing"

        return {
            "turn_number": turn_count,
            "max_turns": max_turns,
            "status": session.status,
            "should_continue": session.status == "active",
            "strategy_selected": strategy,
            "strategy_reasoning": reasoning,
            "phase": phase,
        }

    async def get_turn_scoring(self, session_id: str, turn_number: int) -> dict:
        """
        Get all scoring candidates for a specific turn.

        Args:
            session_id: Session ID
            turn_number: Turn number

        Returns:
            Dict with session_id, turn_number, candidates list, and winner_strategy_id
        """
        import json

        rows = await self.session_repo.get_turn_scoring(session_id, turn_number)

        if not rows:
            return {
                "session_id": session_id,
                "turn_number": turn_number,
                "candidates": [],
                "winner_strategy_id": None,
            }

        candidates = []
        winner_strategy_id = None

        for row in rows:
            candidate = {
                "id": row["id"],
                "strategy_id": row["strategy_id"],
                "strategy_name": row["strategy_name"],
                "focus_type": row["focus_type"],
                "focus_description": row["focus_description"],
                "final_score": row["final_score"],
                "is_selected": bool(row["is_selected"]),
                "vetoed_by": row["vetoed_by"],
                "tier1_results": json.loads(row["tier1_results"])
                if row["tier1_results"]
                else [],
                "tier2_results": json.loads(row["tier2_results"])
                if row["tier2_results"]
                else [],
                "reasoning": row["reasoning"],
            }
            candidates.append(candidate)

            if candidate["is_selected"]:
                winner_strategy_id = candidate["strategy_id"]

        return {
            "session_id": session_id,
            "turn_number": turn_number,
            "candidates": candidates,
            "winner_strategy_id": winner_strategy_id,
        }

    async def get_all_scoring(self, session_id: str) -> list:
        """
        Get all scoring data for all turns in a session.

        Args:
            session_id: Session ID

        Returns:
            List of turn scoring dicts
        """
        turn_numbers = await self.session_repo.get_all_turn_numbers_with_scoring(
            session_id
        )

        results = []
        for turn_num in turn_numbers:
            turn_data = await self.get_turn_scoring(session_id, turn_num)
            results.append(turn_data)

        return results
