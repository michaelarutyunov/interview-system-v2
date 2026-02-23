"""
Tests for FocusSelectionService.

Verifies the resolution order:
1. focus_node_id -> node label
2. focus_description -> use directly
3. focus_mode-based selection
"""

import pytest
from unittest.mock import MagicMock

from src.services.focus_selection_service import FocusSelectionService
from src.domain.models.knowledge_graph import KGNode


@pytest.fixture
def focus_service():
    """Create FocusSelectionService instance."""
    return FocusSelectionService()


@pytest.fixture
def mock_nodes():
    """Create mock KGNode instances."""
    node1 = MagicMock(spec=KGNode)
    node1.id = "node-123"
    node1.label = "oat milk"

    node2 = MagicMock(spec=KGNode)
    node2.id = "node-456"
    node2.label = "almond milk"

    node3 = MagicMock(spec=KGNode)
    node3.id = "node-789"
    node3.label = "dairy alternatives"

    return [node1, node2, node3]


class TestFocusResolutionOrder:
    """Test that resolution follows documented order: node_id -> description -> focus_mode."""

    def test_resolves_from_node_id_first(self, focus_service, mock_nodes):
        """focus_node_id should take priority over focus_description."""
        focus_dict = {
            "focus_node_id": "node-123",
            "focus_description": "some other focus",
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="any_strategy",
        )

        assert result == "oat milk"

    def test_resolves_from_description_when_node_id_not_found(self, focus_service, mock_nodes):
        """Falls back to focus_description when node_id doesn't match any node."""
        focus_dict = {
            "focus_node_id": "nonexistent-node",
            "focus_description": "custom focus topic",
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="any_strategy",
        )

        assert result == "custom focus topic"

    def test_resolves_from_description_when_no_node_id(self, focus_service, mock_nodes):
        """Uses focus_description when focus_node_id is not provided."""
        focus_dict = {
            "focus_description": "the user's feelings about dairy",
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="any_strategy",
        )

        assert result == "the user's feelings about dairy"

    def test_falls_back_to_focus_mode(self, focus_service, mock_nodes):
        """Falls back to focus_mode-based selection when no focus_dict."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="any_strategy",
            focus_mode="recent_node",
        )

        assert result == "oat milk"

    def test_falls_back_when_empty_focus_dict(self, focus_service, mock_nodes):
        """Falls back to focus_mode-based selection when focus_dict is empty."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict={},
            recent_nodes=mock_nodes,
            strategy="any_strategy",
        )

        assert result == "oat milk"


class TestFocusModeSelection:
    """Test focus_mode-driven focus selection (replaces strategy name matching)."""

    def test_recent_node_focus_mode(self, focus_service, mock_nodes):
        """focus_mode=recent_node returns most recent node."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="any_strategy_name",
            focus_mode="recent_node",
        )
        assert result == "oat milk"

    def test_summary_focus_mode(self, focus_service, mock_nodes):
        """focus_mode=summary returns 'what we've discussed'."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="any_strategy_name",
            focus_mode="summary",
        )
        assert result == "what we've discussed"

    def test_topic_focus_mode(self, focus_service, mock_nodes):
        """focus_mode=topic returns 'the topic'."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="any_strategy_name",
            focus_mode="topic",
        )
        assert result == "the topic"

    def test_default_focus_mode_is_recent_node(self, focus_service, mock_nodes):
        """Omitting focus_mode defaults to recent_node behavior."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="totally_new_strategy",
        )
        assert result == "oat milk"

    def test_novel_strategy_name_works_without_code_change(self, focus_service, mock_nodes):
        """A strategy name that has never existed in code should still work."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="triadic_elicitation",
            focus_mode="recent_node",
        )
        assert result == "oat milk"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_recent_nodes_returns_generic_topic(self, focus_service):
        """Returns 'the topic' when no recent nodes are available."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=[],
            strategy="any_strategy",
        )

        assert result == "the topic"

    def test_empty_focus_description_falls_through(self, focus_service, mock_nodes):
        """Empty string focus_description should fall through to focus_mode."""
        focus_dict = {
            "focus_description": "",
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="any_strategy",
        )

        assert result == "oat milk"

    def test_node_id_string_matching(self, focus_service, mock_nodes):
        """Node ID matching should work with string conversion."""
        focus_dict = {
            "focus_node_id": "node-456",
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="any_strategy",
        )

        assert result == "almond milk"
