"""Tests for two_tier engine conversion functions (ADR-010 Phase 2)."""

import pytest

from src.services.scoring.two_tier.engine import (
    convert_scoring_result_to_scored_strategy,
    convert_selection_to_strategy_selection_result,
)
from src.services.scoring.two_tier.base import Tier1Output, Tier2Output
from src.services.scoring.two_tier.engine import ScoringResult


class TestConversionFunctions:
    """Tests for conversion functions between dataclass and Pydantic models."""

    @pytest.fixture
    def sample_scoring_result(self):
        """Create a sample ScoringResult for testing."""
        return ScoringResult(
            strategy={"id": "deepen", "name": "Deepen Understanding"},
            focus={
                "focus_type": "element_coverage",
                "focus_description": "Explore oat milk",
                "element_id": 42,
            },
            final_score=0.65,
            tier1_outputs=[
                Tier1Output(
                    scorer_id="KnowledgeCeilingScorer",
                    is_veto=False,
                    reasoning="User has knowledge",
                    signals={},
                )
            ],
            tier2_outputs=[
                Tier2Output(
                    scorer_id="CoverageGapScorer",
                    raw_score=1.5,
                    weight=0.14,
                    contribution=0.21,
                    reasoning="Coverage gap detected",
                    signals={"coverage_pct": 0.3},
                )
            ],
            vetoed_by=None,
            reasoning_trace=["Phase: exploratory", "CoverageGapScorer: raw=1.5"],
            scorer_sum=0.50,
            phase_multiplier=1.3,
        )

    def test_convert_scoring_result_to_scored_strategy(self, sample_scoring_result):
        """Should convert ScoringResult to ScoredStrategy with all fields."""
        result = convert_scoring_result_to_scored_strategy(
            sample_scoring_result, is_selected=True
        )

        # Verify strategy identification
        assert result.strategy_id == "deepen"
        assert result.strategy_name == "Deepen Understanding"
        assert result.is_selected is True

        # Verify focus conversion (especially element_id)
        assert result.focus.focus_type == "element_coverage"
        assert result.focus.element_id == 42

        # Verify Tier 1 results
        assert len(result.tier1_results) == 1
        assert result.tier1_results[0].scorer_id == "KnowledgeCeilingScorer"
        assert result.tier1_results[0].is_veto is False

        # Verify Tier 2 results
        assert len(result.tier2_results) == 1
        assert result.tier2_results[0].scorer_id == "CoverageGapScorer"
        assert result.tier2_results[0].raw_score == 1.5
        assert result.tier2_results[0].weight == 0.14
        assert result.tier2_results[0].contribution == 0.21

        # Verify scores
        assert result.tier2_score == 0.50
        assert result.final_score == 0.65

        # Verify reasoning
        assert "Phase: exploratory" in result.reasoning

    def test_convert_selection_to_strategy_selection_result(
        self, sample_scoring_result
    ):
        """Should convert full selection to StrategySelectionResult."""
        # Create alternative result
        alternative = ScoringResult(
            strategy={"id": "broaden", "name": "Broaden Coverage"},
            focus={
                "focus_type": "breadth_exploration",
                "focus_description": "Explore new topics",
            },
            final_score=0.54,
            tier1_outputs=[],
            tier2_outputs=[],
            vetoed_by=None,
            reasoning_trace=["Phase: exploratory"],
            scorer_sum=0.45,
            phase_multiplier=1.2,
        )

        result = convert_selection_to_strategy_selection_result(
            session_id="test-session",
            turn_number=1,
            phase="exploratory",
            phase_multiplier=1.3,
            selected_result=sample_scoring_result,
            alternative_results=[alternative],
            total_candidates=8,
            vetoed_count=3,
        )

        # Verify session context
        assert result.session_id == "test-session"
        assert result.turn_number == 1
        assert result.phase == "exploratory"
        assert result.phase_multiplier == 1.3

        # Verify selected strategy
        assert result.selected_strategy.strategy_id == "deepen"
        assert result.selected_strategy.is_selected is True

        # Verify alternatives
        assert len(result.alternatives) == 1
        assert result.alternatives[0].strategy_id == "broaden"
        assert result.alternatives[0].is_selected is False

        # Verify aggregate stats
        assert result.total_candidates == 8
        assert result.vetoed_count == 3

    def test_convert_focus_with_element_id(self):
        """Should preserve element_id when converting focus."""
        scoring_result = ScoringResult(
            strategy={"id": "cover_element", "name": "Cover Element"},
            focus={
                "focus_type": "element_coverage",
                "focus_description": "Cover oat milk attributes",
                "element_id": 42,  # CRITICAL for cover_element
            },
            final_score=0.8,
            tier1_outputs=[],
            tier2_outputs=[],
            vetoed_by=None,
            reasoning_trace=[],
        )

        result = convert_scoring_result_to_scored_strategy(scoring_result)

        # Verify element_id is preserved (this was missing in old schema)
        assert result.focus.element_id == 42
        assert result.focus.focus_type == "element_coverage"
