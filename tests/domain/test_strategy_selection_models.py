"""Tests for StrategySelectionResult models (ADR-010 Phase 2).

RED Phase: Write failing tests first.
"""

from src.domain.models.pipeline_contracts import (
    Focus,
    VetoResult,
    WeightedResult,
    ScoredStrategy,
    StrategySelectionResult,
)


class TestFocusModel:
    """Tests for Focus model with element_id support."""

    def test_creates_focus_with_all_fields(self):
        """Should create focus with all optional fields."""
        focus = Focus(
            focus_type="element_coverage",
            focus_description="Explore oat milk attributes",
            node_id="node_123",
            element_id=42,  # CRITICAL for cover_element strategy
        )

        assert focus.focus_type == "element_coverage"
        assert focus.element_id == 42

    def test_creates_focus_without_optional_fields(self):
        """Should create focus without optional fields."""
        focus = Focus(
            focus_type="breadth_exploration",
            focus_description="Explore new topics",
        )

        assert focus.node_id is None
        assert focus.element_id is None


class TestVetoResultModel:
    """Tests for VetoResult model (Tier 1 output)."""

    def test_creates_veto_result(self):
        """Should create veto result with all fields."""
        veto = VetoResult(
            scorer_id="KnowledgeCeilingScorer",
            is_veto=True,
            reasoning="User indicated no knowledge",
            signals={"user_response": "I don't know"},
        )

        assert veto.is_veto is True
        assert "KnowledgeCeilingScorer" in veto.scorer_id


class TestWeightedResultModel:
    """Tests for WeightedResult model (Tier 2 output)."""

    def test_creates_weighted_result(self):
        """Should create weighted result with contribution."""
        result = WeightedResult(
            scorer_id="CoverageGapScorer",
            raw_score=1.5,
            weight=0.14,
            contribution=0.21,
            reasoning="Uncovered element detected",
            signals={"coverage_pct": 0.3},
        )

        assert result.contribution == 0.21
        assert result.weight == 0.14


class TestScoredStrategyModel:
    """Tests for ScoredStrategy model."""

    def test_creates_scored_strategy(self):
        """Should create scored strategy with all fields."""
        focus = Focus(
            focus_type="element_coverage",
            focus_description="Explore oat milk",
            element_id=42,
        )

        tier1_results = [
            VetoResult(
                scorer_id="KnowledgeCeilingScorer",
                is_veto=False,
                reasoning="User has knowledge",
                signals={},
            )
        ]

        tier2_results = [
            WeightedResult(
                scorer_id="CoverageGapScorer",
                raw_score=1.5,
                weight=0.14,
                contribution=0.21,
                reasoning="",
                signals={},
            )
        ]

        strategy = ScoredStrategy(
            strategy_id="deepen",
            strategy_name="Deepen Understanding",
            focus=focus,
            tier1_results=tier1_results,
            tier2_results=tier2_results,
            tier2_score=0.50,
            final_score=0.65,  # After phase multiplier
            is_selected=True,
            vetoed_by=None,
            reasoning="High coverage gap in oat milk attributes",
        )

        assert strategy.strategy_id == "deepen"
        assert strategy.focus.element_id == 42
        assert len(strategy.tier1_results) == 1
        assert len(strategy.tier2_results) == 1


class TestStrategySelectionResultModel:
    """Tests for StrategySelectionResult model."""

    def test_creates_selection_result(self):
        """Should create complete selection result."""
        focus = Focus(
            focus_type="element_coverage",
            focus_description="Explore oat milk",
            element_id=42,
        )

        selected = ScoredStrategy(
            strategy_id="deepen",
            strategy_name="Deepen Understanding",
            focus=focus,
            tier1_results=[],
            tier2_results=[],
            tier2_score=0.50,
            final_score=0.65,
            is_selected=True,
            vetoed_by=None,
            reasoning="",
        )

        alternative = ScoredStrategy(
            strategy_id="broaden",
            strategy_name="Broaden Coverage",
            focus=Focus(
                focus_type="breadth_exploration",
                focus_description="Explore new topics",
            ),
            tier1_results=[],
            tier2_results=[],
            tier2_score=0.45,
            final_score=0.54,
            is_selected=False,
            vetoed_by=None,
            reasoning="",
        )

        result = StrategySelectionResult(
            session_id="test-session",
            turn_number=1,
            phase="exploratory",
            phase_multiplier=1.3,
            selected_strategy=selected,
            alternatives=[alternative],
            total_candidates=8,
            vetoed_count=3,
        )

        assert result.session_id == "test-session"
        assert result.phase == "exploratory"
        assert result.phase_multiplier == 1.3
        assert result.total_candidates == 8
        assert result.vetoed_count == 3
        assert len(result.alternatives) == 1
