from typing import List
from src.methodologies.base import MethodologyModule, BaseStrategy, BaseSignalDetector


class JTBDModule(MethodologyModule):
    """Jobs-to-be-Done methodology module."""

    name = "jobs_to_be_done"
    schema_path = "config/methodologies/jobs_to_be_done.yaml"

    def get_strategies(self) -> List[type[BaseStrategy]]:
        # Stub implementation - will be populated in Phase 3
        return []

    def get_signal_detector(self) -> BaseSignalDetector:
        # Stub implementation - will be populated in Phase 3
        from src.methodologies.base import BaseSignalDetector

        class StubSignalDetector(BaseSignalDetector):
            async def detect(self, context, graph_state, response_text):
                from src.methodologies.base import SignalState

                return SignalState()

        return StubSignalDetector()
