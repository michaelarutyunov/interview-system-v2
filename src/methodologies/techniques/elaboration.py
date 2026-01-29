"""Elaboration technique - tell me more."""

from typing import TYPE_CHECKING

from src.methodologies.techniques.common import Technique

if TYPE_CHECKING:
    from src.services.turn_pipeline.context import PipelineContext
else:
    PipelineContext = object  # type: ignore


class ElaborationTechnique(Technique):
    """Elaboration technique for expanding on topics.

    Encourages the respondent to provide more detail about what they mentioned.

    Example questions:
    - "Tell me more about [focus]..."
    - "Can you elaborate on [focus]?"
    - "What else can you share about [focus]?"
    """

    name = "elaboration"
    description = "Tell me more: expand on the topic"

    async def generate_questions(
        self,
        focus: str | None,
        context: PipelineContext,
    ) -> list[str]:
        """Generate elaboration questions.

        Uses namespaced signals to adapt:
        - If new concepts were mentioned: focus on elaboration
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
            questions.append(f"Tell me more about {focus}.")
            questions.append(f"Can you elaborate on {focus}?")
            questions.append(f"What else can you share about {focus}?")
        else:
            # No focus available - general elaboration
            questions.append("Can you tell me more about that?")
            questions.append("What else comes to mind?")

        return questions
