"""Tests for export service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.export_service import ExportService
from src.domain.models.knowledge_graph import KGNode


class TestExportService:
    """Tests for ExportService."""

    @pytest.mark.asyncio
    async def test_export_json_format(self):
        """Export to JSON produces valid JSON."""
        # Mock repositories
        session_repo = AsyncMock()
        graph_repo = AsyncMock()

        # Setup mock session
        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.concept_id = "test_concept"
        mock_session.methodology = "means_end_chain"
        mock_session.status = "completed"
        mock_session.created_at = MagicMock()
        mock_session.created_at.isoformat.return_value = "2025-01-21T00:00:00"
        mock_session.completed_at = None
        mock_session.config = {}

        session_repo.get.return_value = mock_session
        session_repo.get_utterances.return_value = []
        session_repo.get_scoring_history.return_value = []

        # Setup mock graph
        graph_repo.get_nodes_by_session.return_value = [
            KGNode(
                id="n1",
                session_id="test-session",
                label="creamy texture",
                node_type="attribute",
                confidence=0.9,
                properties={},
                source_utterance_ids=["u1"],
            )
        ]
        graph_repo.get_edges_by_session.return_value = []

        service = ExportService(session_repo, graph_repo)
        result = await service.export_session("test-session", "json")

        assert result is not None
        # Verify valid JSON
        import json

        data = json.loads(result)
        assert data["metadata"]["session_id"] == "test-session"
        assert len(data["graph"]["nodes"]) == 1

    @pytest.mark.asyncio
    async def test_export_markdown_format(self):
        """Export to Markdown produces readable output."""
        session_repo = AsyncMock()
        graph_repo = AsyncMock()

        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.concept_id = "oat_milk_v1"
        mock_session.methodology = "means_end_chain"
        mock_session.status = "active"
        mock_session.created_at = MagicMock()
        mock_session.created_at.isoformat.return_value = "2025-01-21T00:00:00"
        mock_session.completed_at = None
        mock_session.config = {}

        session_repo.get.return_value = mock_session
        session_repo.get_utterances.return_value = [
            MagicMock(
                id="u1",
                turn_number=1,
                speaker="interviewer",
                text="What comes to mind?",
                created_at=None,
            )
        ]
        session_repo.get_scoring_history.return_value = []

        graph_repo.get_nodes_by_session.return_value = []
        graph_repo.get_edges_by_session.return_value = []

        service = ExportService(session_repo, graph_repo)
        result = await service.export_session("test-session", "markdown")

        assert "# Interview Session Export" in result
        assert "test-session" in result
        assert "What comes to mind?" in result

    @pytest.mark.asyncio
    async def test_export_csv_format(self):
        """Export to CSV produces structured sections."""
        session_repo = AsyncMock()
        graph_repo = AsyncMock()

        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.concept_id = "test_concept"
        mock_session.methodology = "means_end_chain"
        mock_session.status = "active"
        mock_session.created_at = MagicMock()
        mock_session.created_at.isoformat.return_value = "2025-01-21T00:00:00"
        mock_session.completed_at = None
        mock_session.config = {}

        session_repo.get.return_value = mock_session
        session_repo.get_utterances.return_value = []
        session_repo.get_scoring_history.return_value = []

        node = KGNode(
            id="n1",
            session_id="test-session",
            label="test",
            node_type="attribute",
            confidence=0.8,
            properties={},
            source_utterance_ids=[],
        )
        graph_repo.get_nodes_by_session.return_value = [node]
        graph_repo.get_edges_by_session.return_value = []

        service = ExportService(session_repo, graph_repo)
        result = await service.export_session("test-session", "csv")

        assert "## NODES" in result
        assert "test" in result
        assert "attribute" in result

    @pytest.mark.asyncio
    async def test_unsupported_format_raises(self):
        """Unsupported format raises ValueError."""
        service = ExportService()

        with pytest.raises(ValueError, match="Unsupported export format"):
            await service.export_session("test-session", "xml")
