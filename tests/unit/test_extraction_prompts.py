"""Tests for extraction prompts."""

import pytest
import json

from src.llm.prompts.extraction import (
    get_extraction_system_prompt,
    get_extraction_user_prompt,
    get_extractability_system_prompt,
    get_extractability_user_prompt,
    parse_extraction_response,
    parse_extractability_response,
    NODE_TYPE_DESCRIPTIONS,
    EDGE_TYPE_DESCRIPTIONS,
)


class TestExtractionPrompts:
    """Tests for extraction prompt generation."""

    def test_system_prompt_includes_node_types(self):
        """System prompt includes all node type descriptions."""
        prompt = get_extraction_system_prompt()

        for node_type in NODE_TYPE_DESCRIPTIONS:
            assert node_type in prompt

    def test_system_prompt_includes_edge_types(self):
        """System prompt includes all edge type descriptions."""
        prompt = get_extraction_system_prompt()

        for edge_type in EDGE_TYPE_DESCRIPTIONS:
            assert edge_type in prompt

    def test_system_prompt_specifies_json_output(self):
        """System prompt specifies JSON output format."""
        prompt = get_extraction_system_prompt()

        assert "JSON" in prompt
        assert '"concepts"' in prompt
        assert '"relationships"' in prompt

    def test_user_prompt_includes_text(self):
        """User prompt includes the text to extract."""
        text = "I love the creamy texture because it's satisfying"
        prompt = get_extraction_user_prompt(text)

        assert text in prompt

    def test_user_prompt_with_context(self):
        """User prompt includes context when provided."""
        text = "That's right"
        context = "Interviewer asked about texture preferences"
        prompt = get_extraction_user_prompt(text, context)

        assert text in prompt
        assert context in prompt
        assert "Previous context" in prompt


class TestExtractabilityPrompts:
    """Tests for extractability prompt generation."""

    def test_extractability_system_prompt(self):
        """Extractability system prompt explains criteria."""
        prompt = get_extractability_system_prompt()

        assert "extractable" in prompt.lower()
        assert "yes/no" in prompt.lower()
        assert "JSON" in prompt

    def test_extractability_user_prompt(self):
        """Extractability user prompt includes text."""
        text = "Yes"
        prompt = get_extractability_user_prompt(text)

        assert text in prompt


class TestParseExtractionResponse:
    """Tests for parsing extraction responses."""

    def test_parse_valid_json(self):
        """Parses valid JSON response."""
        response = json.dumps({
            "concepts": [
                {"text": "creamy", "node_type": "attribute", "confidence": 0.9}
            ],
            "relationships": [],
            "discourse_markers": ["because"]
        })

        result = parse_extraction_response(response)

        assert len(result["concepts"]) == 1
        assert result["concepts"][0]["text"] == "creamy"
        assert result["discourse_markers"] == ["because"]

    def test_parse_json_with_code_block(self):
        """Parses JSON wrapped in markdown code block."""
        response = '''```json
{
  "concepts": [],
  "relationships": [],
  "discourse_markers": []
}
```'''

        result = parse_extraction_response(response)

        assert result["concepts"] == []

    def test_parse_empty_response(self):
        """Handles empty extraction result."""
        response = '{"concepts": [], "relationships": [], "discourse_markers": []}'

        result = parse_extraction_response(response)

        assert result["concepts"] == []
        assert result["relationships"] == []

    def test_parse_invalid_json_raises(self):
        """Raises ValueError for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_extraction_response("not json")

    def test_parse_missing_keys_uses_defaults(self):
        """Missing keys default to empty lists."""
        response = '{}'

        result = parse_extraction_response(response)

        assert result["concepts"] == []
        assert result["relationships"] == []
        assert result["discourse_markers"] == []


class TestParseExtractabilityResponse:
    """Tests for parsing extractability responses."""

    def test_parse_extractable_true(self):
        """Parses extractable=true response."""
        response = '{"extractable": true, "reason": "Contains product attributes"}'

        is_extractable, reason = parse_extractability_response(response)

        assert is_extractable is True
        assert "attributes" in reason

    def test_parse_extractable_false(self):
        """Parses extractable=false response."""
        response = '{"extractable": false, "reason": "Yes/no response"}'

        is_extractable, reason = parse_extractability_response(response)

        assert is_extractable is False
        assert "Yes/no" in reason

    def test_parse_with_code_block(self):
        """Parses JSON wrapped in code block."""
        response = '```json\n{"extractable": true, "reason": "ok"}\n```'

        is_extractable, reason = parse_extractability_response(response)

        assert is_extractable is True

    def test_parse_invalid_json_raises(self):
        """Raises ValueError for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_extractability_response("yes")
