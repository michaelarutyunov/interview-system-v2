"""Tests for session service.

Uses real database operations with mocked LLM services.
Tests are integration-style but focused on SessionService behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.services.session_service import SessionService, TurnResult
from src.domain.models.extraction import ExtractionResult, ExtractedConcept
from src.domain.models.knowledge_graph import (
    GraphState,
    DepthMetrics,
)
from src.domain.models.concept import Concept, ConceptContext
from src.domain.models.session import Session, SessionState
from src.domain.models.interview_state import InterviewMode


# ============ FIXTURES ============


@pytest.fixture
def mock_extraction_service():
    """Create mock extraction service."""
    service = AsyncMock()
    service.extract = AsyncMock(
        return_value=ExtractionResult(
            concepts=[
                ExtractedConcept(
                    text="test",
                    node_type="attribute",
                    source_utterance_id="u1",
                    confidence=0.9,
                )
            ],
            relationships=[],
            discourse_markers=[],
            is_extractable=True,
        )
    )
    return service


@pytest.fixture
def mock_question_service():
    """Create mock question service."""
    service = AsyncMock()
    service.generate_question = AsyncMock(return_value="Why is that important?")
    service.generate_opening_question = AsyncMock(
        return_value="What do you think about Test Product?"
    )
    service.select_focus_concept = MagicMock(return_value="test")
    service.methodology = "means_end_chain"
    return service


@pytest.fixture
def mock_concept():
    """Create mock concept for testing."""
    return Concept(
        id="test-concept",
        name="Test Product",
        methodology="means_end_chain",
        context=ConceptContext(
            objective="Understand user perceptions of test product",
        ),
        elements=[],
    )


@pytest.fixture
async def test_session(session_repo, test_db, mock_concept):
    """Create a test session in the database."""
    session = Session(
        id="test-session",
        methodology="means_end_chain",
        concept_id="test-concept",
        concept_name="Test Product",
        mode=InterviewMode.EXPLORATORY,
        status="active",
        state=SessionState(
            methodology="means_end_chain",
            concept_id="test-concept",
            concept_name="Test Product",
            turn_count=1,
            mode=InterviewMode.EXPLORATORY,
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    await session_repo.create(
        session,
        config={"concept_name": "Test Product", "max_turns": 20},
    )

    return session


@pytest.fixture
def service(
    session_repo,
    graph_repo,
    mock_extraction_service,
    mock_question_service,
):
    """Create session service with real repos and mocked LLM services."""
    return SessionService(
        session_repo=session_repo,
        graph_repo=graph_repo,
        extraction_service=mock_extraction_service,
        question_service=mock_question_service,
    )


# ============ PROCESS TURN TESTS ============


class TestProcessTurn:
    """Tests for process_turn."""

    @pytest.mark.asyncio
    async def test_returns_turn_result(
        self, service, test_session, mock_extraction_service, mock_question_service
    ):
        """process_turn returns TurnResult."""
        result = await service.process_turn(
            session_id="test-session",
            user_input="I like the taste",
        )

        assert isinstance(result, TurnResult)
        assert result.turn_number >= 1
        assert result.strategy_selected in ["deepen", "close", "explore"]
        assert result.next_question is not None

    @pytest.mark.asyncio
    async def test_calls_extraction(
        self, service, test_session, mock_extraction_service
    ):
        """Calls extraction service with user input."""
        await service.process_turn("test-session", "I like the taste")

        mock_extraction_service.extract.assert_called_once()
        call_args = mock_extraction_service.extract.call_args
        assert call_args.kwargs["text"] == "I like the taste"

    @pytest.mark.asyncio
    async def test_saves_utterance(self, service, test_session, utterance_repo):
        """Saves user and system utterances to database."""
        await service.process_turn("test-session", "I like it")

        utterances = await utterance_repo.get_recent("test-session", limit=10)
        assert len(utterances) >= 1

        user_utterances = [u for u in utterances if u.speaker == "user"]
        assert len(user_utterances) >= 1
        assert user_utterances[-1].text == "I like it"

    @pytest.mark.asyncio
    async def test_updates_graph(self, service, test_session, graph_repo):
        """Updates graph with extraction results."""
        initial_nodes = await graph_repo.get_nodes_by_session("test-session")

        await service.process_turn("test-session", "I like it")

        final_nodes = await graph_repo.get_nodes_by_session("test-session")
        assert len(final_nodes) >= len(initial_nodes)

    @pytest.mark.asyncio
    async def test_generates_question(
        self, service, test_session, mock_question_service
    ):
        """Generates follow-up question."""
        result = await service.process_turn("test-session", "I like it")

        mock_question_service.generate_question.assert_called_once()
        assert result.next_question == "Why is that important?"

    @pytest.mark.asyncio
    async def test_increments_turn_count(self, service, test_session):
        """Increments turn count after processing."""
        session_before = await service.session_repo.get("test-session")
        turn_before = session_before.state.turn_count

        await service.process_turn("test-session", "I like it")

        session_after = await service.session_repo.get("test-session")
        assert session_after.state.turn_count == turn_before + 1


# ============ START SESSION TESTS ============


class TestStartSession:
    """Tests for start_session."""

    @pytest.mark.asyncio
    async def test_generates_opening(
        self,
        service,
        test_session,
        mock_question_service,
        mock_concept,
    ):
        """start_session generates opening question."""
        with patch(
            "src.services.session_service.load_concept", return_value=mock_concept
        ):
            question = await service.start_session("test-session")

        assert question == "What do you think about Test Product?"
        mock_question_service.generate_opening_question.assert_called_once()

    @pytest.mark.asyncio
    async def test_saves_opening_utterance(
        self, service, test_session, mock_concept, utterance_repo
    ):
        """Saves opening question as system utterance."""
        with patch(
            "src.services.session_service.load_concept", return_value=mock_concept
        ):
            await service.start_session("test-session")

        utterances = await utterance_repo.get_recent("test-session", limit=10)
        system_utterances = [u for u in utterances if u.speaker == "system"]

        assert len(system_utterances) >= 1
        assert "What do you think" in system_utterances[-1].text

    @pytest.mark.asyncio
    async def test_raises_for_unknown_session(self, service):
        """Raises ValueError for unknown session."""
        with pytest.raises(ValueError, match="not found"):
            await service.start_session("unknown-session")


# ============ STRATEGY SELECTION TESTS ============


class TestStrategySelection:
    """Tests for strategy selection (private method)."""

    def test_returns_close_near_max_turns(self, service):
        """Returns close strategy near max turns."""
        strategy = service._select_strategy(
            graph_state=GraphState(
                node_count=1,
                edge_count=0,
                nodes_by_type={},
                edges_by_type={},
                orphan_count=0,
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                current_phase="exploratory",
                turn_count=1,
            ),
            turn_number=19,  # Near max of 20
            extraction=ExtractionResult(),
        )

        assert strategy == "close"

    def test_returns_deepen_by_default(self, service):
        """Returns deepen by default (Phase 2)."""
        strategy = service._select_strategy(
            graph_state=GraphState(
                node_count=1,
                edge_count=0,
                nodes_by_type={},
                edges_by_type={},
                orphan_count=0,
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                current_phase="exploratory",
                turn_count=1,
            ),
            turn_number=5,
            extraction=ExtractionResult(),
        )

        assert strategy == "deepen"


# ============ SHOULD CONTINUE TESTS ============


class TestShouldContinue:
    """Tests for should_continue (private method)."""

    def test_false_at_max_turns(self, service):
        """Returns False at max turns."""
        result = service._should_continue(
            turn_number=20,
            max_turns=20,
            graph_state=GraphState(
                node_count=1,
                edge_count=0,
                nodes_by_type={},
                edges_by_type={},
                orphan_count=0,
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                current_phase="exploratory",
                turn_count=1,
            ),
            strategy="deepen",
        )

        assert result is False

    def test_false_for_close_strategy(self, service):
        """Returns False for close strategy."""
        result = service._should_continue(
            turn_number=5,
            max_turns=20,
            graph_state=GraphState(
                node_count=1,
                edge_count=0,
                nodes_by_type={},
                edges_by_type={},
                orphan_count=0,
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                current_phase="exploratory",
                turn_count=1,
            ),
            strategy="close",
        )

        assert result is False

    def test_true_normally(self, service):
        """Returns True for normal conditions."""
        result = service._should_continue(
            turn_number=5,
            max_turns=20,
            graph_state=GraphState(
                node_count=1,
                edge_count=0,
                nodes_by_type={},
                edges_by_type={},
                orphan_count=0,
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                current_phase="exploratory",
                turn_count=1,
            ),
            strategy="deepen",
        )

        assert result is True


# ============ STATUS TESTS ============


class TestGetStatus:
    """Tests for get_status."""

    @pytest.mark.asyncio
    async def test_returns_session_status(self, service, test_session):
        """Returns session status with strategy and phase."""
        status = await service.get_status("test-session")

        assert "turn_number" in status
        assert "max_turns" in status
        assert "status" in status
        assert "phase" in status
        assert status["status"] == "active"
        assert status["turn_number"] >= 1
