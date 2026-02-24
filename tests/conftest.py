"""
Shared test fixtures for critical path tests.

Minimal fixture set for testing core pipeline functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.persistence.database import init_database
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.persistence.repositories.utterance_repo import UtteranceRepository


@pytest.fixture
async def test_db():
    """Create and initialize test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        from src.core import config

        original_path = config.settings.database_path
        config.settings.database_path = db_path

        with patch("src.persistence.database.settings", config.settings):
            yield db_path

        config.settings.database_path = original_path


@pytest.fixture
async def db_connection(test_db):
    """Create a database connection for testing."""
    import aiosqlite

    async with aiosqlite.connect(str(test_db)) as db:
        db.row_factory = aiosqlite.Row
        yield db


@pytest.fixture
async def session_repo(test_db):
    """Create session repository with test database."""
    return SessionRepository(str(test_db))


@pytest.fixture
async def graph_repo(db_connection):
    """Create graph repository with test database connection."""
    return GraphRepository(db_connection)


@pytest.fixture
async def utterance_repo(test_db):
    """Create utterance repository with test database."""
    return UtteranceRepository(str(test_db))


@pytest.fixture
def mock_session():
    """Create mock session object."""
    session = MagicMock()
    session.id = "test-session"
    session.methodology = "means_end_chain"
    session.concept_id = "test-concept"
    session.concept_name = "Test Product"
    session.mode = MagicMock()
    session.mode.value = "exploratory"
    session.config = {"concept_name": "Test Product"}
    session.status = "active"
    session.state = MagicMock()
    session.state.turn_count = 1
    return session


@pytest.fixture
def mock_graph_state():
    """Create mock graph state."""
    from src.domain.models.knowledge_graph import GraphState, DepthMetrics

    return GraphState(
        node_count=1,
        edge_count=0,
        nodes_by_type={"attribute": 1},
        edges_by_type={},
        orphan_count=0,
        depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0, depth_by_element={}),
        current_phase="exploratory",
        turn_count=1,
    )


@pytest.fixture
def mock_extraction_result():
    """Create mock extraction result."""
    from src.domain.models.extraction import ExtractionResult, ExtractedConcept

    return ExtractionResult(
        concepts=[
            ExtractedConcept(
                text="test",
                node_type="attribute",
                source_utterance_id="u1",
                confidence=0.9,
            )
        ],
        relationships=[],
        is_extractable=True,
    )
