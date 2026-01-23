"""
Prompts for question generation.

Generates follow-up questions based on:
- Selected strategy (deepen, broaden, cover, close)
- Current graph state (what we know so far)
- Recent conversation context
- Focus concept (what to ask about)

Phase 2: Hardcoded "deepen" strategy.
Phase 3: Full strategy selection.
"""

from typing import Optional, List, Dict


# Strategy descriptions for prompts
STRATEGY_DESCRIPTIONS = {
    "deepen": {
        "name": "Deepen",
        "intent": "Explore why something matters to understand deeper motivations",
        "probe_style": "Ask 'why is that important?' type questions",
        "example": "You mentioned {concept} - why is that important to you?",
    },
    "broaden": {
        "name": "Broaden",
        "intent": "Find new branches and related concepts",
        "probe_style": "Ask 'what else?' type questions",
        "example": "Besides {concept}, what else matters to you about this?",
    },
    "cover": {
        "name": "Cover",
        "intent": "Explore untouched stimulus elements",
        "probe_style": "Introduce new topic naturally",
        "example": "I'd like to hear your thoughts about {element}...",
    },
    "close": {
        "name": "Close",
        "intent": "Wrap up the interview naturally",
        "probe_style": "Summarize and invite final thoughts",
        "example": "We've covered a lot - is there anything else you'd like to add?",
    },
}


def get_question_system_prompt(strategy: str = "deepen") -> str:
    """
    Get system prompt for question generation.

    Args:
        strategy: Strategy name (deepen, broaden, cover, close)

    Returns:
        System prompt string
    """
    strat = STRATEGY_DESCRIPTIONS.get(strategy, STRATEGY_DESCRIPTIONS["deepen"])

    return f"""You are a skilled qualitative researcher conducting an interview using the Means-End Chain methodology.

Your current strategy is: **{strat['name']}**
Strategy intent: {strat['intent']}
Probe style: {strat['probe_style']}

## Interview Guidelines:
1. Ask ONE question at a time
2. Use the respondent's own language and concepts
3. Be warm, curious, and non-judgmental
4. Questions should feel natural and conversational
5. Avoid leading questions - stay open-ended
6. Reference what the respondent said to show you're listening

## Means-End Chain Methodology:
- Start with concrete Attributes (product features)
- Probe toward Functional Consequences (what it does)
- Move to Psychosocial Consequences (how it makes them feel)
- Ultimately reach Values (why it matters deeply)

The typical "laddering" question is: "Why is that important to you?"

## Output:
Generate ONLY the question - no explanations, no quotation marks, just the question itself."""


def get_question_user_prompt(
    focus_concept: str,
    recent_utterances: Optional[List[Dict[str, str]]] = None,
    graph_summary: Optional[str] = None,
    strategy: str = "deepen",
) -> str:
    """
    Get user prompt for question generation.

    Args:
        focus_concept: Concept to focus the question on
        recent_utterances: Recent conversation turns [{"speaker": "user/system", "text": "..."}]
        graph_summary: Summary of what we know so far
        strategy: Strategy name

    Returns:
        User prompt string
    """
    prompt_parts = []

    # Add recent conversation context
    if recent_utterances:
        context_lines = []
        for utt in recent_utterances[-5:]:  # Last 5 turns
            speaker = "Respondent" if utt.get("speaker") == "user" else "Interviewer"
            context_lines.append(f"{speaker}: {utt['text']}")

        prompt_parts.append("Recent conversation:")
        prompt_parts.append("\n".join(context_lines))
        prompt_parts.append("")

    # Add graph summary if available
    if graph_summary:
        prompt_parts.append(f"What we know so far: {graph_summary}")
        prompt_parts.append("")

    # Add focus and strategy
    strat = STRATEGY_DESCRIPTIONS.get(strategy, STRATEGY_DESCRIPTIONS["deepen"])
    prompt_parts.append(f"Focus concept: {focus_concept}")
    prompt_parts.append(f"Strategy: {strat['name']} - {strat['intent']}")
    prompt_parts.append("")
    prompt_parts.append("Generate a natural follow-up question:")

    return "\n".join(prompt_parts)


def get_opening_question_system_prompt() -> str:
    """
    Get system prompt for generating opening questions.

    Returns:
        System prompt string
    """
    return """You are starting a qualitative research interview about a product or concept.

Your goal is to warmly invite the participant to share their initial thoughts.

## Guidelines:
1. Be friendly and put the respondent at ease
2. Ask about their general thoughts, experiences, or associations
3. Keep it open-ended - don't assume anything
4. Use simple, conversational language
5. One question only

## Output:
Generate ONLY the opening question - no explanations, no quotation marks."""


def get_opening_question_user_prompt(concept_name: str, description: str = "") -> str:
    """
    Get user prompt for generating opening question.

    Args:
        concept_name: Name of the concept/product being discussed
        description: Optional description of the concept

    Returns:
        User prompt string
    """
    prompt = f"Generate an opening question about: {concept_name}"

    if description:
        prompt += f"\n\nProduct description: {description}"

    prompt += "\n\nGenerate a warm, open-ended opening question:"

    return prompt


def get_graph_summary(
    nodes_by_type: Dict[str, int],
    recent_concepts: List[str],
    depth_achieved: int,
) -> str:
    """
    Generate a brief graph summary for context.

    Args:
        nodes_by_type: Count of nodes by type
        recent_concepts: Recently discussed concepts
        depth_achieved: How deep we've gone in the chain

    Returns:
        Brief summary string
    """
    parts = []

    # Depth progress
    depth_labels = ["starting", "surface", "developing", "deep", "very deep"]
    depth_label = depth_labels[min(depth_achieved, len(depth_labels) - 1)]
    parts.append(f"Depth: {depth_label}")

    # What we've covered
    total_nodes = sum(nodes_by_type.values())
    if total_nodes > 0:
        parts.append(f"Explored {total_nodes} concepts")

    # Recent focus
    if recent_concepts:
        recent = ", ".join(recent_concepts[:3])
        parts.append(f"Recent topics: {recent}")

    return " | ".join(parts)


def format_question(raw_question: str) -> str:
    """
    Clean up generated question.

    Args:
        raw_question: Raw LLM output

    Returns:
        Cleaned question string
    """
    question = raw_question.strip()

    # Remove surrounding quotes if present
    if question.startswith('"') and question.endswith('"'):
        question = question[1:-1]
    if question.startswith("'") and question.endswith("'"):
        question = question[1:-1]

    # Ensure ends with question mark or appropriate punctuation
    if question and question[-1] not in ".?!":
        question += "?"

    return question
