"""Regression test: scoped signal discovery works without scoring.py edits.

Proves the Architecture #6 contract — a developer adding a new scoped signal
touches ONLY the signal class file, with zero edits to scoring.py.
"""

import pytest
from structlog.testing import capture_logs

from src.signals.signal_base import SignalDetector


@pytest.fixture
def scoped_registry_snapshot():
    """Isolate scoped signal tests from the real registry and LRU cache."""
    from src.methodologies.scoring import _scoped_signal_names

    _scoped_signal_names.cache_clear()
    saved = SignalDetector._registry.copy()
    SignalDetector._registry.clear()
    yield
    SignalDetector._registry.clear()
    SignalDetector._registry.update(saved)
    _scoped_signal_names.cache_clear()


class TestScopedDiscoveryContract:
    """Prove that a new scoped signal works with zero scoring.py edits."""

    @pytest.mark.usefixtures("scoped_registry_snapshot")
    def test_resolve_per_strategy_values(self):
        """Throwaway scoped signal resolves per-strategy dict to scalar."""
        from src.methodologies.scoring import _resolve_strategy_scoped_signals

        class _TestScopedSignal(SignalDetector):
            signal_name = "test.scoped.dummy"
            scoped = True

        assert _TestScopedSignal.scoped is True  # referenced for pyright

        signals = {"test.scoped.dummy": {"strategy_a": 0.7, "strategy_b": 0.2}}

        resolved_a = _resolve_strategy_scoped_signals(signals, "strategy_a")
        assert resolved_a["test.scoped.dummy"] == 0.7

        resolved_b = _resolve_strategy_scoped_signals(signals, "strategy_b")
        assert resolved_b["test.scoped.dummy"] == 0.2

        # Missing strategy -> 0.0, no penalty
        resolved_c = _resolve_strategy_scoped_signals(signals, "strategy_c")
        assert resolved_c["test.scoped.dummy"] == 0.0

    @pytest.mark.usefixtures("scoped_registry_snapshot")
    def test_non_dict_scoped_signal_warns(self):
        """Scoped signal returning a scalar emits a warning."""
        from src.methodologies.scoring import _resolve_strategy_scoped_signals

        class _BadScopedSignal(SignalDetector):
            signal_name = "test.scoped.bad"
            scoped = True

        assert _BadScopedSignal.scoped is True  # referenced for pyright

        signals = {"test.scoped.bad": 3.0}

        with capture_logs() as cap_logs:
            _resolve_strategy_scoped_signals(signals, "strategy_a")

        warnings = [
            entry
            for entry in cap_logs
            if entry.get("event") == "scoped_signal_returned_non_dict"
        ]
        assert len(warnings) == 1
        assert warnings[0]["signal"] == "test.scoped.bad"
        assert warnings[0]["value_type"] == "float"
