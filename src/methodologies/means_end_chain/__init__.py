from typing import List
from src.methodologies.base import MethodologyModule, BaseStrategy, BaseSignalDetector
from src.methodologies.means_end_chain.signals import MECSignalDetector
from src.methodologies.means_end_chain.strategies.ladder_deeper import (
    LadderDeeperStrategy,
)
from src.methodologies.means_end_chain.strategies.clarify_relationship import (
    ClarifyRelationshipStrategy,
)
from src.methodologies.means_end_chain.strategies.explore_new_attribute import (
    ExploreNewAttributeStrategy,
)
from src.methodologies.means_end_chain.strategies.reflect_and_validate import (
    ReflectAndValidateStrategy,
)


class MECModule(MethodologyModule):
    """Means-End Chain methodology module."""

    name = "means_end_chain"
    schema_path = "config/methodologies/means_end_chain.yaml"

    def get_strategies(self) -> List[type[BaseStrategy]]:
        return [
            LadderDeeperStrategy,
            ClarifyRelationshipStrategy,
            ExploreNewAttributeStrategy,
            ReflectAndValidateStrategy,
        ]

    def get_signal_detector(self) -> BaseSignalDetector:
        return MECSignalDetector()
