from typing import List
from src.methodologies.base import MethodologyModule, BaseStrategy, BaseSignalDetector
from src.methodologies.jtbd.signals import JTBDSignalDetector
from src.methodologies.jtbd.strategies.explore_situation import ExploreSituationStrategy
from src.methodologies.jtbd.strategies.probe_alternatives import (
    ProbeAlternativesStrategy,
)
from src.methodologies.jtbd.strategies.dig_motivation import DigMotivationStrategy
from src.methodologies.jtbd.strategies.uncover_obstacles import UncoverObstaclesStrategy
from src.methodologies.jtbd.strategies.validate_outcome import ValidateOutcomeStrategy
from src.methodologies.jtbd.strategies.balance_coverage import BalanceCoverageStrategy


class JTBDModule(MethodologyModule):
    """Jobs-to-be-Done methodology module."""

    name = "jobs_to_be_done"
    schema_path = "config/methodologies/jobs_to_be_done.yaml"

    def get_strategies(self) -> List[type[BaseStrategy]]:
        return [
            ExploreSituationStrategy,
            ProbeAlternativesStrategy,
            DigMotivationStrategy,
            UncoverObstaclesStrategy,
            ValidateOutcomeStrategy,
            BalanceCoverageStrategy,
        ]

    def get_signal_detector(self) -> BaseSignalDetector:
        return JTBDSignalDetector()
