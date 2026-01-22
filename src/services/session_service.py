"""
Session orchestration service.

Orchestrates the complete turn processing pipeline:
1. Save user utterance
2. Extract concepts and relationships
3. Update knowledge graph
4. Compute graph state
5. Select strategy (Phase 2: hardcoded "deepen")
6. Generate follow-up question
7. Save system utterance
8. Return TurnResult

This is the main entry point for interview turn processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

import structlog

from src.domain.models.extraction import ExtractionResult
from src.domain.models.knowledge_graph import GraphState, KGNode
from src.domain.models.utterance import Utterance
from src.services.extraction_service import ExtractionService
from src.services.graph_service import GraphService
from src.services.question_service import QuestionService
from src.services.strategy_service import StrategyService, SelectionResult
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.persistence.database import get_db_connection

log = structlog.get_logger(__name__)


@dataclass
class TurnResult:
    """
    Result of processing a single turn.

    Matches PRD Section 8.6 response structure.
    """
    turn_number: int
    extracted: Dict[str, Any]  # concepts, relationships
    graph_state: Dict[str, Any]  # node_count, edge_count, depth_achieved
    scoring: Dict[str, Any]  # strategy_id, score, reasoning (Phase 3)
    strategy_selected: str
    next_question: str
    should_continue: bool
    latency_ms: int = 0


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
    recent_utterances: List[Dict[str, str]] = field(default_factory=list)
    graph_state: Optional[GraphState] = None
    recent_nodes: List[KGNode] = field(default_factory=list)


class SessionService:
    """
    Orchestrates interview session turn processing.

    Main entry point for processing user input and generating responses.
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        graph_repo: GraphRepository,
        extraction_service: Optional[ExtractionService] = None,
        graph_service: Optional[GraphService] = None,
        question_service: Optional[QuestionService] = None,
        strategy_service: Optional[StrategyService] = None,
        max_turns: int = 20,
        target_coverage: float = 0.8,
    ):
        """
        Initialize session service.

        Args:
            session_repo: Session repository
            graph_repo: Graph repository
            extraction_service: Extraction service (creates default if None)
            graph_service: Graph service (creates default if None)
            question_service: Question service (creates default if None)
            strategy_service: Strategy service (creates default if None)
            max_turns: Maximum turns before forcing close
            target_coverage: Coverage target (Phase 3)
        """
        self.session_repo = session_repo
        self.graph_repo = graph_repo

        # Create services with graph_repo where needed
        self.extraction = extraction_service or ExtractionService()
        self.graph = graph_service or GraphService(graph_repo)
        self.question = question_service or QuestionService()
        self.strategy = strategy_service

        self.max_turns = max_turns
        self.target_coverage = target_coverage

        log.info("session_service_initialized", max_turns=max_turns)

    async def process_turn(
        self,
        session_id: str,
        user_input: str,
    ) -> TurnResult:
        """
        Process a single interview turn.

        Pipeline:
        1. Load session context
        2. Save user utterance
        3. Extract concepts/relationships
        4. Update knowledge graph
        5. Compute graph state
        6. Select strategy (Phase 2: hardcoded)
        7. Generate follow-up question
        8. Save system utterance
        9. Return TurnResult

        Args:
            session_id: Session ID
            user_input: User's response text

        Returns:
            TurnResult with extraction, graph state, next question

        Raises:
            ValueError: If session not found
        """
        import time
        start_time = time.perf_counter()

        log.info("processing_turn", session_id=session_id, input_length=len(user_input))

        # Step 1: Load session context
        context = await self._load_context(session_id)

        # Step 2: Save user utterance
        user_utterance = await self._save_utterance(
            session_id=session_id,
            turn_number=context.turn_number,
            speaker="user",
            text=user_input,
        )

        # Step 3: Extract concepts/relationships
        extraction = await self.extraction.extract(
            text=user_input,
            context=self._format_context_for_extraction(context),
        )

        # Step 4: Update knowledge graph
        nodes, edges = await self.graph.add_extraction_to_graph(
            session_id=session_id,
            extraction=extraction,
            utterance_id=user_utterance.id,
        )

        # Step 5: Compute graph state
        graph_state = await self.graph.get_graph_state(session_id)
        recent_nodes = await self.graph.get_recent_nodes(session_id, limit=5)

        # Step 6: Select strategy using two-tier adaptive scoring
        # Fall back to Phase 2 hardcoded behavior if strategy_service not available
        if self.strategy:
            selection = await self.strategy.select(
                graph_state=graph_state,
                recent_nodes=[n.dict() for n in recent_nodes],
                conversation_history=context.recent_utterances,  # Pass conversation history for Tier 1 scorers
            )
            strategy = selection.selected_strategy["id"]
            focus = selection.selected_focus
        else:
            # Phase 2: fallback to hardcoded selection
            strategy = self._select_strategy(
                graph_state=graph_state,
                turn_number=context.turn_number,
                extraction=extraction,
            )
            selection = None
            focus = None

        # Step 7: Determine if we should continue
        should_continue = self._should_continue(
            turn_number=context.turn_number,
            graph_state=graph_state,
            strategy=strategy,
        )

        # Step 8: Generate follow-up question
        if should_continue:
            # Determine focus concept from selection or use heuristic
            if selection and focus:
                # Use focus from strategy service selection
                if "node_id" in focus and recent_nodes:
                    # Find the node in recent_nodes
                    focus_concept = next(
                        (n.label for n in recent_nodes if str(n.id) == focus["node_id"]),
                        # Fallback to description if node not found
                        focus.get("focus_description", "the topic")
                    )
                else:
                    # Use focus description as fallback
                    focus_concept = focus.get("focus_description", "the topic")
            else:
                # Phase 2: fall back to heuristic selection
                focus_concept = self.question.select_focus_concept(
                    recent_nodes=recent_nodes,
                    graph_state=graph_state,
                    strategy=strategy,
                )

            # Add current utterance to recent for context
            updated_utterances = context.recent_utterances + [
                {"speaker": "user", "text": user_input}
            ]

            next_question = await self.question.generate_question(
                focus_concept=focus_concept,
                recent_utterances=updated_utterances,
                graph_state=graph_state,
                recent_nodes=recent_nodes,
                strategy=strategy,
            )
        else:
            next_question = "Thank you for sharing your thoughts with me today. This has been very helpful."

        # Step 9: Save system utterance
        await self._save_utterance(
            session_id=session_id,
            turn_number=context.turn_number,
            speaker="system",
            text=next_question,
        )

        # Step 10: Update session turn count
        from src.domain.models.session import SessionState
        updated_state = SessionState(
            methodology=context.methodology,
            concept_id=context.concept_id,
            concept_name=context.concept_name,
            turn_count=context.turn_number + 1,
            coverage_score=0.0,  # Will be computed on-demand
        )
        await self.session_repo.update_state(session_id, updated_state)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        log.info(
            "turn_processed",
            session_id=session_id,
            turn_number=context.turn_number,
            concepts_extracted=len(extraction.concepts),
            strategy=strategy,
            should_continue=should_continue,
            latency_ms=latency_ms,
        )

        return TurnResult(
            turn_number=context.turn_number,
            extracted={
                "concepts": [
                    {
                        "text": c.text,
                        "type": c.node_type,
                        "confidence": c.confidence,
                    }
                    for c in extraction.concepts
                ],
                "relationships": [
                    {
                        "source": r.source_text,
                        "target": r.target_text,
                        "type": r.relationship_type,
                    }
                    for r in extraction.relationships
                ],
            },
            graph_state={
                "node_count": graph_state.node_count,
                "edge_count": graph_state.edge_count,
                "depth_achieved": graph_state.nodes_by_type,
            },
            scoring={
                "coverage": 0.0,  # Phase 3: computed by CoverageScorer
                "depth": 0.0,  # Phase 3: computed by DepthScorer
                "saturation": 0.0,  # Phase 3: computed by SaturationScorer
            },
            strategy_selected=strategy,
            next_question=next_question,
            should_continue=should_continue,
            latency_ms=latency_ms,
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

        # Get concept name from session
        concept_name = session.concept_name
        concept_description = ""  # Not stored in Session model

        question = await self.question.generate_opening_question(
            concept_name=concept_name,
            concept_description=concept_description,
        )

        # Save as system utterance (turn 0)
        await self._save_utterance(
            session_id=session_id,
            turn_number=0,
            speaker="system",
            text=question,
        )

        log.info("session_started", session_id=session_id, concept=concept_name)

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

        # Get recent utterances
        recent_utterances = await self._get_recent_utterances(session_id, limit=10)

        # Get graph state
        graph_state = await self.graph.get_graph_state(session_id)

        # Get recent nodes
        recent_nodes = await self.graph.get_recent_nodes(session_id, limit=5)

        return SessionContext(
            session_id=session_id,
            methodology=session.methodology,
            concept_id=session.concept_id,
            concept_name=session.concept_name,
            turn_number=session.state.turn_count or 1,
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
        utterance_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        # Use database connection directly
        db = await get_db_connection()
        try:
            await db.execute(
                """
                INSERT INTO utterances (id, session_id, turn_number, speaker, text, discourse_markers, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (utterance_id, session_id, turn_number, speaker, text, "[]", now),
            )
            await db.commit()
        finally:
            await db.close()

        return Utterance(
            id=utterance_id,
            session_id=session_id,
            turn_number=turn_number,
            speaker=speaker,
            text=text,
        )

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
        db = await get_db_connection()
        try:
            cursor = await db.execute(
                """
                SELECT speaker, text FROM utterances
                WHERE session_id = ?
                ORDER BY turn_number DESC, created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = await cursor.fetchall()
        finally:
            await db.close()

        # Reverse to get chronological order
        return [{"speaker": row[0], "text": row[1]} for row in reversed(rows)]

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
        for utt in context.recent_utterances[-5:]:
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
        graph_state: GraphState,
        strategy: str,
    ) -> bool:
        """
        Determine if interview should continue.

        Args:
            turn_number: Current turn number
            graph_state: Current graph state
            strategy: Selected strategy

        Returns:
            True if should continue, False if should end
        """
        # Max turns reached
        if turn_number >= self.max_turns:
            log.info("session_ending", reason="max_turns")
            return False

        # Strategy is close
        if strategy == "close":
            log.info("session_ending", reason="close_strategy")
            return False

        # Phase 3 will add: coverage target reached, saturation detected

        return True
