"""Frame resistance signal — detects explicit rejection of the question's framing (1-5)."""

from src.signals.llm.decorator import llm_global_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_global_signal(
    signal_name="response.semantic.llm.frame_resistance",
    description="Whether the respondent explicitly rejects the question's framing or premise.",
)
class FrameResistanceSignal(BaseLLMSignal):
    """Global frame resistance — explicit rejection, not cooperative hedging."""

    boolean_output: bool = True

    RUBRIC: str = """\
Does the respondent explicitly reject the framing or premise of the question?

Distinguish frame rejection from cooperative hedging:
- Frame rejection (score 4-5): "that's not the right framing", "I wouldn't put it that way",
  "that's not how I think about it", "I'd push back on that", "that seems like a stretch",
  dismissing the premise of the question.
- Cooperative hedging (score 1-3): "I'm not sure", "maybe", "I think", "I guess",
  "possibly", "it depends" — these soften claims but don't reject the framing.

1 = No resistance. Fully accepts the question's framing, answers within it.
2 = Minor qualification. "It depends" or "sometimes" but still works within the frame.
3 = Ambivalent. Genuine uncertainty about whether the framing applies, but not rejecting it.
4 = Explicit rejection. States clearly that the framing doesn't fit their experience.
   "I'm not sure that's the right framing for me", "I wouldn't put it that way".
5 = Strong rejection with correction. Rejects framing AND offers alternative framing.
   "That's not how I think about it at all — I'd describe it as..."""

    CROSSCHECK: str = """\
IMPORTANT: A respondent who is hesitant (engagement=1-2) or uncertain (certainty=1-2)
is NOT necessarily rejecting the framing. Only score frame_resistance 4+ when the
respondent's language explicitly pushes back on the question's premise or framing.
Hesitant cooperation is NOT frame resistance."""
