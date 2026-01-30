"""Tests for pipeline stage contracts (ADR-010 Part 1)."""

import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    UtteranceSavingOutput,
    StateComputationOutput,
    StrategySelectionInput,
    StrategySelectionOutput,
    ExtractionOutput,
    GraphUpdateOutput,
    QuestionGenerationOutput,
    ResponseSavingOutput,
    ContinuationOutput,
    ScoringPersistenceOutput,
)
from src.domain.models.knowledge_graph import (
    GraphState,
    DepthMetrics,
    KGNode,
)
from src.domain.models.utterance import Utterance
from src.domain.models.extraction import (
    ExtractionResult,
    ExtractedConcept,
    ExtractedRelationship,
)


class TestContextLoadingOutput:
    """Tests for ContextLoadingStage output contract."""

    def test_context_loading_output_creation(self):
        """Should create valid context loading output."""
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
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
        utterance = Utterance(
            id="utter_123",
            session_id="session_456",
            turn_number=1,
            speaker="user",
            text="I think oat milk is creamy.",
        )
        output = UtteranceSavingOutput(
            turn_number=1,
            user_utterance_id="utter_123",
            user_utterance=utterance,
        )

        assert output.turn_number == 1
        assert output.user_utterance_id == "utter_123"
        assert output.user_utterance.text == "I think oat milk is creamy."

    def test_requires_utterance_id(self):
        """Should require user_utterance_id."""
        utterance = Utterance(
            id="utter_123",
            session_id="session_456",
            turn_number=1,
            speaker="user",
            text="I think oat milk is creamy.",
        )
        with pytest.raises(ValidationError):
            # Use model_construct to test validation without pyright errors
            UtteranceSavingOutput.model_construct(
                turn_number=1,
                user_utterance=utterance,
                # Missing user_utterance_id - will fail validation
            ).model_validate(None)


class TestStateComputationOutput:
    """Tests for StateComputationStage output contract (ADR-010 freshness)."""

    def test_state_computation_output_with_freshness(self):
        """Should create state computation output with timestamp for freshness tracking."""
        graph_state = GraphState(
            node_count=10,
            edge_count=8,
            depth_metrics=DepthMetrics(max_depth=3, avg_depth=1.5),
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
            current_phase="exploratory",
            turn_count=0,
        )

        # Missing required fields - use model_construct to test validation
        with pytest.raises(ValidationError):
            StrategySelectionInput.model_construct(
                graph_state=graph_state,
                recent_nodes=[],
                # Missing extraction, conversation_history, turn_number, mode, computed_at
            ).model_validate(None)


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
        if output.focus is not None:
            assert output.focus["node_id"] == "node_123"
        assert output.selected_at is not None

    def test_strategy_selection_output_requires_strategy(self):
        """Should require strategy field."""
        with pytest.raises(ValidationError):
            StrategySelectionOutput.model_construct(
                # Missing strategy
                focus={"focus_type": "node", "node_id": "node_123"},
                selected_at=datetime.now(timezone.utc),
            ).model_validate(None)


class TestExtractionOutput:
    """Tests for ExtractionStage output contract."""

    def test_extraction_output_creation(self):
        """Should create valid extraction output."""
        extraction = ExtractionResult(
            concepts=[
                ExtractedConcept(
                    text="oat milk is creamy",
                    node_type="attribute",
                    source_utterance_id="utter_123",
                )
            ],
            relationships=[
                ExtractedRelationship(
                    source_text="oat milk",
                    target_text="creamy",
                    relationship_type="has_attribute",
                    source_utterance_id="utter_123",
                )
            ],
        )
        output = ExtractionOutput(
            extraction=extraction,
            methodology="means_end_chain",
        )

        assert output.methodology == "means_end_chain"
        assert output.concept_count == 1
        assert output.relationship_count == 1
        assert output.timestamp is not None

    def test_extraction_output_auto_counts(self):
        """Should auto-calculate counts from extraction result."""
        extraction = ExtractionResult(
            concepts=[
                ExtractedConcept(
                    text=f"concept_{i}",
                    node_type="attribute",
                    source_utterance_id=f"utter_{i}",
                )
                for i in range(3)
            ],
            relationships=[],
        )
        output = ExtractionOutput(
            extraction=extraction,
            methodology="means_end_chain",
            concept_count=0,  # Should be auto-filled
        )

        assert output.concept_count == 3


