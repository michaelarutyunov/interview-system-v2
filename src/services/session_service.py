"""
Session orchestration service.

Main entry point for interview turn processing, delegating to a pipeline
of composable stages for extraction, graph updates, strategy selection,
and question generation.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, TYPE_CHECKING
from uuid import uuid4

import structlog

from src.core.config import interview_config, settings
from src.services.srl_service import SRLService
from src.services.canonical_slot_service import CanonicalSlotService
from src.services.embedding_service import EmbeddingService
from src.persistence.repositories.canonical_slot_repo import CanonicalSlotRepository
from src.core.concept_loader import load_concept
from src.domain.models.extraction import ExtractionResult
from src.domain.models.knowledge_graph import GraphState, KGNode
from src.domain.models.utterance import Utterance
from src.llm.client import LLMClient
from src.services.extraction_service import ExtractionService
from src.services.focus_selection_service import FocusSelectionService
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
    SRLPreprocessingStage,
    ExtractionStage,
    GraphUpdateStage,
    SlotDiscoveryStage,
    StateComputationStage,
    StrategySelectionStage,
    ContinuationStage,
    QuestionGenerationStage,
    ResponseSavingStage,
    ScoringPersistenceStage,
)

log = structlog.get_logger(__name__)


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
    """Orchestrates interview session turn processing.

    Main entry point for processing user input and generating responses.
    Uses TurnPipeline with composable stages for extraction, graph updates,
    strategy selection, and question generation.
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
        extraction_llm_client: Optional[LLMClient] = None,
        generation_llm_client: Optional[LLMClient] = None,
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
            extraction_llm_client: LLM client for extraction (required if extraction_service not provided)
            generation_llm_client: LLM client for question generation (required if question_service not provided)
        """
        self.session_repo = session_repo
        self.graph_repo = graph_repo

        # Store LLM clients for use in pipeline stages
        self.extraction_llm_client = extraction_llm_client
        self.generation_llm_client = generation_llm_client

        # Store canonical_slot_repo for NodeStateTracker
        # Will be initialized in _build_pipeline() when pipeline is first constructed
        self.canonical_slot_repo: Optional[CanonicalSlotRepository] = None

        # Create services with graph_repo where needed
        if extraction_service:
            self.extraction = extraction_service
        else:
            if extraction_llm_client is None:
                raise ValueError(
                    "extraction_llm_client is required when extraction_service is not provided"
                )
            self.extraction = ExtractionService(llm_client=extraction_llm_client)

        # Note: GraphService is created in _build_pipeline() after canonical_slot_repo is initialized
        # This allows us to pass canonical_slot_repo to GraphService.__init__ (no longer optional)
        self.graph: Optional[GraphService] = (
            graph_service  # Set in _build_pipeline() if None
        )

        # Question service needs methodology for opening question generation
        # We'll create it with a default and update it when we have a session
        if question_service:
            self.question = question_service
        else:
            if generation_llm_client is None:
                raise ValueError(
                    "generation_llm_client is required when question_service is not provided"
                )
            # Create with default methodology, will be updated per session
            self.question = QuestionService(
                llm_client=generation_llm_client, methodology="means_end_chain"
            )

        # Create utterance repo if not provided
        if utterance_repo is None:
            utterance_repo = UtteranceRepository(str(session_repo.db_path))
        self.utterance_repo = utterance_repo

        # Create focus selection service (consolidates focus resolution logic)
        self.focus_selection = FocusSelectionService()

        # Load from centralized interview configuration
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
            TurnPipeline configured with 12 stages for turn processing
        """
        # SRL service: lazy-loads spaCy model on first use, None disables gracefully
        srl_service = SRLService() if settings.enable_srl else None

        # Canonical slot discovery dependencies (conditionally enabled)
        canonical_slot_repo = None
        canonical_slot_service = None
        canonical_graph_service = None

        # EmbeddingService: shared between surface dedup and canonical slots
        # Created unconditionally — surface dedup is independent of canonical slots
        embedding_service = EmbeddingService()  # lazy loads all-MiniLM-L6-v2 + spaCy

        if settings.enable_canonical_slots:
            # Slot discovery uses scoring LLM (KIMI) — cheaper and sufficient
            # for structured JSON extraction. Falls back to generation client.
            from src.llm.client import get_scoring_llm_client

            try:
                slot_llm_client = get_scoring_llm_client()
            except ValueError:
                # KIMI_API_KEY not configured — fall back to generation client
                if self.generation_llm_client is None:
                    raise ValueError(
                        "No LLM client available for SlotDiscoveryStage: "
                        "configure KIMI_API_KEY or provide generation_llm_client"
                    )
                slot_llm_client = self.generation_llm_client

            canonical_slot_repo = CanonicalSlotRepository(
                str(self.session_repo.db_path)
            )
            canonical_slot_service = CanonicalSlotService(
                llm_client=slot_llm_client,
                slot_repo=canonical_slot_repo,
                embedding_service=embedding_service,
            )

            # Store canonical_slot_repo for NodeStateTracker
            self.canonical_slot_repo = canonical_slot_repo

            # Import and initialize CanonicalGraphService
            from src.services.canonical_graph_service import (
                CanonicalGraphService as CGS,
            )

            canonical_graph_service = CGS(canonical_slot_repo=canonical_slot_repo)

            # Create GraphService with canonical_slot_repo and embedding_service
            if self.graph is None:
                self.graph = GraphService(
                    self.graph_repo,
                    canonical_slot_repo=canonical_slot_repo,
                    embedding_service=embedding_service,
                )
        else:
            # Canonical slots disabled: set canonical_slot_repo to None
            self.canonical_slot_repo = None

            # Create GraphService with embedding_service for surface dedup (independent of canonical)
            if self.graph is None:
                self.graph = GraphService(
                    self.graph_repo,
                    canonical_slot_repo=None,
                    embedding_service=embedding_service,
                )

        # Build stage list
        stages = [
            ContextLoadingStage(
                session_repo=self.session_repo,
                graph_service=self.graph,
            ),
            UtteranceSavingStage(),
            SRLPreprocessingStage(srl_service=srl_service),
            ExtractionStage(
                extraction_service=self.extraction,
            ),
            GraphUpdateStage(
                graph_service=self.graph,
            ),
            # Stage 4.5: SlotDiscoveryStage (always wired, skips if service is None)
            # Maps surface nodes to canonical slots via LLM proposal + embedding similarity
            # Also aggregates surface edges to canonical edges
            SlotDiscoveryStage(
                slot_service=canonical_slot_service, graph_service=self.graph
            ),
        ]

        # StateComputationStage: Refresh graph state and compute canonical graph state
        stages.append(
            StateComputationStage(
                graph_service=self.graph,
                canonical_graph_service=canonical_graph_service,  # None if disabled
            )
        )

        stages.extend(
            [
                StrategySelectionStage(),
                ContinuationStage(
                    focus_selection_service=self.focus_selection,
                ),
                QuestionGenerationStage(
                    question_service=self.question,
                ),
                ResponseSavingStage(),
                ScoringPersistenceStage(
                    session_repo=self.session_repo,
                ),
            ]
        )

        return TurnPipeline(stages=stages)

    async def process_turn(
        self,
        session_id: str,
        user_input: str,
    ) -> PipelineTurnResult:
        """Process a single interview turn using the pipeline.

        Delegates to TurnPipeline which executes 12 stages sequentially:
        1. ContextLoadingStage - Load session metadata and graph state
        2. UtteranceSavingStage - Save user utterance
        3. SRLPreprocessingStage - Preprocess user input for SRL extraction
        4. ExtractionStage - Extract concepts/relationships
        5. GraphUpdateStage - Update knowledge graph
        6. SlotDiscoveryStage - Discover canonical slots (if enabled)
        7. StateComputationStage - Refresh graph state and saturation metrics
        8. StrategySelectionStage - Select questioning strategy
        9. ContinuationStage - Determine if should continue
        10. QuestionGenerationStage - Generate follow-up question
        11. ResponseSavingStage - Save system utterance
        12. ScoringPersistenceStage - Save scoring and update turn count

        Args:
            session_id: Session ID
            user_input: User's response text

        Returns:
            TurnResult with extraction, graph state, next question, and continuation status

        Raises:
            ValueError: If session not found
        """
        log.info("processing_turn", session_id=session_id, input_length=len(user_input))

        # Load or create NodeStateTracker for this turn
        # If persisted state exists, load it; otherwise create fresh tracker
        node_tracker = await self._get_or_create_node_tracker(session_id)

        # Create initial context with node_tracker
        context = PipelineContext(
            session_id=session_id,
            user_input=user_input,
            node_tracker=node_tracker,
        )

        # Execute pipeline
        result = await self.pipeline.execute(context)

        # Persist node_tracker state after turn completes
        # This ensures previous_focus and all_response_depths are saved for next turn
        await self._save_node_tracker(session_id, node_tracker)

        log.info(
            "turn_processed",
            session_id=session_id,
            turn_number=result.turn_number,
            strategy=result.strategy_selected,
            should_continue=result.should_continue,
            latency_ms=result.latency_ms,
        )

        return result

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
        objective = concept.context.objective or concept.name

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

        # GraphService is always set after __init__ completes (_build_pipeline creates it)
        assert self.graph is not None, "GraphService not initialized"

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

        Simple heuristic strategy selection. The actual strategy selection
        is handled by StrategySelectionStage in the pipeline.

        Args:
            graph_state: Current graph state
            turn_number: Current turn number
            extraction: Latest extraction result

        Returns:
            Strategy name
        """

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
            "focus_tracing": [entry.model_dump() for entry in session.state.focus_history],
        }

    # ==================== NODE TRACKER STATE PERSISTENCE ====================

    async def _get_or_create_node_tracker(self, session_id: str):
        """
        Load existing node tracker state or create new tracker.

        Args:
            session_id: Session ID to load tracker state for

        Returns:
            NodeStateTracker with restored state or fresh tracker
        """
        from src.services.node_state_tracker import NodeStateTracker

        # Try to load persisted state
        tracker_state_json = await self.session_repo.get_node_tracker_state(session_id)

        if tracker_state_json:
            try:
                # Deserialize from JSON
                state_data = json.loads(tracker_state_json)
                tracker = NodeStateTracker.from_dict(state_data)
                log.debug(
                    "node_tracker_loaded",
                    session_id=session_id,
                    nodes_count=len(tracker.states),
                    previous_focus=tracker.previous_focus,
                )
                return tracker
            except (json.JSONDecodeError, ValueError) as e:
                log.warning(
                    "node_tracker_load_failed_creating_fresh",
                    session_id=session_id,
                    error=str(e),
                )
                # Fall through to create fresh tracker

        # No persisted state or load failed - create fresh tracker
        log.debug(
            "node_tracker_created_fresh",
            session_id=session_id,
            reason="no_persisted_state_or_load_failed",
        )
        # Create fresh tracker with canonical_slot_repo for node aggregation across paraphrases
        return NodeStateTracker(canonical_slot_repo=self.canonical_slot_repo)

    async def _save_node_tracker(self, session_id: str, node_tracker) -> None:
        """
        Persist node tracker state to database.

        Args:
            session_id: Session ID to save tracker state for
            node_tracker: NodeStateTracker to persist
        """
        # Skip if tracker is empty (no nodes tracked yet)
        if node_tracker.is_empty():
            log.debug(
                "node_tracker_skip_save",
                session_id=session_id,
                reason="no_states_to_save",
            )
            return

        # Serialize to JSON
        tracker_dict = node_tracker.to_dict()
        tracker_state_json = json.dumps(tracker_dict)

        # Persist to database
        await self.session_repo.update_node_tracker_state(
            session_id, tracker_state_json
        )
        log.debug(
            "node_tracker_saved",
            session_id=session_id,
            nodes_count=len(node_tracker.states),
            previous_focus=node_tracker.previous_focus,
        )
