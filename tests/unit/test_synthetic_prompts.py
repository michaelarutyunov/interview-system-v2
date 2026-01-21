"""Tests for synthetic respondent prompts."""

import pytest

from src.llm.prompts.synthetic import (
    get_synthetic_system_prompt,
    get_synthetic_user_prompt,
    get_synthetic_system_prompt_with_deflection,
    parse_synthetic_response,
    get_available_personas,
    PERSONAS,
)


class TestSystemPrompts:
    """Tests for system prompt generation."""

    def test_base_system_prompt_exists(self):
        """Base system prompt can be generated."""
        prompt = get_synthetic_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_system_prompt_includes_guidelines(self):
        """System prompt includes response guidelines."""
        prompt = get_synthetic_system_prompt()

        assert "Response Guidelines" in prompt
        assert "conversational" in prompt.lower()

    def test_system_prompt_deflection_variant(self):
        """Deflection variant adds deflection guidance."""
        base_prompt = get_synthetic_system_prompt()
        deflection_prompt = get_synthetic_system_prompt_with_deflection()

        assert len(deflection_prompt) > len(base_prompt)
        assert "Deflection" in deflection_prompt
        assert "what really matters to me" in deflection_prompt.lower()


class TestUserPrompts:
    """Tests for user prompt generation."""

    def test_user_prompt_with_question_only(self):
        """User prompt works with just a question."""
        prompt = get_synthetic_user_prompt(
            question="Why is creamy texture important to you?",
            persona="health_conscious"
        )

        assert "creamy texture" in prompt
        assert "health_conscious" in prompt
        assert "Health-Conscious Millennial" in prompt

    def test_user_prompt_includes_persona_traits(self):
        """User prompt includes persona traits."""
        prompt = get_synthetic_user_prompt(
            question="What do you think?",
            persona="price_sensitive"
        )

        assert "Budget-Conscious Shopper" in prompt
        assert "compares prices" in prompt.lower()

    def test_user_prompt_with_previous_concepts(self):
        """User prompt includes previously mentioned concepts."""
        prompt = get_synthetic_user_prompt(
            question="Tell me more about that.",
            persona="health_conscious",
            previous_concepts=["creamy texture", "plant-based", "satisfying"]
        )

        assert "creamy texture" in prompt
        assert "plant-based" in prompt
        assert "Concepts already mentioned" in prompt

    def test_user_prompt_with_interview_context(self):
        """User prompt includes interview context."""
        prompt = get_synthetic_user_prompt(
            question="Why does that matter?",
            persona="quality_focused",
            interview_context={
                "product_name": "Oat Milk",
                "turn_number": 5,
                "coverage_achieved": 0.6
            }
        )

        assert "Oat Milk" in prompt
        assert "turn 5" in prompt
        assert "60% coverage" in prompt

    def test_user_prompt_all_parameters(self):
        """User prompt works with all parameters."""
        prompt = get_synthetic_user_prompt(
            question="What else matters?",
            persona="sustainability_minded",
            previous_concepts=["sustainable packaging"],
            interview_context={
                "product_name": "Oat Milk",
                "turn_number": 3,
                "coverage_achieved": 0.4
            }
        )

        assert "What else matters?" in prompt
        assert "sustainability" in prompt.lower()
        assert "sustainable packaging" in prompt.lower()
        assert "Oat Milk" in prompt


class TestPersonaConfig:
    """Tests for persona configuration."""

    def test_personas_have_required_keys(self):
        """All personas have required configuration keys."""
        for persona_id, config in PERSONAS.items():
            assert "name" in config
            assert "traits" in config
            assert isinstance(config["traits"], list)
            assert len(config["traits"]) > 0
            assert "speech_pattern" in config

    def test_get_available_personas(self):
        """Can get list of available personas."""
        personas = get_available_personas()

        assert isinstance(personas, dict)
        assert "health_conscious" in personas
        assert personas["health_conscious"] == "Health-Conscious Millennial"


class TestParseSyntheticResponse:
    """Tests for response parsing."""

    def test_parse_plain_response(self):
        """Parses plain response unchanged."""
        response = "I really like the creamy texture because it feels satisfying."
        parsed = parse_synthetic_response(response)

        assert parsed == response

    def test_parse_removes_markdown_quotes(self):
        """Removes markdown quote wrapping."""
        response = '"""I like the texture."""'
        parsed = parse_synthetic_response(response)

        assert parsed == "I like the texture."
        assert not parsed.startswith('"')

    def test_parse_removes_response_prefix(self):
        """Removes 'Response:' prefix."""
        response = "Response: I think it's great."
        parsed = parse_synthetic_response(response)

        assert parsed == "I think it's great."
        assert not parsed.lower().startswith("response:")

    def test_parse_removes_your_response_prefix(self):
        """Removes 'Your response:' prefix."""
        response = "Your response: It matters because..."
        parsed = parse_synthetic_response(response)

        assert parsed == "It matters because..."

    def test_parse_whitespace_cleanup(self):
        """Cleans up extra whitespace."""
        response = '  "  Response with spaces  "  '
        parsed = parse_synthetic_response(response)

        assert parsed == "Response with spaces"
