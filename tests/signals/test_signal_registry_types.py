"""Regression tests for signal registry type system fixes.

Tests verify:
1. Bug Fix #1: BaseLLMSignal imported at module level (not TYPE_CHECKING)
2. Bug Fix #2: All LLM signal classes inherit from BaseLLMSignal
3. Bug Fix #3: Loop logic correctly pairs signal names with detectors
"""

import pytest

from src.signals.llm.decorator import _registered_llm_signals
from src.signals.llm.llm_signal_base import BaseLLMSignal
from src.signals.signal_registry import ComposedSignalDetector


class TestLLMSignalInheritance:
    """Test that all LLM signal classes properly inherit from BaseLLMSignal."""

    def test_all_llm_signals_inherit_from_base(self):
        """Verify all registered LLM signals inherit from BaseLLMSignal.

        Regression test for Bug #2: LLM signal classes were empty (just `pass`)
        without inheriting from BaseLLMSignal. This broke `issubclass()` checks.
        """
        # Get all registered LLM signal classes
        llm_signals = _registered_llm_signals

        # Verify we have LLM signals registered
        assert len(llm_signals) > 0, "No LLM signals registered"

        # Check each one inherits from BaseLLMSignal
        for signal_name, signal_class in llm_signals.items():
            assert issubclass(signal_class, BaseLLMSignal), (
                f"LLM signal '{signal_name}' does not inherit from BaseLLMSignal. "
                f"MRO: {signal_class.__mro__}"
            )

    def test_specific_llm_signals_inherit_correctly(self):
        """Test specific known LLM signals have correct inheritance."""
        expected_signals = [
            "llm.response_depth",
            "llm.certainty",
            "llm.engagement",
            "llm.specificity",
            "llm.valence",
        ]

        for signal_name in expected_signals:
            assert signal_name in _registered_llm_signals, (
                f"Expected LLM signal '{signal_name}' not registered"
            )

            signal_class = _registered_llm_signals[signal_name]
            assert issubclass(signal_class, BaseLLMSignal), (
                f"LLM signal '{signal_name}' should inherit from BaseLLMSignal"
            )


class TestIsLLMSignalMethod:
    """Test the _is_llm_signal() static method works correctly."""

    def test_is_llm_signal_detects_llm_signals(self):
        """Verify _is_llm_signal() returns True for registered LLM signals.

        Regression test for Bug #1: BaseLLMSignal was imported under TYPE_CHECKING,
        causing NameError at runtime when _is_llm_signal() used issubclass().
        """
        # Test with known LLM signals
        llm_signal_names = [
            "llm.response_depth",
            "llm.certainty",
            "llm.engagement",
            "llm.specificity",
            "llm.valence",
        ]

        for signal_name in llm_signal_names:
            result = ComposedSignalDetector._is_llm_signal(signal_name)
            assert result is True, f"Expected _is_llm_signal('{signal_name}') to return True"

    def test_is_llm_signal_rejects_non_llm_signals(self):
        """Verify _is_llm_signal() returns False for non-LLM signals."""
        non_llm_signals = [
            "graph.node_count",
            "graph.orphan_count",
            "temporal.strategy_repetition_count",
            "meta.interview_progress",
            "nonexistent.signal",
        ]

        for signal_name in non_llm_signals:
            result = ComposedSignalDetector._is_llm_signal(signal_name)
            assert result is False, f"Expected _is_llm_signal('{signal_name}') to return False"

    def test_is_llm_signal_no_name_error(self):
        """Verify _is_llm_signal() doesn't raise NameError.

        This is the core regression test for Bug #1. Before the fix,
        BaseLLMSignal was only imported under `if TYPE_CHECKING:`,
        causing NameError at runtime.
        """
        # Should not raise NameError
        try:
            result = ComposedSignalDetector._is_llm_signal("llm.response_depth")
            assert result is True
        except NameError as e:
            pytest.fail(
                f"_is_llm_signal() raised NameError: {e}. "
                "This indicates BaseLLMSignal is not imported at runtime."
            )


class TestSignalRegistryLoopLogic:
    """Test the signal detector loop processes correct signal-detector pairs."""

    def test_detector_signal_name_access(self):
        """Verify signal detectors have accessible signal_name attribute.

        Regression test for Bug #3: Loop used zip(detectors, detectors) instead
        of iterating and accessing detector.signal_name.
        """
        from src.signals.signal_base import SignalDetector

        # Get a sample signal detector
        signal_names = ["graph.node_count"]
        detector_class = SignalDetector.get_signal_class(signal_names[0])

        assert detector_class is not None, "Could not get sample detector class"

        # Instantiate detector
        detector = detector_class(node_tracker=None)

        # Verify it has signal_name attribute
        assert hasattr(detector, "signal_name"), "Signal detector missing signal_name attribute"
        assert detector.signal_name == signal_names[0], (
            f"Expected signal_name='{signal_names[0]}', got '{detector.signal_name}'"
        )

    def test_composed_detector_stores_detectors_correctly(self):
        """Verify ComposedSignalDetector stores detector instances, not names."""
        signal_names = ["graph.node_count", "graph.orphan_count"]

        detector = ComposedSignalDetector(
            signal_names=signal_names,
            node_tracker=None,
        )

        # Verify non_llm_detectors contains detector instances
        assert len(detector.non_llm_detectors) == 2, (
            f"Expected 2 non-LLM detectors, got {len(detector.non_llm_detectors)}"
        )

        # Verify each element is a detector instance with signal_name
        for det in detector.non_llm_detectors:
            assert hasattr(det, "signal_name"), "Detector should have signal_name attribute"
            assert hasattr(det, "detect"), "Detector should have detect method"


class TestImportCorrectness:
    """Test that BaseLLMSignal is importable at runtime (not just TYPE_CHECKING)."""

    def test_base_llm_signal_importable_at_runtime(self):
        """Verify BaseLLMSignal can be imported at runtime.

        Regression test for Bug #1: BaseLLMSignal was only available during
        static type checking, not at runtime.
        """
        # This should not raise ImportError or NameError
        try:
            from src.signals.llm.llm_signal_base import BaseLLMSignal as BLS

            assert BLS is not None
            assert isinstance(BLS, type), "BaseLLMSignal should be a class"
        except (ImportError, NameError) as e:
            pytest.fail(
                f"Failed to import BaseLLMSignal at runtime: {e}. "
                "This suggests it's still under TYPE_CHECKING."
            )

    def test_signal_registry_imports_base_llm_signal(self):
        """Verify signal_registry.py imports BaseLLMSignal at module level."""
        import src.signals.signal_registry as registry_module

        # Check BaseLLMSignal is in module namespace
        assert hasattr(registry_module, "BaseLLMSignal"), (
            "signal_registry.py should import BaseLLMSignal at module level"
        )

        # Verify it's the correct class
        assert registry_module.BaseLLMSignal is BaseLLMSignal, (
            "BaseLLMSignal in signal_registry is not the same as the actual class"
        )
