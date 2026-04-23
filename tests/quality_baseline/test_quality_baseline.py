"""Quality baseline regression tests.

Self-test mode (no LLM cost): verifies comparison function correctness.
Live mode (LLM cost): re-runs simulations and compares against fixtures.

Run self-test:
    uv run pytest tests/quality_baseline/test_quality_baseline.py -v

Run live baseline (LLM cost):
    uv run pytest tests/quality_baseline/test_quality_baseline.py -v -m quality_baseline
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.quality_baseline.comparison import (
    DEFAULT_THRESHOLDS,
    check_thresholds,
    compare_sessions,
    jaccard,
)

FIXTURES_DIR = Path("tests/fixtures/quality_baseline")


def _load_fixtures() -> list[dict]:
    if not FIXTURES_DIR.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(FIXTURES_DIR.glob("*.json"))]


# --- Self-tests: comparison function correctness (no LLM cost) ---


class TestJaccard:
    def test_identical_sets(self):
        assert jaccard({"a", "b", "c"}, {"a", "b", "c"}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        result = jaccard({"a", "b", "c"}, {"b", "c", "d"})
        assert result == pytest.approx(2 / 4)

    def test_empty_both(self):
        assert jaccard(set(), set()) == 1.0

    def test_empty_one(self):
        assert jaccard({"a"}, set()) == 0.0
        assert jaccard(set(), {"a"}) == 0.0


class TestIdentityComparison:
    """Verify that comparing a fixture against itself yields perfect scores."""

    @pytest.fixture(
        params=_load_fixtures(), ids=lambda f: f.get("methodology", "unknown")
    )
    def fixture(self, request) -> dict:
        return request.param

    def test_identity_returns_perfect_scores(self, fixture):
        result = compare_sessions(fixture, fixture)
        assert result.mean_concept_jaccard == 1.0
        assert result.mean_node_type_accuracy == 1.0
        assert result.mean_relationship_jaccard == 1.0
        assert result.strategy_match_rate == 1.0
        assert result.focus_match_rate == 1.0

    def test_identity_passes_thresholds(self, fixture):
        result = compare_sessions(fixture, fixture)
        failures = check_thresholds(result, DEFAULT_THRESHOLDS)
        assert failures == [], f"Identity comparison failed thresholds: {failures}"

    def test_all_turns_present(self, fixture):
        result = compare_sessions(fixture, fixture)
        assert len(result.turns) == fixture["total_turns"]


class TestPartialMatch:
    """Verify comparison function handles partial matches correctly."""

    def _make_session(self, turn: dict) -> dict:
        return {
            "session_id": "test",
            "methodology": "test",
            "concept_id": "test",
            "persona_id": "test",
            "turns": [turn],
        }

    def test_half_concepts_match(self):
        fixture = self._make_session(
            {
                "turn_number": 1,
                "strategy": "ascend",
                "focus_node_label": "price",
                "concepts": [
                    {"label": "price", "node_type": "attribute"},
                    {"label": "quality", "node_type": "attribute"},
                ],
                "relationships": [
                    {
                        "source_label": "price",
                        "target_label": "quality",
                        "edge_type": "leads_to",
                    },
                ],
            }
        )
        new_data = self._make_session(
            {
                "turn_number": 1,
                "strategy": "ascend",
                "focus_node_label": "price",
                "concepts": [
                    {"label": "price", "node_type": "attribute"},
                    {"label": "taste", "node_type": "attribute"},
                ],
                "relationships": [
                    {
                        "source_label": "price",
                        "target_label": "taste",
                        "edge_type": "leads_to",
                    },
                ],
            }
        )
        result = compare_sessions(fixture, new_data)
        assert result.mean_concept_jaccard == pytest.approx(1 / 3)
        assert result.mean_node_type_accuracy == 1.0
        assert result.mean_relationship_jaccard == 0.0
        assert result.strategy_match_rate == 1.0
        assert result.focus_match_rate == 1.0

    def test_no_overlap_fails_gracefully(self):
        fixture = self._make_session(
            {
                "turn_number": 1,
                "strategy": "ascend",
                "focus_node_label": "a",
                "concepts": [{"label": "a", "node_type": "x"}],
                "relationships": [],
            }
        )
        new_data = self._make_session(
            {
                "turn_number": 1,
                "strategy": "ground",
                "focus_node_label": "b",
                "concepts": [{"label": "b", "node_type": "y"}],
                "relationships": [],
            }
        )
        result = compare_sessions(fixture, new_data)
        assert result.mean_concept_jaccard == 0.0
        assert result.mean_node_type_accuracy == 0.0
        assert result.strategy_match_rate == 0.0
        assert result.focus_match_rate == 0.0

    def test_node_type_mismatch_detected(self):
        fixture = self._make_session(
            {
                "turn_number": 1,
                "strategy": "ascend",
                "focus_node_label": "price",
                "concepts": [{"label": "price", "node_type": "attribute"}],
                "relationships": [],
            }
        )
        new_data = self._make_session(
            {
                "turn_number": 1,
                "strategy": "ascend",
                "focus_node_label": "price",
                "concepts": [{"label": "price", "node_type": "functional_consequence"}],
                "relationships": [],
            }
        )
        result = compare_sessions(fixture, new_data)
        assert result.mean_concept_jaccard == 1.0
        assert result.mean_node_type_accuracy == 0.0


# --- Live baseline tests (LLM cost, opt-in) ---


@pytest.mark.quality_baseline
class TestLiveBaseline:
    """Re-run simulations and compare against saved fixtures.

    Requires LLM API access and incurs costs. Run with:
        uv run pytest tests/quality_baseline/test_quality_baseline.py -m quality_baseline -v
    """

    def test_fixtures_exist(self):
        """Verify fixtures have been built."""
        fixtures = list(FIXTURES_DIR.glob("*.json"))
        assert len(fixtures) >= 5, (
            f"Expected >=5 fixtures, found {len(fixtures)}. "
            f"Run: uv run python scripts/eval/build_quality_baseline.py"
        )

    # To add live re-run tests, implement a simulation runner that:
    # 1. Imports SimulationService from src.services
    # 2. Runs simulation with fixture's concept_id + persona_id
    # 3. Extracts per-turn outputs using the same logic as build_quality_baseline.py
    # 4. Compares against the fixture using compare_sessions()
    # 5. Checks thresholds using check_thresholds()
