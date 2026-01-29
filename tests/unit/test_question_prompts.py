"""Tests for question prompts."""

from src.llm.prompts.question import (
    get_question_system_prompt,
    get_question_user_prompt,
    get_opening_question_system_prompt,
    get_opening_question_user_prompt,
    get_graph_summary,
    format_question,
)
from src.core.schema_loader import load_methodology


class TestQuestionSystemPrompt:
    """Tests for question system prompt generation."""

    def test_includes_strategy_name(self):
        """System prompt includes strategy name."""
        prompt = get_question_system_prompt("deepen")
        assert "Deepen" in prompt

    def test_includes_strategy_intent(self):
        """System prompt includes strategy intent."""
        prompt = get_question_system_prompt("deepen")
        assert "deeper motivations" in prompt.lower()

    def test_includes_methodology(self):
        """System prompt includes Means-End Chain methodology."""
        prompt = get_question_system_prompt()
        assert "Means-End Chain" in prompt

    def test_different_strategies(self):
        """Different strategies produce different prompts."""
        deepen = get_question_system_prompt("deepen")
        broaden = get_question_system_prompt("broaden")

        assert "why" in deepen.lower()
        assert "what else" in broaden.lower()

    def test_defaults_to_deepen(self):
        """Unknown strategy defaults to deepen."""
        prompt = get_question_system_prompt("unknown")
        assert "Deepen" in prompt


class TestQuestionUserPrompt:
    """Tests for question user prompt generation."""

    def test_includes_focus_concept(self):
        """User prompt includes focus concept."""
        prompt = get_question_user_prompt("creamy texture")
        assert "creamy texture" in prompt

    def test_includes_recent_utterances(self):
        """User prompt includes conversation context."""
        utterances = [
            {"speaker": "system", "text": "What do you think?"},
            {"speaker": "user", "text": "I like the taste"},
        ]
        prompt = get_question_user_prompt("taste", recent_utterances=utterances)

        assert "I like the taste" in prompt
        assert "Respondent:" in prompt

    def test_includes_graph_summary(self):
        """User prompt includes graph summary."""
        prompt = get_question_user_prompt(
            "test",
            graph_summary="Explored 5 concepts",
        )
        assert "5 concepts" in prompt

    def test_limits_recent_utterances(self):
        """Only includes last 5 utterances."""
        utterances = [{"speaker": "user", "text": f"Turn {i}"} for i in range(10)]
        prompt = get_question_user_prompt("test", recent_utterances=utterances)

        assert "Turn 9" in prompt
        assert "Turn 0" not in prompt  # Older turns excluded


class TestOpeningQuestionPrompts:
    """Tests for opening question prompts."""

    def test_system_prompt_is_warm(self):
        """Opening system prompt encourages warmth."""
        prompt = get_opening_question_system_prompt()
        assert "warm" in prompt.lower() or "friendly" in prompt.lower()

    def test_user_prompt_includes_concept(self):
        """User prompt includes objective."""
        prompt = get_opening_question_user_prompt(
            "Understand user experiences with Oat Milk"
        )
        assert "Oat Milk" in prompt

    def test_user_prompt_includes_objective(self):
        """User prompt includes interview objective."""
        prompt = get_opening_question_user_prompt(
            "Understand user experiences with plant-based milk alternatives"
        )
        assert "plant-based milk alternatives" in prompt
        assert "objective" in prompt.lower()

    def test_user_prompt_includes_methodology(self):
        """User prompt includes methodology context when provided."""
        schema = load_methodology("means_end_chain")
        prompt = get_opening_question_user_prompt(
            "Understand coffee drinking habits", methodology=schema
        )
        assert "means_end_chain" in prompt
        assert "opening_bias" in prompt.lower() or "guidance" in prompt.lower()

    def test_system_prompt_includes_methodology(self):
        """System prompt includes methodology context when provided."""
        schema = load_methodology("means_end_chain")
        prompt = get_opening_question_system_prompt(methodology=schema)
        assert "means_end_chain" in prompt
        assert "Methodology Context" in prompt


class TestGraphSummary:
    """Tests for graph summary generation."""

    def test_includes_depth(self):
        """Summary includes depth label."""
        summary = get_graph_summary(
            nodes_by_type={"attribute": 2},
            recent_concepts=["texture"],
            depth_achieved=2,
        )
        assert "developing" in summary.lower() or "depth" in summary.lower()

    def test_includes_node_count(self):
        """Summary includes total node count."""
        summary = get_graph_summary(
            nodes_by_type={"attribute": 3, "functional_consequence": 2},
            recent_concepts=[],
            depth_achieved=1,
        )
        assert "5" in summary

    def test_includes_recent_concepts(self):
        """Summary includes recent concepts."""
        summary = get_graph_summary(
            nodes_by_type={},
            recent_concepts=["texture", "taste"],
            depth_achieved=0,
        )
        assert "texture" in summary


class TestFormatQuestion:
    """Tests for question formatting."""

    def test_strips_whitespace(self):
        """Strips leading/trailing whitespace."""
        result = format_question("  Hello?  ")
        assert result == "Hello?"

    def test_removes_quotes(self):
        """Removes surrounding quotes."""
        assert format_question('"What do you think?"') == "What do you think?"
        assert format_question("'What do you think?'") == "What do you think?"

    def test_adds_question_mark(self):
        """Adds question mark if missing."""
        result = format_question("Why is that important")
        assert result.endswith("?")

    def test_preserves_existing_punctuation(self):
        """Preserves existing punctuation."""
        assert format_question("Tell me more.") == "Tell me more."
        assert format_question("Why?") == "Why?"
