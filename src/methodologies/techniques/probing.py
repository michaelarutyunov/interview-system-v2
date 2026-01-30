"""Probing technique - explore alternatives and obstacles."""

from typing import TYPE_CHECKING

from src.methodologies.techniques.common import Technique

if TYPE_CHECKING:
    from src.services.turn_pipeline.context import PipelineContext
else:
    PipelineContext = object  # type: ignore


class ProbingTechnique(Technique):
    """Probing technique for exploring alternatives and obstacles.

    Explores different aspects by asking about alternatives,
    variations, and potential obstacles.

    Example questions:
    - "What else could [focus] give you?"
    - "What other options have you considered?"
    - "What might get in the way of [focus]?"
    """

    name = "probing"
    description = "Explore alternatives: 'what else...'"

    async def generate_questions(
        self,
        focus: str | None,
        context: PipelineContext,
    ) -> list[str]:
        """Generate probing questions.

        Uses namespaced signals to adapt:
        - If focus is None: use most recent node
        """
        questions = []

        # Get focus from recent nodes if not provided
        if focus is None:
            recent_nodes = (
                context.recent_nodes if hasattr(context, "recent_nodes") else []
            )
            if recent_nodes:
                focus = (
                    recent_nodes[0].label
                    if hasattr(recent_nodes[0], "label")
                    else str(recent_nodes[0])
                )

        if focus:
            questions.append(f"What else could {focus} give you?")
            questions.append(f"What other options besides {focus} have you considered?")
            questions.append(f"What might get in the way of {focus}?")
        else:
            # No focus available - general probing
            questions.append("What other options have you considered?")
            questions.append("What might be getting in the way?")

        return questions
