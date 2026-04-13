"""
Prompts for synthetic respondent generation.

Generates contextually appropriate respondent answers for testing:
- Persona system loaded from config/personas/*.yaml
- Natural response patterns (detailed, medium, brief, deflections)
- Interview context awareness (previous concepts, turn number)
- Deflection patterns for authentic respondent behavior

Used by:
- SyntheticService for generating synthetic responses
- Test scripts for automated regression testing

Migration (2026-01-29):
- Personas loaded from config/personas/*.yaml via persona_loader
- Legacy PERSONAS dict removed after migration verification
"""

from typing import Dict, Any, List, Optional

# Import persona loader
from src.core.persona_loader import load_persona, list_personas as load_list_personas



def get_synthetic_system_prompt(
    response_patterns: Optional[Dict[str, float]] = None,
) -> str:
    """
    Get system prompt for synthetic respondent generation.

    Args:
        response_patterns: Optional dict of response type probabilities from persona YAML.

    Returns:
        System prompt string for LLM
    """
    defaults = {"detailed": 0.40, "medium": 0.40, "brief": 0.15, "acknowledgment": 0.05}
    patterns = response_patterns or defaults

    brief_pct = int(patterns.get("brief", defaults["brief"]) * 100)
    medium_pct = int(patterns.get("medium", defaults["medium"]) * 100)
    detailed_pct = int(patterns.get("detailed", defaults["detailed"]) * 100)
    ack_pct = int(patterns.get("acknowledgment", defaults["acknowledgment"]) * 100)

    return f"""You are simulating a real person responding to interview questions in a text-only chat.

## Response Length (hard limits — stay within these):
- **Brief** ({brief_pct}% of responses): 10–25 words. One fragment or short statement. No explanation needed.
- **Medium** ({medium_pct}% of responses): 25–60 words. One idea, maybe a quick example. Stop there.
- **Detailed** ({detailed_pct}% of responses): 60–100 words. Two ideas at most. Never a structured paragraph.
- **Acknowledgment** ({ack_pct}% of responses): 2–8 words. "Yeah", "not really", "I guess so", "hmm not sure".

## Format rules (non-negotiable):
- No stage directions. Never write *pauses*, *thinks*, *shifts*, or any asterisk actions.
- No structured paragraphs. Chat messages are flat — just sentences.
- Don't introduce more than 2 distinct ideas per response. Circling one idea in different words is fine and realistic.
- Don't summarise or wrap up at the end. Just stop when the thought is done.
- Trailing off is fine: "I don't know, it's just kind of..." is a complete response.

## What to avoid:
- Textbook-complete answers that cover every angle of the question
- Sounding like a focus group participant performing helpfulness
- Perfect grammar and polished phrasing throughout
- Restating the interviewer's words back at them"""


def get_synthetic_system_prompt_with_deflection(
    response_patterns: Optional[Dict[str, float]] = None,
) -> str:
    """
    Get system prompt with deflection guidance.

    Adds instructions for including deflection patterns to simulate
    authentic respondent behavior where they redirect the conversation.

    Args:
        response_patterns: Optional dict of response type probabilities from persona YAML.

    Returns:
        System prompt string with deflection guidance
    """
    base_prompt = get_synthetic_system_prompt(response_patterns)

    deflection_guidance = """

## Deflection Patterns (use in ~20% of responses):
Sometimes real respondents deflect or redirect the conversation. Include deflections like:
- "That's okay, but what really matters to me is..."
- "I guess, but I'm more focused on..."
- "That's not really my main concern..."
- "I'd say it's more about..."
- "Not so much that, but I do care about..."

Use deflections to show what actually matters to the persona, not just what the interviewer asks about."""

    return base_prompt + deflection_guidance


def get_synthetic_user_prompt(
    question: str,
    persona: str,
    previous_concepts: Optional[List[str]] = None,
    interview_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Get user prompt for synthetic response generation.

    Args:
        question: The interviewer's question
        persona: Persona ID from config/personas/*.yaml
        previous_concepts: Optional list of concepts mentioned earlier
        interview_context: Optional dict with product_name, turn_number

    Returns:
        User prompt string
    """
    # Get persona configuration from YAML
    persona_config = load_persona(persona).model_dump()

    prompt_parts = []

    # Add persona configuration
    prompt_parts.append(f"## Your Persona: {persona_config['name']} ({persona})")
    prompt_parts.append(f"Traits: {', '.join(persona_config['traits'])}")
    prompt_parts.append(f"Speech Pattern: {persona_config['speech_pattern']}")

    # Add deflection patterns if available
    if persona_config.get("deflection_patterns"):
        prompt_parts.append(
            f"Deflection Patterns: {', '.join(persona_config['deflection_patterns'][:3])}"
        )

    prompt_parts.append("")

    # Add previous concepts if provided
    if previous_concepts:
        # Show last 5 concepts
        recent_concepts = previous_concepts[-5:]
        prompt_parts.append("## Concepts already mentioned:")
        prompt_parts.append(f"{', '.join(recent_concepts)}")
        prompt_parts.append("")

    # Add interview context if provided
    if interview_context:
        prompt_parts.append("## Interview Context:")
        product_name = interview_context.get("product_name", "this product")
        turn_number = interview_context.get("turn_number", 1)

        prompt_parts.append(f"- Product: {product_name}")
        prompt_parts.append(f"- Turn {turn_number}")
        prompt_parts.append("")

    # Add the question
    prompt_parts.append("## Interviewer's Question:")
    prompt_parts.append(question)
    prompt_parts.append("")
    prompt_parts.append("Generate your natural response as this persona:")

    return "\n".join(prompt_parts)


def parse_synthetic_response(response_text: str) -> str:
    """
    Clean LLM artifacts from synthetic response.

    Removes markdown quotes, response prefixes, and extra whitespace.

    Args:
        response_text: Raw LLM response

    Returns:
        Cleaned response string
    """
    # Strip whitespace
    text = response_text.strip()

    # Remove markdown quote wrapping (""")
    if text.startswith('"""'):
        text = text[3:]
    if text.endswith('"""'):
        text = text[:-3]
    text = text.strip()

    # Remove "Response:" prefix
    if text.lower().startswith("response:"):
        text = text[9:].strip()

    # Remove "Your response:" prefix
    if text.lower().startswith("your response:"):
        text = text[14:].strip()

    # Clean up any remaining extra whitespace
    text = " ".join(text.split())

    return text


def get_available_personas() -> Dict[str, str]:
    """
    Get dict of available personas.

    Loads from config/personas/*.yaml.

    Returns:
        Dict mapping persona_id to persona_name
    """
    return load_list_personas()
