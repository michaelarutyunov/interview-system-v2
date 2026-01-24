"""
Service protocol definitions (interfaces).

Defines formal interfaces for services using Python's typing.Protocol.
Enforces structural subtyping and enables type checking across service boundaries.

Part of ADR-008 Phase 2: Formalize Contracts
"""

from typing import Protocol, List, Optional, Dict, Any

from src.domain.models.extraction import ExtractionResult
from src.domain.models.knowledge_graph import GraphState, KGNode, KGEdge
from src.domain.models.turn import TurnResult
from src.domain.models.interview_state import InterviewMode


class IExtractionService(Protocol):
    """
    Protocol for extraction services.

    Defines interface for extracting concepts and relationships
    from user text.
    """

    async def extract(
        self,
        text: str,
        context: str = "",
        methodology_schema: Optional[dict] = None,
    ) -> ExtractionResult:
        """
        Extract concepts and relationships from text.

        Args:
            text: User input text to analyze
            context: Conversation context for disambiguation
            methodology_schema: Optional methodology configuration

        Returns:
            ExtractionResult with extracted concepts and relationships
        """
        ...


class IGraphService(Protocol):
    """
    Protocol for graph services.

    Defines interface for knowledge graph operations.
    """

    async def add_extraction_to_graph(
        self,
        session_id: str,
        extraction: ExtractionResult,
        utterance_id: str,
    ) -> tuple[List[KGNode], List[KGEdge]]:
        """
        Add extraction results to the knowledge graph.

        Args:
            session_id: Session identifier
            extraction: Extraction result to add
            utterance_id: Source utterance for provenance

        Returns:
            Tuple of (created_nodes, created_edges)
        """
        ...

    async def get_graph_state(self, session_id: str) -> GraphState:
        """
        Get current state of the knowledge graph.

        Args:
            session_id: Session identifier

        Returns:
            GraphState with current metrics
        """
        ...

    async def get_recent_nodes(
        self,
        session_id: str,
        limit: int = 5,
    ) -> List[KGNode]:
        """
        Get recently added nodes.

        Args:
            session_id: Session identifier
            limit: Maximum nodes to return

        Returns:
            List of recently created KGNode objects
        """
        ...


class IQuestionService(Protocol):
    """
    Protocol for question generation services.

    Defines interface for generating interview questions.
    """

    async def generate_question(
        self,
        focus_concept: str,
        recent_utterances: Optional[List[Dict[str, str]]] = None,
        graph_state: Optional[GraphState] = None,
        recent_nodes: Optional[List[KGNode]] = None,
        strategy: Optional[str] = None,
    ) -> str:
        """
        Generate a follow-up question.

        Args:
            focus_concept: Concept to focus the question on
            recent_utterances: Recent conversation turns for context
            graph_state: Current graph state for context
            recent_nodes: Recently added nodes for context
            strategy: Questioning strategy to use

        Returns:
            Generated question string
        """
        ...

    async def generate_opening_question(
        self,
        concept_name: str,
        concept_description: str = "",
    ) -> str:
        """
        Generate an opening question for a new session.

        Args:
            concept_name: Name of the concept/product
            concept_description: Optional description

        Returns:
            Opening question string
        """
        ...

    def select_focus_concept(
        self,
        recent_nodes: List[KGNode],
        graph_state: GraphState,
        strategy: Optional[str] = None,
    ) -> str:
        """
        Select which concept to focus the next question on.

        Args:
            recent_nodes: Recently added nodes
            graph_state: Current graph state
            strategy: Strategy affecting selection

        Returns:
            Concept label to focus on
        """
        ...


class IStrategyService(Protocol):
    """
    Protocol for strategy selection services.

    Defines interface for selecting questioning strategies.
    """

    async def select(
        self,
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        mode: InterviewMode = InterviewMode.COVERAGE_DRIVEN,
    ) -> "SelectionResult":
        """
        Select the best strategy for the current state.

        Args:
            graph_state: Current graph state
            recent_nodes: List of recent nodes from last N turns
            conversation_history: Recent conversation turns
            mode: Interview mode (coverage_driven or graph_driven)

        Returns:
            SelectionResult with selected strategy, focus, and alternatives
        """
        ...


class ISessionService(Protocol):
    """
    Protocol for session orchestration services.

    Defines interface for coordinating the turn processing pipeline.
    """

    async def process_turn(
        self,
        session_id: str,
        user_input: str,
    ) -> TurnResult:
        """
        Process a single interview turn.

        Args:
            session_id: Session identifier
            user_input: User's response text

        Returns:
            TurnResult with extraction, graph state, next question
        """
        ...

    async def start_session(
        self,
        session_id: str,
    ) -> str:
        """
        Generate opening question for a session.

        Args:
            session_id: Session identifier

        Returns:
            Opening question string
        """
        ...

    async def get_status(self, session_id: str) -> dict:
        """
        Get session status including current strategy.

        Args:
            session_id: Session identifier

        Returns:
            Dict with turn_number, max_turns, coverage, status, etc.
        """
        ...

    async def get_turn_scoring(
        self,
        session_id: str,
        turn_number: int,
    ) -> dict:
        """
        Get all scoring candidates for a specific turn.

        Args:
            session_id: Session identifier
            turn_number: Turn number

        Returns:
            Dict with session_id, turn_number, candidates list
        """
        ...


# Import SelectionResult for type annotations
# This is defined here to avoid circular imports
class SelectionResult:
    """Placeholder for strategy_service.SelectionResult."""

    pass
