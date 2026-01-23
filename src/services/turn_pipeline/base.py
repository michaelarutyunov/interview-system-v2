"""
Base stage class for turn processing pipeline.

ADR-008 Phase 3: All pipeline stages inherit from TurnStage.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import PipelineContext


class TurnStage(ABC):
    """
    Abstract base class for pipeline stages.

    Each stage must implement the process() method which takes a PipelineContext,
    performs its operation, updates the context, and returns the modified context.
    """

    @abstractmethod
    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Process this stage, update context, return modified context.

        Args:
            context: Current turn context with all accumulated state

        Returns:
            Modified context with stage results added
        """
        pass

    @property
    def stage_name(self) -> str:
        """Return the stage name for logging."""
        return self.__class__.__name__
