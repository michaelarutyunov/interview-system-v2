from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext


class SignalState(BaseModel):
    """Base class for methodology-specific signal state."""

    # Common signals all methodologies share
    strategy_repetition_count: int = 0
    turns_since_strategy_change: int = 0
    response_confidence: float = 0.5
    response_ambiguity: float = 0.0

    class Config:
        extra = "allow"  # Allow methodology-specific signals


class BaseSignalDetector(ABC):
    """Base class for methodology-specific signal detection."""

    @abstractmethod
    async def detect(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> SignalState:
        """Detect signals from current turn context."""
        pass


class BaseStrategy(ABC):
    """Base class for methodology-specific strategies."""

    name: str
    description: str

    @staticmethod
    @abstractmethod
    def score_signals() -> Dict[str, float]:
        """
        Return signal weights for this strategy.
        Positive weights = signal increases strategy score.
        Negative weights = signal decreases strategy score.
        """
        pass

    @abstractmethod
    async def generate_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
    ) -> Optional[str]:
        """Determine focus node for this strategy, if applicable."""
        pass


class MethodologyModule(ABC):
    """Base class for methodology module registration."""

    name: str
    schema_path: str  # Path to YAML schema

    @abstractmethod
    def get_strategies(self) -> List[type[BaseStrategy]]:
        """Return all strategy classes for this methodology."""
        pass

    @abstractmethod
    def get_signal_detector(self) -> BaseSignalDetector:
        """Return signal detector instance for this methodology."""
        pass