class TestGraphUpdateOutput:
    """Tests for GraphUpdateStage output contract."""

    def test_graph_update_output_creation(self):
        """Should create valid graph update output."""
        node = KGNode(
            id="node_123",
            session_id="session_456",
            label="oat milk is creamy",
            node_type="attribute",
            source_utterance_ids=["utter_123"],
        )
        output = GraphUpdateOutput(
            nodes_added=[node],
            edges_added=[{"source": "node_123", "target": "node_456"}],
        )

        assert output.node_count == 1
        assert output.edge_count == 1
        assert output.timestamp is not None

    def test_graph_update_output_auto_counts(self):
        """Should auto-calculate counts from lists."""
        nodes = [
            KGNode(
                id=f"node_{i}",
                session_id="session_456",
                label=f"text_{i}",
                node_type="attribute",
                source_utterance_ids=["utter_123"],
            )
            for i in range(3)
        ]
        output = GraphUpdateOutput(
            nodes_added=nodes,
            edges_added=[],
            node_count=0,  # Should be auto-filled
        )

        assert output.node_count == 3


class TestQuestionGenerationOutput:
    """Tests for QuestionGenerationStage output contract."""

    def test_question_generation_output_creation(self):
        """Should create valid question generation output."""
        output = QuestionGenerationOutput(
            question="Can you tell me more about why you think oat milk is creamy?",
            strategy="deepen",
            focus={"node_id": "node_123"},
        )

        assert output.strategy == "deepen"
        assert output.has_llm_fallback is False
        assert output.timestamp is not None

    def test_question_generation_with_llm_fallback(self):
        """Should track LLM fallback usage."""
        output = QuestionGenerationOutput(
            question="What else can you tell me?",
            strategy="broaden",
            has_llm_fallback=True,
        )

        assert output.has_llm_fallback is True


class TestResponseSavingOutput:
    """Tests for ResponseSavingStage output contract."""

    def test_response_saving_output_creation(self):
        """Should create valid response saving output."""
        utterance = Utterance(
            id="utter_456",
            session_id="session_123",
            turn_number=2,
            speaker="system",
            text="Can you tell me more?",
        )
        output = ResponseSavingOutput(
            turn_number=2,
            system_utterance_id="utter_456",
            system_utterance=utterance,
            question_text="Can you tell me more?",
        )

        assert output.turn_number == 2
        assert output.system_utterance_id == "utter_456"
        assert output.question_text == "Can you tell me more?"


class TestContinuationOutput:
    """Tests for ContinuationStage output contract."""

    def test_continuation_output_continue(self):
        """Should create continuation output for continuing."""
        output = ContinuationOutput(
            should_continue=True,
            focus_concept="oat_milk",
            reason="More depth needed on key attributes",
            turns_remaining=5,
        )

        assert output.should_continue is True
        assert output.focus_concept == "oat_milk"
        assert output.turns_remaining == 5

    def test_continuation_output_stop(self):
        """Should create continuation output for stopping."""
        output = ContinuationOutput(
            should_continue=False,
            reason="Saturation reached - all elements covered",
            turns_remaining=0,
        )

        assert output.should_continue is False
        assert output.turns_remaining == 0


class TestScoringPersistenceOutput:
    """Tests for ScoringPersistenceStage output contract."""

    def test_scoring_persistence_output_creation(self):
        """Should create valid scoring persistence output."""
        output = ScoringPersistenceOutput(
            turn_number=3,
            strategy="deepen",
            depth_score=1.5,
            saturation_score=0.9,
            has_methodology_signals=True,
            has_legacy_scoring=False,
        )

        assert output.turn_number == 3
        assert output.strategy == "deepen"
        assert output.depth_score == 1.5
        assert output.has_methodology_signals is True

    def test_scoring_persistence_with_legacy_data(self):
        """Should track legacy scoring for old sessions."""
        output = ScoringPersistenceOutput(
            turn_number=1,
            strategy="broaden",
            depth_score=1.0,
            saturation_score=0.3,
            has_methodology_signals=False,
            has_legacy_scoring=True,
        )

        assert output.has_legacy_scoring is True
        assert output.has_methodology_signals is False
