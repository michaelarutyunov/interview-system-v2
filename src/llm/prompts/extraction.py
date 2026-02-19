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
    concept_naming_convention: Optional[str] = None,
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
    edge_descriptions = schema.get_edge_descriptions_with_connections()

    # Load concept elements for element linking (LEGACY - exploratory interviews don't use elements)
    # For exploratory research, elements list is always empty, so this section is not added to prompt
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

    # Determine primary edge type for this methodology's conversational examples
    # (avoids hardcoding MEC-specific "leads_to" which doesn't exist in JTBD etc.)
    valid_edge_types = schema.get_valid_edge_types()
    primary_edge_type = next(
        (et for et in valid_edge_types if et != "revises"),
        valid_edge_types[0] if valid_edge_types else "leads_to",
    )
    edge_type_list = ", ".join(valid_edge_types)

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

    # Build naming convention instruction
    if concept_naming_convention:
        naming_instruction = f"{concept_naming_convention} The source_quote field captures the respondent's verbatim language."
    else:
        naming_instruction = "Name concepts concisely according to their node type. Use the node type descriptions and examples above as naming models. The source_quote field captures the respondent's verbatim language."

    return f"""You are an expert qualitative researcher extracting knowledge from interview responses.

Your task is to identify concepts and relationships from the respondent's text that reveal their mental model about the product being discussed.

## Valid Node Types ({methodology.replace("_", " ").title()}):
{node_types_str}

## Valid Edge Types:
{edge_types_str}

{elements_section}
## Universal Extraction Principles:
1. Only extract concepts EXPLICITLY mentioned or clearly implied. When multiple concepts co-occur in a response, create relationships between them using the methodology's edge types—even if the connection is implicit—with confidence proportional to your certainty.
2. {naming_instruction}
3. Classify each concept into the most appropriate node type
4. Assign confidence based on how explicit the concept/relationship is
5. Include the verbatim quote that supports each extraction

## Cross-Turn Relationship Bridging (CRITICAL):
When creating relationships:
- **Connect new concepts to existing ones**: If the context includes "[Existing graph concepts from previous turns]", reference those exact labels as source_text or target_text
- **Bridge Q→A pairs**: When the interviewer asks about a topic and the respondent answers, create a relationship from the question topic → answer concept
- **Do NOT re-extract existing concepts**: If a concept already exists in the graph, use its exact label in relationships but do not add it as a new concept
- Use the methodology's appropriate relationship type (commonly "{primary_edge_type}")
- Set confidence 0.7-0.8 for implicit connections, 0.85-1.0 for explicit ones

Examples:
- Existing concept: "morning routine"
  Respondent: "That routine helps me stay focused at work"
  → Extract new concept: "stay focused at work"
  → Extract relationship: "morning routine" {primary_edge_type} "stay focused at work"
  (References existing concept without re-extracting it)

- Interviewer: "Why does that nice sensation matter?"
  Respondent: "It feels like a good start of the day"
  → Extract relationship: "nice sensation" {primary_edge_type} "good start of the day"
{methodology_section}
## Output Format:
Return valid JSON with this structure:
{{
  "concepts": [
    {{
      "text": "concise concept label phrased according to its node type",
      "node_type": "one of the valid node types",
      "confidence": 0.0-1.0,
      "source_quote": "verbatim text that supports this",
      "linked_elements": [1, 2]  // Array of element IDs this concept relates to (empty array if none)
    }}
  ],
  "relationships": [
    {{
      "source_text": "source concept label",
      "target_text": "target concept label",
      "relationship_type": "one of: {edge_type_list}",
      "confidence": 0.0-1.0,
      "source_quote": "verbatim text showing relationship"
    }}
  ]
}}

If the text contains no extractable concepts, return:
{{"concepts": [], "relationships": []}}"""


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


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from LLM response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _repair_json(text: str) -> str:
    """Attempt to repair common LLM JSON generation errors.

    Handles three frequent failure modes:
    1. Missing commas between properties ("key": value "key2": value2)
    2. Trailing commas before closing brackets ([...,] or {...,})
    3. Truncated JSON (incomplete closing brackets/braces)
    """
    import re

    # Fix 1: Missing commas between properties/elements
    # Pattern: "value" "key" or number "key" (missing comma between them)
    # e.g. "confidence": 0.9 "source_quote": "..."
    text = re.sub(r"(\")\s*\n\s*(\")", r"\1,\n\2", text)
    text = re.sub(r"(\d)\s*\n\s*(\")", r"\1,\n\2", text)
    text = re.sub(r"(true|false|null)\s*\n\s*(\")", r"\1,\n\2", text)
    # Also handle same-line missing commas: "value" "key"
    text = re.sub(r'(\")\s+(\"[a-z_]+"?\s*:)', r"\1, \2", text)
    text = re.sub(r'(\d)\s+(\"[a-z_]+"?\s*:)', r"\1, \2", text)
    # Fix missing comma between array elements: } {
    text = re.sub(r"(\})\s*\n\s*(\{)", r"\1,\n\2", text)
    # Fix missing comma after ] or } before "key":
    text = re.sub(r'(\]|\})\s*\n\s*(\"[a-z_]+"?\s*:)', r"\1,\n\2", text)

    # Fix 2: Trailing commas before closing brackets
    text = re.sub(r",\s*\]", "]", text)
    text = re.sub(r",\s*\}", "}", text)

    # Fix 3: Truncated JSON — balance brackets/braces
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    if open_braces > 0 or open_brackets > 0:
        # Try to close unclosed structures
        text = text.rstrip().rstrip(",")
        text += "]" * open_brackets + "}" * open_braces

    return text


def parse_extraction_response(response_text: str) -> Dict[str, Any]:
    """
    Parse LLM extraction response into structured data.

    Includes repair logic for common LLM JSON generation errors:
    missing commas, trailing commas, and truncated responses.

    Args:
        response_text: Raw LLM response (should be JSON)

    Returns:
        Parsed dict with concepts, relationships

    Raises:
        ValueError: If response is not valid JSON even after repair
    """
    import json

    text = _strip_markdown_fences(response_text)

    # Try strict parse first
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Attempt repair and retry
        repaired = _repair_json(text)
        try:
            data = json.loads(repaired)
            import structlog

            structlog.get_logger(__name__).warning(
                "extraction_json_repaired",
                original_length=len(text),
                repaired_length=len(repaired),
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in extraction response: {e}")

    # Validate structure
    if not isinstance(data, dict):
        raise ValueError("Extraction response must be a JSON object")

    # Ensure required keys exist with defaults
    return {
        "concepts": data.get("concepts", []),
        "relationships": data.get("relationships", []),
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
