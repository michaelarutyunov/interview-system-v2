"""
Prompts for concept and relationship extraction.

Extracts:
- Concepts (potential knowledge graph nodes)
- Relationships (edges between concepts)
- Discourse markers (linguistic signals)

All prompts produce JSON for structured parsing.
"""

from typing import Dict, Any

# Node type descriptions for Means-End Chain methodology
NODE_TYPE_DESCRIPTIONS = {
    "attribute": "Concrete product feature or characteristic (e.g., 'creamy texture', 'plant-based')",
    "functional_consequence": "Tangible outcome from using the product (e.g., 'easier to digest', 'mixes well')",
    "psychosocial_consequence": "Emotional or social outcome (e.g., 'feel healthier', 'impress friends')",
    "instrumental_value": "Preferred mode of behavior (e.g., 'being responsible', 'taking care of myself')",
    "terminal_value": "End-state of existence (e.g., 'happiness', 'security', 'self-fulfillment')",
}

# Edge type descriptions
EDGE_TYPE_DESCRIPTIONS = {
    "leads_to": "Causal or enabling relationship (source enables/causes target)",
    "revises": "Contradiction - newer belief supersedes older one",
}


def get_extraction_system_prompt() -> str:
    """
    Get system prompt for concept/relationship extraction.

    Returns:
        System prompt string for LLM
    """
    node_types_str = "\n".join(
        f"  - {name}: {desc}" for name, desc in NODE_TYPE_DESCRIPTIONS.items()
    )
    edge_types_str = "\n".join(
        f"  - {name}: {desc}" for name, desc in EDGE_TYPE_DESCRIPTIONS.items()
    )

    return f"""You are an expert qualitative researcher extracting knowledge from interview responses.

Your task is to identify concepts and relationships from the respondent's text that reveal their mental model about the product being discussed.

## Valid Node Types (Means-End Chain):
{node_types_str}

## Valid Edge Types:
{edge_types_str}

## Extraction Guidelines:
1. Only extract concepts EXPLICITLY mentioned or clearly implied
2. Use the respondent's own language for concept labels
3. Classify each concept into the most appropriate node type
4. Identify causal relationships indicated by language like "because", "so", "that's why"
5. Look for discourse markers that signal relationships
6. Assign confidence based on how explicit the concept/relationship is
7. Include the verbatim quote that supports each extraction

## Output Format:
Return valid JSON with this structure:
{{
  "concepts": [
    {{
      "text": "concept label in respondent's words",
      "node_type": "one of the valid node types",
      "confidence": 0.0-1.0,
      "source_quote": "verbatim text that supports this"
    }}
  ],
  "relationships": [
    {{
      "source_text": "source concept label",
      "target_text": "target concept label",
      "relationship_type": "leads_to or revises",
      "confidence": 0.0-1.0,
      "source_quote": "verbatim text showing relationship"
    }}
  ],
  "discourse_markers": ["because", "so", ...]
}}

If the text contains no extractable concepts, return:
{{"concepts": [], "relationships": [], "discourse_markers": []}}"""


def get_extraction_user_prompt(text: str, context: str = "") -> str:
    """
    Get user prompt for extraction with the respondent's text.

    Args:
        text: Respondent's utterance to extract from
        context: Optional context from previous turns

    Returns:
        User prompt string
    """
    prompt = f'Extract concepts and relationships from this response:\n\n"{text}"'

    if context:
        prompt = f"Previous context:\n{context}\n\n{prompt}"

    return prompt


def get_extractability_system_prompt() -> str:
    """
    Get system prompt for assessing extractability.

    Used as a fast pre-filter before full extraction.

    Returns:
        System prompt string
    """
    return """You are assessing whether text contains extractable knowledge for a qualitative research interview.

Extractable text contains:
- Product attributes, features, or characteristics
- Benefits, outcomes, or consequences
- Feelings, emotions, or social implications
- Values or life goals
- Causal relationships between any of the above

Non-extractable text includes:
- Simple yes/no responses
- Acknowledgments ("okay", "I see")
- Questions back to the interviewer
- Off-topic tangents
- Very short responses with no substance

Return JSON:
{
  "extractable": true or false,
  "reason": "brief explanation"
}"""


def get_extractability_user_prompt(text: str) -> str:
    """
    Get user prompt for extractability assessment.

    Args:
        text: Text to assess

    Returns:
        User prompt string
    """
    return f'Is this utterance extractable?\n\n"{text}"'


def parse_extraction_response(response_text: str) -> Dict[str, Any]:
    """
    Parse LLM extraction response into structured data.

    Args:
        response_text: Raw LLM response (should be JSON)

    Returns:
        Parsed dict with concepts, relationships, discourse_markers

    Raises:
        ValueError: If response is not valid JSON
    """
    import json

    # Try to extract JSON from response (handle markdown code blocks)
    text = response_text.strip()

    # Remove markdown code block if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in extraction response: {e}")

    # Validate structure
    if not isinstance(data, dict):
        raise ValueError("Extraction response must be a JSON object")

    # Ensure required keys exist with defaults
    return {
        "concepts": data.get("concepts", []),
        "relationships": data.get("relationships", []),
        "discourse_markers": data.get("discourse_markers", []),
    }


def parse_extractability_response(response_text: str) -> tuple[bool, str]:
    """
    Parse LLM extractability response.

    Args:
        response_text: Raw LLM response (should be JSON)

    Returns:
        (is_extractable, reason) tuple

    Raises:
        ValueError: If response is not valid JSON
    """
    import json

    text = response_text.strip()

    # Remove markdown code block if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in extractability response: {e}")

    return (
        bool(data.get("extractable", True)),
        str(data.get("reason", ""))
    )
