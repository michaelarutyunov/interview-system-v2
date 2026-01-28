from typing import List
from src.methodologies.base import MethodologyModule, BaseStrategy, BaseSignalDetector


class MECModule(MethodologyModule):
    """Means-End Chain methodology module."""

    name = "means_end_chain"
    schema_path = "config/methodologies/means_end_chain.yaml"

    def get_strategies(self) -> List[type[BaseStrategy]]:
        # Stub implementation - will be populated in Phase 2
        return []

    def get_signal_detector(self) -> BaseSignalDetector:
        # Stub implementation - will be populated in Phase 2
        from src.methodologies.base import BaseSignalDetector

        class StubSignalDetector(BaseSignalDetector):
            async def detect(self, context, graph_state, response_text):
                from src.methodologies.base import SignalState

                return SignalState()

        return StubSignalDetector()
