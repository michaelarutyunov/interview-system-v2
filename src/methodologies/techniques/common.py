"""Base class for questioning techniques."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.turn_pipeline.context import PipelineContext
else:
    PipelineContext = object  # type: ignore


class Technique(ABC):
    """A questioning technique - the 'how' of asking questions.

    Techniques are reusable modules that generate questions using specific
    questioning patterns. They are distinct from strategies, which decide
    WHEN to use a particular technique based on signals.

    Attributes:
        name: Unique identifier for this technique
        description: Human-readable description of what this technique does

    Example:
        class LadderingTechnique(Technique):
            name = "laddering"
            description = "Probe deeper: 'why is that important?'"

            async def generate_questions(self, focus, context):
                return [
                    f"Why is {focus} important to you?",
                    f"What does {focus} give you?",
                ]
    """

    name: str
    description: str

    @abstractmethod
    async def generate_questions(
        self,
        focus: str | None,
        context: PipelineContext,
    ) -> list[str]:
        """Generate 1-3 questions using this technique.

        Args:
            focus: The concept/node to focus on (may be None for general questions)
            context: Pipeline context with signals, graph state, etc.

        Returns:
            List of question strings (typically 1-3 questions)
        """
        ...
