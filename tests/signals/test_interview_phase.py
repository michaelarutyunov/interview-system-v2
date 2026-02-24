"""Tests for InterviewPhaseSignal._normalize_boundaries().

Covers all three key formats the normalizer must handle:
1. Phase-name keys (current registry output): {"early": 5, "mid": 17}
2. Legacy turn-based keys: {"early_max_turns": 4, "mid_max_turns": 12}
3. Legacy node-based keys: {"early_max_nodes": 4, "mid_max_nodes": 12}
"""

import pytest

from src.signals.meta.interview_phase import InterviewPhaseSignal


@pytest.fixture
def signal():
    return InterviewPhaseSignal()


class TestNormalizeBoundaries:
    """Test _normalize_boundaries with various input formats."""

    def test_new_flat_format(self, signal):
        """Phase-name keys from current registry output."""
        result = signal._normalize_boundaries({"early": 5, "mid": 17, "late": 999})
        assert result == {"early_max_turns": 5, "mid_max_turns": 17}

    def test_old_turn_based_format(self, signal):
        """Legacy early_max_turns / mid_max_turns keys."""
        result = signal._normalize_boundaries(
            {"early_max_turns": 4, "mid_max_turns": 12}
        )
        assert result == {"early_max_turns": 4, "mid_max_turns": 12}

    def test_old_node_based_format(self, signal):
        """Legacy early_max_nodes / mid_max_nodes keys."""
        result = signal._normalize_boundaries(
            {"early_max_nodes": 3, "mid_max_nodes": 10}
        )
        assert result == {"early_max_turns": 3, "mid_max_turns": 10}

    def test_empty_dict_uses_defaults(self, signal):
        """Empty boundaries fall back to defaults."""
        result = signal._normalize_boundaries({})
        assert result == {"early_max_turns": 4, "mid_max_turns": 12}

    def test_phase_name_takes_precedence_over_legacy(self, signal):
        """If both 'early' and 'early_max_turns' exist, 'early' wins."""
        result = signal._normalize_boundaries(
            {"early": 5, "early_max_turns": 99, "mid": 17, "mid_max_turns": 99}
        )
        assert result == {"early_max_turns": 5, "mid_max_turns": 17}

    def test_turn_based_takes_precedence_over_node_based(self, signal):
        """If both turn-based and node-based exist, turn-based wins."""
        result = signal._normalize_boundaries(
            {"early_max_turns": 4, "early_max_nodes": 99, "mid_max_turns": 12, "mid_max_nodes": 99}
        )
        assert result == {"early_max_turns": 4, "mid_max_turns": 12}
