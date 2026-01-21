"""Tests for ScorerBase and ScorerOutput."""

import pytest
from pydantic import ValidationError


class TestScorerOutput:
    """Test ScorerOutput model."""

    def test_create_valid_output(self):
        """Test creating a valid ScorerOutput."""
        from src.services.scoring.base import ScorerOutput

        output = ScorerOutput(
            scorer_name="TestScorer",
            raw_score=1.5,
            weight=1.0,
            weighted_score=1.5,
            signals={"test": "value"},
            reasoning="Test reasoning"
        )

        assert output.scorer_name == "TestScorer"
        assert output.raw_score == 1.5
        assert output.weight == 1.0
        assert output.weighted_score == 1.5
        assert output.signals == {"test": "value"}
        assert output.reasoning == "Test reasoning"

    def test_raw_score_validation(self):
        """Test that raw_score must be between 0 and 2."""
        from src.services.scoring.base import ScorerOutput

        # Test valid scores
        ScorerOutput(
            scorer_name="Test",
            raw_score=0.0,
            weight=1.0,
            weighted_score=0.0
        )
        ScorerOutput(
            scorer_name="Test",
            raw_score=1.0,
            weight=1.0,
            weighted_score=1.0
        )
        ScorerOutput(
            scorer_name="Test",
            raw_score=2.0,
            weight=1.0,
            weighted_score=2.0
        )

        # Test invalid scores
        with pytest.raises(ValidationError):
            ScorerOutput(
                scorer_name="Test",
                raw_score=-0.1,
                weight=1.0,
                weighted_score=0.0
            )

        with pytest.raises(ValidationError):
            ScorerOutput(
                scorer_name="Test",
                raw_score=2.1,
                weight=1.0,
                weighted_score=2.1
            )

    def test_weight_validation(self):
        """Test that weight must be >= 0.1."""
        from src.services.scoring.base import ScorerOutput

        # Test valid weights
        ScorerOutput(
            scorer_name="Test",
            raw_score=1.0,
            weight=0.1,
            weighted_score=1.0
        )
        ScorerOutput(
            scorer_name="Test",
            raw_score=1.0,
            weight=1.0,
            weighted_score=1.0
        )
        ScorerOutput(
            scorer_name="Test",
            raw_score=1.0,
            weight=5.0,
            weighted_score=1.0
        )

        # Test invalid weight
        with pytest.raises(ValidationError):
            ScorerOutput(
                scorer_name="Test",
                raw_score=1.0,
                weight=0.05,
                weighted_score=1.0
            )


class TestScorerBase:
    """Test ScorerBase abstract class."""

    def test_init_with_defaults(self):
        """Test ScorerBase initialization with default values."""
        from src.services.scoring.base import ScorerBase

        class ConcreteScorer(ScorerBase):
            async def score(self, strategy, focus, graph_state, recent_nodes):
                return self.make_output(1.0, {}, "test")

        scorer = ConcreteScorer()

        assert scorer.enabled is True
        assert scorer.weight == 1.0
        assert scorer.veto_threshold == 0.1
        assert scorer.params == {}

    def test_init_with_config(self):
        """Test ScorerBase initialization with custom config."""
        from src.services.scoring.base import ScorerBase

        class ConcreteScorer(ScorerBase):
            async def score(self, strategy, focus, graph_state, recent_nodes):
                return self.make_output(1.0, {}, "test")

        config = {
            "enabled": False,
            "weight": 2.0,
            "veto_threshold": 0.2,
            "params": {"threshold": 0.5}
        }

        scorer = ConcreteScorer(config)

        assert scorer.enabled is False
        assert scorer.weight == 2.0
        assert scorer.veto_threshold == 0.2
        assert scorer.params == {"threshold": 0.5}

    def test_make_output_clamps_high_score(self):
        """Test that make_output clamps scores > 2.0 to 2.0."""
        from src.services.scoring.base import ScorerBase

        class ConcreteScorer(ScorerBase):
            async def score(self, strategy, focus, graph_state, recent_nodes):
                return self.make_output(1.0, {}, "test")

        scorer = ConcreteScorer()
        output = scorer.make_output(3.5, {"test": "value"}, "High score")

        assert output.raw_score == 2.0
        assert output.weighted_score == 2.0 ** scorer.weight
        assert output.signals == {"test": "value"}
        assert output.reasoning == "High score"

    def test_make_output_clamps_low_score(self):
        """Test that make_output clamps scores < 0.0 to 0.0."""
        from src.services.scoring.base import ScorerBase

        class ConcreteScorer(ScorerBase):
            async def score(self, strategy, focus, graph_state, recent_nodes):
                return self.make_output(1.0, {}, "test")

        scorer = ConcreteScorer()
        output = scorer.make_output(-0.5, {"test": "value"}, "Low score")

        assert output.raw_score == 0.0
        assert output.weighted_score == 0.0 ** scorer.weight
        assert output.signals == {"test": "value"}
        assert output.reasoning == "Low score"

    def test_make_output_applies_weight(self):
        """Test that make_output correctly applies weight to calculate weighted_score."""
        from src.services.scoring.base import ScorerBase

        class ConcreteScorer(ScorerBase):
            async def score(self, strategy, focus, graph_state, recent_nodes):
                return self.make_output(1.0, {}, "test")

        scorer = ConcreteScorer({"weight": 2.0})
        output = scorer.make_output(1.5, {}, "Test")

        assert output.raw_score == 1.5
        assert output.weight == 2.0
        assert output.weighted_score == 1.5 ** 2.0  # 2.25

    def test_repr(self):
        """Test ScorerBase __repr__ method."""
        from src.services.scoring.base import ScorerBase

        class ConcreteScorer(ScorerBase):
            async def score(self, strategy, focus, graph_state, recent_nodes):
                return self.make_output(1.0, {}, "test")

        scorer = ConcreteScorer({"weight": 1.5, "veto_threshold": 0.2})
        repr_str = repr(scorer)

        assert "ConcreteScorer" in repr_str
        assert "enabled=True" in repr_str
        assert "weight=1.5" in repr_str
        assert "veto_threshold=0.2" in repr_str
