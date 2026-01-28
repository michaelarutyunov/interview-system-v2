"""Response quality signals - sentiment, uncertainty, ambiguity."""

from src.methodologies.signals.llm.common import BaseLLMSignal


class SentimentSignal(BaseLLMSignal):
    """Analyzes response sentiment: positive | neutral | negative.

    Namespaced signal: llm.sentiment
    Cost: high (LLM analysis)
    Refresh: per_response (ALWAYS fresh)

    Sentiment categories:
    - positive: Enthusiastic, favorable language
    - neutral: Factual, balanced language
    - negative: Unfavorable, hesitant language
    """

    signal_name = "llm.sentiment"

    async def _analyze_with_llm(self, response_text: str) -> dict:
        """Analyze sentiment (simplified for PoC).

        Production: Use LLM sentiment analysis.
        Proof-of-concept: Use simple keyword detection.
        """
        text_lower = response_text.lower()

        # Positive indicators
        positive_words = [
            "love",
            "like",
            "great",
            "good",
            "excellent",
            "enjoy",
            "prefer",
            "appreciate",
        ]

        # Negative indicators
        negative_words = [
            "hate",
            "dislike",
            "bad",
            "terrible",
            "don't",
            "don t",
            "cannot",
            "can't",
            "can t",
            "won't",
            "won t",
            "no",
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {self.signal_name: sentiment}


class UncertaintySignal(BaseLLMSignal):
    """Analyzes how uncertain/hesitant the response is.

    Namespaced signal: llm.uncertainty
    Cost: high (LLM analysis)
    Refresh: per_response (ALWAYS fresh)

    Returns float 0-1:
    - 0: Very confident, certain language
    - 1: Highly uncertain, hedging language
    """

    signal_name = "llm.uncertainty"

    async def _analyze_with_llm(self, response_text: str) -> dict:
        """Analyze uncertainty (simplified for PoC).

        Production: Use LLM to detect hedging, uncertainty markers.
        Proof-of-concept: Use keyword detection.
        """
        text_lower = response_text.lower()

        # Uncertainty indicators
        uncertainty_words = [
            "maybe",
            "perhaps",
            "possibly",
            "might",
            "could be",
            "not sure",
            "uncertain",
            "think",
            "guess",
            "probably",
            "somewhat",
            "kind of",
            "kinda",
        ]

        uncertainty_count = sum(
            1 for word in uncertainty_words if word in text_lower.split()
        )
        word_count = len(response_text.split())

        # Normalize by response length (0-1 range)
        uncertainty_score = min(uncertainty_count / max(word_count, 1), 1.0)

        return {self.signal_name: uncertainty_score}


class AmbiguitySignal(BaseLLMSignal):
    """Analyzes how ambiguous/vague the response is.

    Namespaced signal: llm.ambiguity
    Cost: high (LLM analysis)
    Refresh: per_response (ALWAYS fresh)

    Returns float 0-1:
    - 0: Very specific, concrete language
    - 1: Highly ambiguous, vague language
    """

    signal_name = "llm.ambiguity"

    async def _analyze_with_llm(self, response_text: str) -> dict:
        """Analyze ambiguity (simplified for PoC).

        Production: Use LLM to detect vague language.
        Proof-of-concept: Use word count and specificity heuristics.
        """
        word_count = len(response_text.split())

        # Ambiguity indicators
        ambiguous_words = [
            "thing",
            "something",
            "anything",
            "stuff",
            "whatever",
            "stuff like that",
            "and so on",
            "etc",
        ]

        ambiguous_count = sum(
            1 for word in ambiguous_words if word in response_text.lower()
        )

        # Also penalize very short responses (likely incomplete)
        short_response_penalty = 1.0 if word_count < 5 else 0.0

        # Normalize and combine
        ambiguity_score = min(
            (ambiguous_count / max(word_count, 1)) + short_response_penalty,
            1.0,
        )

        return {self.signal_name: ambiguity_score}
