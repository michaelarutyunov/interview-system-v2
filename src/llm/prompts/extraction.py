"""
Prompts for concept and relationship extraction.

Extracts:
- Concepts (potential knowledge graph nodes)
- Relationships (edges between concepts)
- Discourse markers (linguistic signals)

All prompts produce JSON for structured parsing.

Architecture:
- Universal principles are hardcoded (apply to all methodologies)
- Methodology-specific content loaded from schema YAML
- Prompts are methodology-agnostic and schema-driven
"""

from typing import Dict, Any, Optional

from src.core.schema_loader import load_methodology
from src.core.concept_loader import load_concept


def get_extraction_system_prompt(
    methodology: str = "means_end_chain",
    concept_id: Optional[str] = None,
) -> str:
    """
    Get system prompt for concept/relationship extraction.

    Args:
        methodology: Methodology schema name (e.g., "means_end_chain")
        concept_id: Optional concept ID to include elements for element linking

    Returns:
        System prompt string for LLM
    """
    # Load schema and get descriptions
    schema = load_methodology(methodology)
    node_descriptions = schema.get_node_descriptions()
    edge_descriptions = schema.get_edge_descriptions()

    # Load concept elements for element linking
    elements_section = ""
    if concept_id:
        try:
            concept = load_concept(concept_id)
            elements_list = []
            for element in concept.elements:
                aliases_str = ", ".join([element.label] + element.aliases)
                elements_list.append(
                    f"  - Element {element.id}: {element.label} (aliases: {aliases_str})"
                )

            elements_section = f"""
## Concept Elements ({concept.name}):
The following are predefined semantic elements for this research topic.
For each extracted concept, identify which element(s) it relates to by element ID.
{chr(10).join(elements_list)}

Important:
- A concept can relate to multiple elements (e.g., "creamy foam" relates to elements 1 and 4)
- Only link to elements when there is a clear semantic relationship
- If no clear relationship exists, return an empty array for linked_elements
"""
        except Exception as e:
            import structlog

            log = structlog.get_logger(__name__)
            log.warning(
                "concept_load_failed_for_extraction",
                concept_id=concept_id,
                error=str(e),
            )

    node_types_str = "\n".join(
        f"  - {name}: {desc}" for name, desc in node_descriptions.items()
    )
    edge_types_str = "\n".join(
        f"  - {name}: {desc}" for name, desc in edge_descriptions.items()
    )

    # Methodology-specific content from schema
    methodology_guidelines = schema.get_extraction_guidelines()
    methodology_examples = schema.get_relationship_examples()

    # Build methodology-specific section
    methodology_section = ""
    if methodology_guidelines:
        guidelines_str = "\n".join(f"  - {g}" for g in methodology_guidelines)
        methodology_section += f"""
## Methodology-Specific Extraction Guidelines ({methodology}):
{guidelines_str}
"""

    if methodology_examples:
        examples_str = ""
        for name, example_spec in methodology_examples.items():
            examples_str += f"""
**{name.replace("_", " ").title()}:**
{example_spec.description}
Example: {example_spec.example}
Extract: {example_spec.extraction}
"""
        methodology_section += f"""
## Relationship Extraction Examples ({methodology}):
{examples_str}
"""

    return f"""You are an expert qualitative researcher extracting knowledge from interview responses.

Your task is to identify concepts and relationships from the respondent's text that reveal their mental model about the product being discussed.

## Valid Node Types ({methodology.replace("_", " ").title()}):
{node_types_str}

## Valid Edge Types:
{edge_types_str}

## Stance Detection:
For each concept, determine the respondent's stance:
- +1 (positive): Respondent expresses liking, preference, agreement, or positive emotions
- 0 (neutral): Respondent states facts or neutral observations without clear positive/negative sentiment
- -1 (negative): Respondent expresses dislike, criticism, disagreement, or negative emotions

Examples:
- "I love how creamy it is" → stance: +1
- "It mixes well" → stance: 0
- "I hate the aftertaste" → stance: -1
{elements_section}
## Universal Extraction Principles:
1. Only extract concepts EXPLICITLY mentioned or clearly implied
2. Use the respondent's own language for concept labels
3. Classify each concept into the most appropriate node type
4. Assign confidence based on how explicit the concept/relationship is
5. Include the verbatim quote that supports each extraction
6. Determine stance based on sentiment and emotional content
{methodology_section}
## Output Format:
Return valid JSON with this structure:
{{
  "concepts": [
    {{
      "text": "concept label in respondent's words",
      "node_type": "one of the valid node types",
      "confidence": 0.0-1.0,
      "stance": -1, 0, or 1,
      "source_quote": "verbatim text that supports this",
      "linked_elements": [1, 2]  // Array of element IDs this concept relates to (empty array if none)
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


def get_extractability_system_prompt(methodology: str = "means_end_chain") -> str:
    """
    Get system prompt for assessing extractability.

    Used as a fast pre-filter before full extraction.

    Args:
        methodology: Methodology schema name (e.g., "means_end_chain")

    Returns:
        System prompt string
    """
    # Load methodology-specific extractability criteria
    schema = load_methodology(methodology)
    criteria = schema.get_extractability_criteria()

    extractable_items = "\n".join(f"- {item}" for item in criteria.extractable_contains)
    non_extractable_items = "\n".join(
        f"- {item}" for item in criteria.non_extractable_contains
    )

    return f"""You are assessing whether text contains extractable knowledge for a qualitative research interview ({methodology.replace("_", " ")}).

Extractable text contains:
{extractable_items if extractable_items else "- Relevant content for analysis"}

Non-extractable text includes:
{non_extractable_items if non_extractable_items else "- Simple yes/no, acknowledgments, off-topic"}

Return JSON:
{{
  "extractable": true or false,
  "reason": "brief explanation"
}}"""


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

    return (bool(data.get("extractable", True)), str(data.get("reason", "")))
