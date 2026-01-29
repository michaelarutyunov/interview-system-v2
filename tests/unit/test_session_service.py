"""Tests for session service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.session_service import SessionService, TurnResult
from src.domain.models.extraction import ExtractionResult, ExtractedConcept
from src.domain.models.knowledge_graph import (
    GraphState,
    KGNode,
    DepthMetrics,
    CoverageState,
)
from src.domain.models.concept import Concept, ConceptContext


@pytest.fixture
def mock_session_repo():
    """Create mock session repository."""
    repo = AsyncMock()
    repo.db = AsyncMock()
    repo.db.execute = AsyncMock()
    repo.db.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_graph_repo():
    """Create mock graph repository."""
    return AsyncMock()


@pytest.fixture
def mock_extraction_service():
    """Create mock extraction service."""
    service = AsyncMock()
    service.extract = AsyncMock(
        return_value=ExtractionResult(
            concepts=[
                ExtractedConcept(
                    text="test", node_type="attribute", source_utterance_id="u1"
                )
            ],
            relationships=[],
            is_extractable=True,
        )
    )
    return service


@pytest.fixture
def mock_graph_service():
    """Create mock graph service."""
    service = AsyncMock()
    service.add_extraction_to_graph = AsyncMock(return_value=([], []))
    service.get_graph_state = AsyncMock(
        return_value=GraphState(
            node_count=1,
            edge_count=0,
            nodes_by_type={"attribute": 1},
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0, depth_by_element={}),
            coverage_state=CoverageState(),
        )
    )
    service.get_recent_nodes = AsyncMock(
        return_value=[
            KGNode(id="n1", session_id="s1", label="test", node_type="attribute")
        ]
    )
    return service


@pytest.fixture
def mock_question_service():
    """Create mock question service."""
    service = AsyncMock()
    service.generate_question = AsyncMock(return_value="Why is that important?")
    service.generate_opening_question = AsyncMock(return_value="What do you think?")
    service.select_focus_concept = MagicMock(return_value="test")
    return service


@pytest.fixture
def mock_concept():
    """Create mock concept for testing."""
    return Concept(
        id="test-concept",
        name="Test Concept",
        methodology="means_end_chain",
        context=ConceptContext(
            topic="test topic",
            insight="test insight",
            objective="Understand user perceptions of test product",
        ),
        elements=[],
    )


@pytest.fixture
def service(
    mock_session_repo,
    mock_graph_repo,
    mock_extraction_service,
    mock_graph_service,
    mock_question_service,
):
    """Create session service with mocks."""
    return SessionService(
        session_repo=mock_session_repo,
        graph_repo=mock_graph_repo,
        extraction_service=mock_extraction_service,
        graph_service=mock_graph_service,
        question_service=mock_question_service,
    )


@pytest.fixture
def mock_session():
    """Create mock session object."""
    session = MagicMock()
    session.id = "test-session"
    session.methodology = "means_end_chain"
    session.concept_id = "test-concept"
    session.config = {"concept_name": "Test Product"}
    session.turn_count = 1
    return session


class TestProcessTurn:
    """Tests for process_turn."""

    @pytest.mark.asyncio
    async def test_returns_turn_result(self, service, mock_session_repo, mock_session):
        """process_turn returns TurnResult."""
        mock_session_repo.get = AsyncMock(return_value=mock_session)

        # Mock utterance fetching
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        result = await service.process_turn(
            session_id="test-session",
            user_input="I like the taste",
        )

        assert isinstance(result, TurnResult)
        assert result.turn_number == 1
        assert result.strategy_selected == "deepen"
        assert result.should_continue is True

    @pytest.mark.asyncio
    async def test_calls_extraction(
        self, service, mock_session_repo, mock_session, mock_extraction_service
    ):
        """Calls extraction service with user input."""
        mock_session_repo.get = AsyncMock(return_value=mock_session)
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        await service.process_turn("s1", "I like the taste")

        mock_extraction_service.extract.assert_called_once()
        call_args = mock_extraction_service.extract.call_args
        assert call_args.kwargs["text"] == "I like the taste"

    @pytest.mark.asyncio
    async def test_updates_graph(
        self, service, mock_session_repo, mock_session, mock_graph_service
    ):
        """Updates graph with extraction results."""
        mock_session_repo.get = AsyncMock(return_value=mock_session)
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        await service.process_turn("s1", "I like it")

        mock_graph_service.add_extraction_to_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_generates_question(
        self, service, mock_session_repo, mock_session, mock_question_service
    ):
        """Generates follow-up question."""
        mock_session_repo.get = AsyncMock(return_value=mock_session)
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        result = await service.process_turn("s1", "I like it")

        mock_question_service.generate_question.assert_called_once()
        assert result.next_question == "Why is that important?"

    @pytest.mark.asyncio
    async def test_ends_at_max_turns(self, service, mock_session_repo, mock_session):
        """Ends session at max turns."""
        mock_session.turn_count = 20  # At max
        mock_session_repo.get = AsyncMock(return_value=mock_session)
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        result = await service.process_turn("s1", "I like it")

        assert result.should_continue is False


class TestStartSession:
    """Tests for start_session."""

    @pytest.mark.asyncio
    async def test_generates_opening(
        self, service, mock_session_repo, mock_session, mock_question_service, mock_concept
    ):
        """start_session generates opening question."""
        mock_session_repo.get = AsyncMock(return_value=mock_session)

        with patch("src.services.session_service.load_concept", return_value=mock_concept):
            with patch.object(service, "_save_utterance", new_callable=AsyncMock):
                question = await service.start_session("test-session")

        assert question == "What do you think?"
        mock_question_service.generate_opening_question.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_for_unknown_session(self, service, mock_session_repo):
        """Raises ValueError for unknown session."""
        mock_session_repo.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await service.start_session("unknown")


class TestStrategySelection:
    """Tests for strategy selection."""

    def test_returns_close_near_max_turns(self, service):
        """Returns close strategy near max turns."""
        strategy = service._select_strategy(
            graph_state=GraphState(
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                coverage_state=CoverageState(),
            ),
            turn_number=19,  # Near max of 20
            extraction=ExtractionResult(),
        )

        assert strategy == "close"

    def test_returns_deepen_by_default(self, service):
        """Returns deepen by default (Phase 2)."""
        strategy = service._select_strategy(
            graph_state=GraphState(
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                coverage_state=CoverageState(),
            ),
            turn_number=5,
            extraction=ExtractionResult(),
        )

        assert strategy == "deepen"


class TestShouldContinue:
    """Tests for should_continue."""

    def test_false_at_max_turns(self, service):
        """Returns False at max turns."""
        result = service._should_continue(
            turn_number=20,
            max_turns=20,
            graph_state=GraphState(
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                coverage_state=CoverageState(),
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
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                coverage_state=CoverageState(),
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
                depth_metrics=DepthMetrics(
                    max_depth=0, avg_depth=0.0, depth_by_element={}
                ),
                coverage_state=CoverageState(),
            ),
            strategy="deepen",
        )

        assert result is True
