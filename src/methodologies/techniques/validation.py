"""Validation technique - confirm outcomes and understanding."""

from src.methodologies.techniques.common import Technique


class ValidationTechnique(Technique):
    """Validation technique for confirming outcomes.

    Confirms understanding and validates the outcome or value
    that the user is seeking.

    Example questions:
    - "So you want [focus] because..."
    - "It sounds like [focus] is important to you because..."
    - "Am I right that [focus] gives you..."
    """

    name = "validation"
    description = "Confirm outcomes: 'so you want...'"

    async def generate_questions(
        self,
        focus: str | None,
        context: any,
    ) -> list[str]:
        """Generate validation questions.

        Uses namespaced signals to adapt:
        - If meta.interview_progress is high: more definitive confirmation
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
            questions.append(f"So you want {focus} because...?")
            questions.append(
                f"It sounds like {focus} is important to you. Why is that?"
            )
            questions.append(f"Am I right that {focus} gives you something meaningful?")
        else:
            # No focus available - general validation
            questions.append("So what I'm hearing is...?")
            questions.append("Let me confirm my understanding...")

        return questions
