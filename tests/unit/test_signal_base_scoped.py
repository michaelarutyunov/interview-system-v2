"""Tests for SignalDetector.scoped and get_scoped_signal_names()."""

import pytest

from src.signals.signal_base import SignalDetector


@pytest.fixture
def registry_snapshot():
    """Save, clear, and restore SignalDetector._registry to prevent test pollution."""
    saved = SignalDetector._registry.copy()
    SignalDetector._registry.clear()
    yield
    SignalDetector._registry.clear()
    SignalDetector._registry.update(saved)


@pytest.mark.usefixtures("registry_snapshot")
class TestScopedClassVar:
    """Tests for the scoped ClassVar on SignalDetector."""

    def test_default_scoped_is_false(self):
        """A fresh subclass without explicit scoped inherits False."""

        class UnscopedSignal(SignalDetector):
            signal_name = "test.unscoped"

        assert UnscopedSignal.scoped is False
        assert UnscopedSignal.signal_name in SignalDetector._registry

    def test_explicit_scoped_true(self):
        """A subclass can set scoped=True."""

        class ScopedSignal(SignalDetector):
            signal_name = "test.scoped"
            scoped = True

        assert ScopedSignal.scoped is True


@pytest.mark.usefixtures("registry_snapshot")
class TestGetScopedSignalNames:
    """Tests for get_scoped_signal_names() classmethod."""

    def test_empty_when_no_scoped_registered(self):
        """Returns empty frozenset when no detector has scoped=True."""
        result = SignalDetector.get_scoped_signal_names()
        assert isinstance(result, frozenset)
        assert len(result) == 0

    def test_returns_only_scoped_signals(self):
        """Only signal names from detectors with scoped=True are returned."""

        class UnscopedA(SignalDetector):
            signal_name = "test.unscoped_a"

        class ScopedB(SignalDetector):
            signal_name = "test.scoped_b"
            scoped = True

        class UnscopedC(SignalDetector):
            signal_name = "test.unscoped_c"

        # Verify scoped values on the classes themselves
        assert UnscopedA.scoped is False
        assert ScopedB.scoped is True
        assert UnscopedC.scoped is False

        result = SignalDetector.get_scoped_signal_names()
        assert result == frozenset({"test.scoped_b"})

    def test_scoped_false_not_included(self):
        """Explicit scoped=False is treated the same as default."""

        class ExplicitFalse(SignalDetector):
            signal_name = "test.explicit_false"
            scoped = False

        assert ExplicitFalse.scoped is False
        result = SignalDetector.get_scoped_signal_names()
        assert "test.explicit_false" not in result


class TestScopedIntegration:
    """Integration tests using the real signal registry (no snapshot isolation)."""

    def test_strategy_repetition_count_is_scoped(self):
        """StrategyRepetitionCountSignal is discoverable via get_scoped_signal_names."""
        import src.signals  # noqa: F401 — side-effect import triggers auto-registration

        result = SignalDetector.get_scoped_signal_names()
        assert "interview.strategy.self_count" in result

    def test_turns_since_change_not_scoped(self):
        """TurnsSinceChangeSignal returns a scalar — not in the scoped set."""
        import src.signals  # noqa: F401 — side-effect import triggers auto-registration

        result = SignalDetector.get_scoped_signal_names()
        assert "interview.strategy.turns_since_change" not in result
