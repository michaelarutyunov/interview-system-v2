"""
Tests for FocusSelectionService.

Verifies the resolution order:
1. focus_node_id -> node label
2. focus_description -> use directly
3. strategy-based heuristic selection
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
    """Test that resolution follows documented order: node_id -> description -> heuristic."""

    def test_resolves_from_node_id_first(self, focus_service, mock_nodes):
        """focus_node_id should take priority over focus_description."""
        focus_dict = {
            "focus_node_id": "node-123",
            "focus_description": "some other focus",  # Should be ignored
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="deepen",
        )

        assert result == "oat milk"  # From node, not description

    def test_resolves_from_description_when_node_id_not_found(
        self, focus_service, mock_nodes
    ):
        """Falls back to focus_description when node_id doesn't match any node."""
        focus_dict = {
            "focus_node_id": "nonexistent-node",
            "focus_description": "custom focus topic",
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="deepen",
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
            strategy="broaden",
        )

        assert result == "the user's feelings about dairy"

    def test_falls_back_to_strategy_heuristic(self, focus_service, mock_nodes):
        """Falls back to strategy-based selection when no focus_dict."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="deepen",
        )

        # deepen uses most recent node
        assert result == "oat milk"

    def test_falls_back_to_strategy_when_empty_focus_dict(
        self, focus_service, mock_nodes
    ):
        """Falls back to strategy-based selection when focus_dict is empty."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict={},
            recent_nodes=mock_nodes,
            strategy="deepen",
        )

        assert result == "oat milk"


class TestStrategyBasedSelection:
    """Test strategy-based heuristic selection."""

    def test_deepen_strategy_uses_most_recent_node(self, focus_service, mock_nodes):
        """deepen strategy should focus on the most recent (first) node."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="deepen",
        )

        assert result == "oat milk"  # First node

    def test_broaden_strategy_uses_most_recent_node(self, focus_service, mock_nodes):
        """broaden strategy should also use the most recent node."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="broaden",
        )

        assert result == "oat milk"

    def test_cover_strategy_uses_most_recent_node(self, focus_service, mock_nodes):
        """cover strategy should use the most recent node (placeholder behavior)."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="cover",
        )

        assert result == "oat milk"

    def test_close_strategy_returns_summary_focus(self, focus_service, mock_nodes):
        """close strategy should return 'what we've discussed'."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="close",
        )

        assert result == "what we've discussed"

    def test_reflect_strategy_uses_most_recent_node(self, focus_service, mock_nodes):
        """reflect strategy should focus on the most recent node."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="reflect",
        )

        assert result == "oat milk"

    def test_unknown_strategy_defaults_to_most_recent(self, focus_service, mock_nodes):
        """Unknown strategies should default to most recent node."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="some_unknown_strategy",
        )

        assert result == "oat milk"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_recent_nodes_returns_generic_topic(self, focus_service):
        """Returns 'the topic' when no recent nodes are available."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=[],
            strategy="deepen",
        )

        assert result == "the topic"

    def test_empty_focus_description_falls_through(self, focus_service, mock_nodes):
        """Empty string focus_description should fall through to heuristic."""
        focus_dict = {
            "focus_description": "",  # Empty string
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="deepen",
        )

        # Should fall through to heuristic since description is empty
        assert result == "oat milk"

    def test_node_id_string_matching(self, focus_service, mock_nodes):
        """Node ID matching should work with string conversion."""
        # Node IDs might come as integers or strings
        focus_dict = {
            "focus_node_id": "node-456",  # Second node
        }

        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=focus_dict,
            recent_nodes=mock_nodes,
            strategy="deepen",
        )

        assert result == "almond milk"  # Second node

    def test_cover_element_strategy(self, focus_service, mock_nodes):
        """cover_element strategy should behave like cover."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="cover_element",
        )

        assert result == "oat milk"
