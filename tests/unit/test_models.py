"""Tests for domain models."""

import pytest

from src.domain.models import (
    KGNode,
    KGEdge,
    GraphState,
    Utterance,
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
)
from src.domain.models.knowledge_graph import DepthMetrics


class TestKGNode:
    """Tests for KGNode model."""

    def test_create_valid_node(self):
        """KGNode can be created with valid data."""
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="creamy texture",
            node_type="attribute",
            confidence=0.9,
            source_utterance_ids=["utt-1"],
        )

        assert node.id == "node-1"
        assert node.label == "creamy texture"
        assert node.node_type == "attribute"
        assert node.confidence == 0.9
        assert node.superseded_by is None

    def test_node_defaults(self):
        """KGNode has sensible defaults."""
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        assert node.confidence == 0.8
        assert node.properties == {}
        assert node.source_utterance_ids == []
        assert node.superseded_by is None

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            KGNode(
                id="n1",
                session_id="s1",
                label="test",
                node_type="attribute",
                confidence=1.5,
            )

        with pytest.raises(ValueError):
            KGNode(
                id="n1",
                session_id="s1",
                label="test",
                node_type="attribute",
                confidence=-0.1,
            )


class TestKGEdge:
    """Tests for KGEdge model."""

    def test_create_valid_edge(self):
        """KGEdge can be created with valid data."""
        edge = KGEdge(
            id="edge-1",
            session_id="session-1",
            source_node_id="node-1",
            target_node_id="node-2",
            edge_type="leads_to",
            confidence=0.85,
        )

        assert edge.source_node_id == "node-1"
        assert edge.target_node_id == "node-2"
        assert edge.edge_type == "leads_to"


class TestUtterance:
    """Tests for Utterance model."""

    def test_create_user_utterance(self):
        """Utterance can be created for user input."""
        utt = Utterance(
            id="utt-1",
            session_id="session-1",
            turn_number=1,
            speaker="user",
            text="I like the creamy texture",
        )

        assert utt.speaker == "user"
        assert utt.turn_number == 1

    def test_create_system_utterance(self):
        """Utterance can be created for system response."""
        utt = Utterance(
            id="utt-2",
            session_id="session-1",
            turn_number=1,
            speaker="system",
            text="Why is that important to you?",
        )

        assert utt.speaker == "system"


class TestExtractionResult:
    """Tests for extraction result models."""

    def test_extraction_with_concepts(self):
        """ExtractionResult can hold concepts and relationships."""
        result = ExtractionResult(
            concepts=[
                ExtractedConcept(
                    text="creamy texture",
                    node_type="attribute",
                    confidence=0.9,
                    source_quote="I love the creamy texture",
                    source_utterance_id="u1",
                ),
                ExtractedConcept(
                    text="satisfying",
                    node_type="functional_consequence",
                    confidence=0.8,
                    source_quote="it's really satisfying",
                    source_utterance_id="u1",
                ),
            ],
            relationships=[
                ExtractedRelationship(
                    source_text="creamy texture",
                    target_text="satisfying",
                    relationship_type="leads_to",
                    confidence=0.75,
                    source_utterance_id="u1",
                ),
            ],
            discourse_markers=["because"],
        )

        assert len(result.concepts) == 2
        assert len(result.relationships) == 1
        assert "because" in result.discourse_markers

    def test_empty_extraction(self):
        """ExtractionResult can be empty for non-extractable input."""
        result = ExtractionResult(
            is_extractable=False,
            extractability_reason="Yes/no response",
        )

        assert result.concepts == []
        assert result.relationships == []
        assert not result.is_extractable


class TestGraphState:
    """Tests for GraphState model."""

    def test_empty_graph_state(self):
        """GraphState defaults to empty."""
        state = GraphState(
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0, depth_by_element={}),
        )

        assert state.node_count == 0
        assert state.edge_count == 0
        assert state.depth_metrics.max_depth == 0

    def test_graph_state_with_data(self):
        """GraphState can hold aggregate data."""
        state = GraphState(
            node_count=5,
            edge_count=3,
            nodes_by_type={"attribute": 2, "functional_consequence": 3},
            orphan_count=1,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.5, depth_by_element={}),
        )

        assert state.node_count == 5
        assert state.nodes_by_type["attribute"] == 2
        assert state.depth_metrics.max_depth == 2

    def test_current_phase_getset(self):
        """Current phase can be set and retrieved directly."""
        state = GraphState(
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0, depth_by_element={}),
        )

        # Default phase is exploratory
        assert state.current_phase == "exploratory"

        # Set to focused
        state.current_phase = "focused"
        assert state.current_phase == "focused"

        # Set to closing
        state.current_phase = "closing"
        assert state.current_phase == "closing"

    def test_add_strategy_used_initializes_history(self):
        """First call to add_strategy_used initializes history list."""
        state = GraphState(
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0, depth_by_element={}),
        )

        state.add_strategy_used("broaden")

        assert state.strategy_history == ["broaden"]

    def test_add_strategy_used_appends_to_history(self):
        """Subsequent calls append to existing history."""
        state = GraphState(
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0, depth_by_element={}),
        )

        state.add_strategy_used("broaden")
        state.add_strategy_used("deepen")
        state.add_strategy_used("broaden")

        assert state.strategy_history == ["broaden", "deepen", "broaden"]

    def test_strategy_history_persists_across_operations(self):
        """Strategy history persists through other state operations."""
        state = GraphState(
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0, depth_by_element={}),
        )

        # Add some strategies
        state.add_strategy_used("broaden")
        state.add_strategy_used("deepen")

        # Change phase (other operation)
        state.current_phase = "focused"

        # History should still be there
        assert state.strategy_history == ["broaden", "deepen"]
