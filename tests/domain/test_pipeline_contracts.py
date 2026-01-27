"""Tests for pipeline stage contracts (ADR-010 Part 1).

RED Phase: Write failing tests first to prove they test the right thing.
"""

import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    UtteranceSavingOutput,
    StateComputationOutput,
    StrategySelectionInput,
    StrategySelectionOutput,
)
from src.domain.models.knowledge_graph import (
    GraphState,
    CoverageState,
    DepthMetrics,
)


class TestContextLoadingOutput:
    """Tests for ContextLoadingStage output contract."""

    def test_context_loading_output_creation(self):
        """Should create valid context loading output."""
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk v2",
            turn_number=1,
            mode="coverage",
            max_turns=10,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        assert output.methodology == "means_end_chain"
        assert output.concept_id == "oat_milk_v2"
        assert output.turn_number == 1
        assert output.graph_state.node_count == 5


class TestUtteranceSavingOutput:
    """Tests for UtteranceSavingStage output contract."""

    def test_utterance_saving_output_creation(self):
        """Should create valid utterance saving output."""
        output = UtteranceSavingOutput(
            turn_number=1,
            user_utterance_id="utter_123",
        )

        assert output.turn_number == 1
        assert output.user_utterance_id == "utter_123"

    def test_requires_utterance_id(self):
        """Should require user_utterance_id."""
        with pytest.raises(ValidationError):
            UtteranceSavingOutput(
                turn_number=1,
                # Missing user_utterance_id
            )


class TestStateComputationOutput:
    """Tests for StateComputationStage output contract (ADR-010 freshness)."""

    def test_state_computation_output_with_freshness(self):
        """Should create state computation output with timestamp for freshness tracking."""
        graph_state = GraphState(
            node_count=10,
            edge_count=8,
            depth_metrics=DepthMetrics(max_depth=3, avg_depth=1.5),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=2,
        )

        now = datetime.now(timezone.utc)
        output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=[],
            computed_at=now,
        )

        assert output.graph_state.node_count == 10
        assert output.computed_at == now
        # Verify computed_at is recent (within 1 second)
        assert datetime.now(timezone.utc) - output.computed_at < timedelta(seconds=1)

    def test_computed_at_must_be_datetime(self):
        """Should require computed_at to be a datetime."""
        graph_state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
        )

        with pytest.raises(ValidationError):
            StateComputationOutput(
                graph_state=graph_state,
                recent_nodes=[],
                computed_at="not a datetime",  # type: ignore
            )


class TestStrategySelectionInput:
    """Tests for StrategySelectionStage input contract (ADR-010 freshness validation)."""

    def test_strategy_selection_input_with_fresh_state(self):
        """Should accept input with fresh state (computed after extraction)."""
        now = datetime.now(timezone.utc)
        extraction_time = now - timedelta(milliseconds=100)
        state_time = now  # State computed AFTER extraction

        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        # Mock extraction with timestamp
        class MockExtraction:
            timestamp = extraction_time

        input_data = StrategySelectionInput(
            graph_state=graph_state,
            recent_nodes=[],
            extraction=MockExtraction(),  # type: ignore
            conversation_history=[],
            turn_number=1,
            mode="coverage",
            computed_at=state_time,
        )

        assert input_data.graph_state.node_count == 5
        assert input_data.computed_at == state_time

    def test_strategy_selection_input_rejects_stale_state(self):
        """Should REJECT input with stale state (computed before extraction).

        This is the key ADR-010 fix for the stale coverage_state bug.
        """
        now = datetime.now(timezone.utc)
        extraction_time = now
        state_time = now - timedelta(
            seconds=5
        )  # State computed 5 seconds BEFORE extraction

        graph_state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
        )

        # Mock extraction with timestamp
        class MockExtraction:
            timestamp = extraction_time

        with pytest.raises(ValidationError, match="State is stale"):
            StrategySelectionInput(
                graph_state=graph_state,
                recent_nodes=[],
                extraction=MockExtraction(),  # type: ignore
                conversation_history=[],
                turn_number=0,
                mode="coverage",
                computed_at=state_time,
            )

    def test_strategy_selection_input_allows_simultaneous_times(self):
        """Should allow state and extraction at same time (not stale)."""
        now = datetime.now(timezone.utc)

        graph_state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
        )

        # Mock extraction with timestamp
        class MockExtraction:
            timestamp = now

        # Should not raise - same time is acceptable
        input_data = StrategySelectionInput(
            graph_state=graph_state,
            recent_nodes=[],
            extraction=MockExtraction(),  # type: ignore
            conversation_history=[],
            turn_number=0,
            mode="coverage",
            computed_at=now,  # Same time as extraction
        )

        assert input_data.computed_at == now

    def test_strategy_selection_input_requires_all_fields(self):
        """Should require all mandatory fields."""
        graph_state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
        )

        # Missing required fields
        with pytest.raises(ValidationError):
            StrategySelectionInput(
                graph_state=graph_state,
                # Missing extraction, conversation_history, turn_number, mode, computed_at
                recent_nodes=[],
            )


class TestStrategySelectionOutput:
    """Tests for StrategySelectionStage output contract."""

    def test_strategy_selection_output_with_selection(self):
        """Should create valid strategy selection output."""
        output = StrategySelectionOutput(
            strategy="deepen",
            focus={"focus_type": "node", "node_id": "node_123"},
            selected_at=datetime.now(timezone.utc),
        )

        assert output.strategy == "deepen"
        assert output.focus["node_id"] == "node_123"
        assert output.selected_at is not None

    def test_strategy_selection_output_requires_strategy(self):
        """Should require strategy field."""
        with pytest.raises(ValidationError):
            StrategySelectionOutput(
                # Missing strategy
                focus={"focus_type": "node", "node_id": "node_123"},
                selected_at=datetime.now(timezone.utc),
            )
