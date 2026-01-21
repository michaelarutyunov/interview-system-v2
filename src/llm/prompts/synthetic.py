"""
Prompts for synthetic respondent generation.

Generates contextually appropriate respondent answers for testing:
- Persona system with 5 predefined personas
- Natural response patterns (detailed, medium, brief, deflections)
- Interview context awareness (previous concepts, turn number, coverage)
- Deflection patterns for authentic respondent behavior

Used by:
- SyntheticService for generating synthetic responses
- Test scripts for automated regression testing
"""

from typing import Dict, Any, List, Optional


# Persona definitions with traits and speech patterns
PERSONAS: Dict[str, Dict[str, Any]] = {
    "health_conscious": {
        "name": "Health-Conscious Millennial",
        "traits": [
            "prioritizes health and wellness",
            "reads nutrition labels carefully",
            "values organic and natural ingredients",
            "avoids artificial additives and preservatives",
            "willing to pay more for health benefits"
        ],
        "speech_pattern": (
            "Uses health-related terminology (nutrients, ingredients, wellness), "
            "focuses on how products affect their body and long-term health, "
            "mentions specific health concerns or goals"
        )
    },
    "price_sensitive": {
        "name": "Budget-Conscious Shopper",
        "traits": [
            "compares prices across brands",
            "looks for sales and discounts",
            "prioritizes value over premium features",
            "budget-conscious but not cheap",
            "seeks cost-effective alternatives"
        ],
        "speech_pattern": (
            "Mentions price, value, deals, and budget considerations, "
            "compares costs and benefits, talks about getting the most for their money, "
            "references shopping around for better prices"
        )
    },
    "convenience_seeker": {
        "name": "Busy Professional",
        "traits": [
            "values time over cost",
            "prioritizes convenience and ease of use",
            "seeks quick and simple solutions",
            "often on-the-go or multi-tasking",
            "appreciates grab-and-go options"
        ],
        "speech_pattern": (
            "Focuses on convenience, time-saving, and simplicity, "
            "mentions busy schedule and need for quick solutions, "
            "values products that fit into their fast-paced lifestyle"
        )
    },
    "quality_focused": {
        "name": "Quality Enthusiast",
        "traits": [
            "appreciates premium quality and craftsmanship",
            "values superior taste and experience",
            "seeks the best products regardless of price",
            "knowledgeable about product characteristics",
            "enjoys discovering and trying premium options"
        ],
        "speech_pattern": (
            "Uses descriptive language about taste, texture, and quality, "
            "appreciates nuanced differences between products, "
            "values authenticity and craftsmanship, mentions premium aspects"
        )
    },
    "sustainability_minded": {
        "name": "Environmentally Conscious Consumer",
        "traits": [
            "prioritizes environmental impact",
            "values sustainable packaging and sourcing",
            "willing to pay more for eco-friendly options",
            "researches company ethics and practices",
            "makes choices based on carbon footprint"
        ],
        "speech_pattern": (
            "Focuses on sustainability, environmental impact, and ethics, "
            "mentions packaging, sourcing, and company values, "
            "talks about making a difference through consumer choices"
        )
    },
}


def get_synthetic_system_prompt() -> str:
    """
    Get system prompt for synthetic respondent generation.

    Returns:
        System prompt string for LLM
    """
    return """You are a synthetic respondent for testing an adaptive interview system.

Generate natural, realistic responses to interview questions about products and consumer preferences.

## Response Guidelines:
1. Be conversational and natural - like a real person in an interview
2. Vary your response length (some brief, some detailed, most medium-length)
3. Express authentic opinions and preferences
4. Use the persona's traits and speech patterns to guide your responses
5. Feel comfortable with simple acknowledgments or brief answers
6. Don't always provide elaborate explanations - sometimes short answers are natural

## Response Patterns:
- **Detailed responses**: 2-3 sentences sharing thoughts and reasons (40% of responses)
- **Medium responses**: 1-2 sentences with some explanation (40% of responses)
- **Brief responses**: Short phrases or simple answers (15% of responses)
- **Acknowledgments**: "Okay", "I see", "That makes sense" (5% of responses)

## What to Avoid:
- Don't be overly helpful or eager to please
- Don't provide textbook-perfect "laddering" responses
- Don't always give detailed explanations when a brief answer feels natural
- Don't sound like a focus group participant trying to be helpful
- Don't repeat back the interviewer's language perfectly

Remember: Real people are sometimes brief, sometimes detailed, sometimes distracted. Be authentic."""


def get_synthetic_system_prompt_with_deflection() -> str:
    """
    Get system prompt with deflection guidance.

    Adds instructions for including deflection patterns to simulate
    authentic respondent behavior where they redirect the conversation.

    Returns:
        System prompt string with deflection guidance
    """
    base_prompt = get_synthetic_system_prompt()

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
        persona: Persona ID from PERSONAS dict
        previous_concepts: Optional list of concepts mentioned earlier
        interview_context: Optional dict with product_name, turn_number, coverage_achieved

    Returns:
        User prompt string
    """
    # Get persona configuration
    persona_config = PERSONAS.get(persona, PERSONAS["health_conscious"])

    prompt_parts = []

    # Add persona configuration
    prompt_parts.append(f"## Your Persona: {persona_config['name']} ({persona})")
    prompt_parts.append(f"Traits: {', '.join(persona_config['traits'])}")
    prompt_parts.append(f"Speech Pattern: {persona_config['speech_pattern']}")
    prompt_parts.append("")

    # Add previous concepts if provided
    if previous_concepts:
        # Show last 5 concepts
        recent_concepts = previous_concepts[-5:]
        prompt_parts.append(f"## Concepts already mentioned:")
        prompt_parts.append(f"{', '.join(recent_concepts)}")
        prompt_parts.append("")

    # Add interview context if provided
    if interview_context:
        prompt_parts.append("## Interview Context:")
        product_name = interview_context.get("product_name", "this product")
        turn_number = interview_context.get("turn_number", 1)
        coverage = interview_context.get("coverage_achieved", 0.0)

        prompt_parts.append(f"- Product: {product_name}")
        prompt_parts.append(f"- turn {turn_number}")
        prompt_parts.append(f"- {coverage*100:.0f}% coverage")
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

    Returns:
        Dict mapping persona_id to persona_name
    """
    return {
        persona_id: config["name"]
        for persona_id, config in PERSONAS.items()
    }
