"""Signal detector registry for composing signals from pools.

Maps namespaced signal names to detector classes and handles
dynamic signal detection with auto-registration and topological sort.

Now includes LLM-aware signal detection that batches LLM signals
into a single Kimi K2.5 API call.
"""

import structlog
from typing import Any, List, Optional, Set, TYPE_CHECKING

from src.core.exceptions import ScorerFailureError
from src.services.node_state_tracker import NodeStateTracker
from src.signals.signal_base import SignalDetector

# LLM batch detection (added for LLM signal support)
from src.signals.llm.batch_detector import LLMBatchDetector

if TYPE_CHECKING:
    from src.signals.llm.llm_signal_base import BaseLLMSignal
    from src.services.turn_pipeline.context import PipelineContext

log = structlog.get_logger(__name__)


class ComposedSignalDetector:
    """Composed signal detector from YAML config.

    Detects all signals for a methodology by composing detectors
    from shared signal pools.

    Uses auto-registration (via __init_subclass__) and topological sort
    to determine signal detection order based on declared dependencies.

    Now includes special handling for LLM signals to batch
    them into a single API call via LLMBatchDetector.
    """

    def __init__(
        self,
        signal_names: list[str],
        node_tracker: Optional[NodeStateTracker] = None,
        llm_client: Optional[Any] = None,
    ):
        """Initialize composed detector.

        Args:
            signal_names: List of namespaced signal names to detect
            node_tracker: NodeStateTracker instance (required for node-level signals)
            llm_client: Optional LLM client for batch LLM signal detection
        """
        self.signal_names = signal_names
        self.node_tracker = node_tracker
        self.llm_client = llm_client

        # Separate LLM signals for batch detection

        llm_signal_names: Set[str] = set()
        non_llm_signal_names: List[str] = []

        for name in signal_names:
            if self._is_llm_signal(name):
                llm_signal_names.add(name)
            else:
                non_llm_signal_names.append(name)

        # Store LLM client if provided
        if llm_client:
            self.llm_client = llm_client

        # Create non-LLM detector instances normally
        self.non_llm_detectors: List[SignalDetector] = []
        for signal_name in non_llm_signal_names:
            signal_class = SignalDetector.get_signal_class(signal_name)
            if signal_class is None:
                raise ValueError(f"Unknown signal: {signal_name}")
            detector = signal_class(node_tracker=node_tracker)
            self.non_llm_detectors.append(detector)

        # LLM detector will be set separately via set_llm_detector()
        self._llm_detector: Optional[LLMBatchDetector] = None
        self.llm_signal_names = llm_signal_names

        # Combine all detectors
        self.detectors: self.non_llm_detectors

    @staticmethod
    def _is_llm_signal(signal_name: str) -> bool:
        """Check if a signal name is an LLM signal."""
        try:
            from src.signals.llm.decorator import llm_signal
            signal_cls = llm_signal._registered_classes.get(signal_name)
            return signal_cls is not None and issubclass(signal_cls, BaseLLMSignal)
        except (AttributeError, ImportError):
            return False

    def set_llm_detector(self, detector: Any) -> None:
        """Set the LLM batch detector to use for LLM signals."""
        self._llm_detector = detector
        log.debug(
            f"LLMBatchDetector set for {len(self.llm_signal_names)} "
            f"LLM signals: {sorted(self.llm_signal_names)}"
        )

    @classmethod
    def get_known_signal_names(cls) -> Set[str]:
        """Return set of all registered signal names."""
        return set(SignalDetector.get_registered_signals().keys())

    async def detect(
        self,
        context: "PipelineContext",
        graph_state: Any,
        response_text: str,
    ) -> dict[str, Any]:
        """Detect all signals in dependency order.

        Args:
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text

        Returns:
            Dictionary of all detected signals

        Raises:
            ScorerFailureError: If any signal detector fails
        """
        all_signals: dict[str, Any] = {}

        # Detect non-LLM signals using individual calls
        for signal_name, detector in zip(self.non_llm_detectors, self.non_llm_detectors):
            if signal_name not in self.llm_signal_names:
                # For signals with dependencies, provide context with previous signals
                if detector.dependencies:
                    class _ContextWithSignals:
                        def __init__(self, signals_dict):
                            self.signals = signals_dict
                    detect_context = _ContextWithSignals(all_signals)
                else:
                    detect_context = context

                try:
                    signals = await detector.detect(
                        detect_context, graph_state, response_text
                    )
                    all_signals.update(signals)
                except Exception as e:
                    log.error(
                        "signal_detector_failed",
                        signal_name=signal_name,
                        error=str(e),
                        exc_info=True,
                    )
                    raise ScorerFailureError(
                        f"Signal detector '{signal_name}' failed: {e}"
                    ) from e

        # Detect LLM signals using batch detector
        if self.llm_signal_names and self._llm_detector:
            try:
                # Filter to only LLM detectors
                llm_detectors = [
                    d for d in self.detectors if d.signal_name in self.llm_signal_names
                ]

                log.debug(
                    f"Batching {len(self.llm_signal_names)} LLM signals: "
                    f"{sorted(self.llm_signal_names)}"
                )

                # Batch all LLM signals in one call
                llm_signals = await self._llm_detector.detect(
                    context=context,
                    graph_state=graph_state,
                    response_text=response_text,
                    signal_classes=llm_detectors,
                )

                # Merge LLM signal results into all_signals
                all_signals.update(llm_signals)

                log.info(f"LLM batch detection complete: {llm_signals}")

            except Exception as e:
                log.error(f"LLM batch detection failed: {e}", exc_info=True)
                # Re-raise as ScorerFailureError to maintain consistent error handling
                raise ScorerFailureError(f"LLM signal detection failed: {e}") from e

        return all_signals
