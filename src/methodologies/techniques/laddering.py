"""Laddering technique - means-end chain probing."""

from typing import TYPE_CHECKING

from src.methodologies.techniques.common import Technique

if TYPE_CHECKING:
    from src.services.turn_pipeline.context import PipelineContext
else:
    PipelineContext = object  # type: ignore


class LadderingTechnique(Technique):
    """Means-end chain probing technique.

    Probes deeper into the chain by asking "why" questions to uncover
    underlying values and motivations.

    Example questions:
    - "Why is [focus] important to you?"
    - "What does [focus] give you?"
    - "And what does that mean for you?"
    """

    name = "laddering"
    description = "Probe deeper: 'why is that important?'"

    async def generate_questions(
        self,
        focus: str | None,
        context: PipelineContext,
    ) -> list[str]:
        """Generate laddering questions to probe deeper.

        Uses namespaced signals to adapt question depth:
        - If graph.max_depth < 2: add more probing questions
        - If focus is None: use most recent node from context
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
            questions.append(f"Why is {focus} important to you?")
            questions.append(f"What does {focus} give you?")

            # Check current depth from namespaced signal
            if hasattr(context, "signals") and context.signals:
                max_depth = context.signals.get("graph.max_depth", 0)
                if max_depth < 2:
                    questions.append("And what does that mean for you?")
        else:
            # No focus available - general laddering question
            questions.append("What's important to you about this?")
            questions.append("Why does that matter?")

        return questions
