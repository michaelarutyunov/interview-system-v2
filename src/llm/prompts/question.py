"""
Prompts for question generation.

Generates follow-up questions based on:
- Selected strategy (deepen, broaden, cover_element, closing, reflection,
                  bridge, contrast, ease, synthesis)
- Current graph state (what we know so far)
- Recent conversation context
- Focus concept (what to ask about)

Strategy definitions are loaded from config/scoring.yaml.
"""

from typing import Optional, List, Dict, Any

from src.domain.models.methodology_schema import MethodologySchema


# Strategy descriptions for prompts
# Note: Keys must match strategy.id values in config/scoring.yaml
STRATEGY_DESCRIPTIONS = {
    "deepen": {
        "name": "Deepen Understanding",
        "intent": "Explore why something matters to understand deeper motivations",
        "probe_style": "Ask 'why is that important?' type questions",
        "example": "You mentioned {concept} - why is that important to you?",
    },
    "broaden": {
        "name": "Explore Breadth",
        "intent": "Find new branches and related concepts",
        "probe_style": "Ask 'what else?' type questions",
        "example": "Besides {concept}, what else matters to you about this?",
    },
    "cover_element": {
        "name": "Cover Stimulus Element",
        "intent": "Explore untouched stimulus elements",
        "probe_style": "Introduce new topic naturally",
        "example": "I'd like to hear your thoughts about {element}...",
    },
    "closing": {
        "name": "Closing Interview",
        "intent": "Wrap up the interview naturally",
        "probe_style": "Summarize and invite final thoughts",
        "example": "We've covered a lot - is there anything else you'd like to add?",
    },
    "reflection": {
        "name": "Reflection / Meta-Question",
        "intent": "Ask a meta-question about the interview process or experience",
        "probe_style": "Step back and reflect on the conversation",
        "example": "How has this conversation been for you so far?",
    },
    "bridge": {
        "name": "Lateral Bridge to Peripheral",
        "intent": "Link to what was just said, then gently shift to a related area",
        "probe_style": "Acknowledge their point, then explore a connected topic",
        "example": "That's interesting about X. Have you also noticed anything about Y?",
    },
    "contrast": {
        "name": "Introduce Counter-Example",
        "intent": "Politely introduce a counter-example to test boundaries",
        "probe_style": "Gently challenge with an opposite case",
        "example": "That makes sense. Have you ever experienced the opposite - where X?",
    },
    "ease": {
        "name": "Ease / Rapport Repair",
        "intent": "Simplify or soften the question to encourage participation",
        "probe_style": "Make the question easier to answer",
        "example": "Let me put this more simply - what do you think about X?",
    },
    "synthesis": {
        "name": "Summarise & Invite Extension",
        "intent": "Briefly summarize what you've heard and invite correction or addition",
        "probe_style": "Reflect back and ask for more",
        "example": "So far I've heard X and Y. Is that right, or is there more to add?",
    },
    "clarify": {
        "name": "Clarify / Rephrase",
        "intent": "Rephrase the previous question when user shows confusion or lack of understanding",
        "probe_style": "Ask the same thing in simpler, clearer words",
        "example": "Let me put this more simply - what do you think about {concept}?",
    },
}


def get_question_system_prompt(
    strategy: str = "deepen", topic: Optional[str] = None
) -> str:
    """
    Get system prompt for question generation.

    Args:
        strategy: Strategy name (deepen, broaden, cover_element, closing, reflection,
                      bridge, contrast, ease, synthesis) - must match config/scoring.yaml
        topic: Research topic to anchor questions to (prevents drift)

    Returns:
        System prompt string
    """
    strat = STRATEGY_DESCRIPTIONS.get(strategy, STRATEGY_DESCRIPTIONS["deepen"])

    # Build topic anchoring instruction if topic provided
    topic_instruction = ""
    if topic:
        topic_instruction = f"""
## Topic Anchoring:
This interview is about **{topic}**. While exploring deeper motivations and values,
ensure questions remain connected to the respondent's experience with {topic}.
If the conversation drifts too far into abstract philosophy, gently relate back to {topic}.
"""

    return f"""You are a skilled qualitative researcher conducting an interview.

Your current strategy is: **{strat["name"]}**
Strategy intent: {strat["intent"]}
Probe style: {strat["probe_style"]}

## Question Style Guidelines:
1. Ask ONE question at a time
2. **Keep questions UNDER 15 WORDS** when possible
3. Use simple, everyday language
4. Be direct - avoid nested clauses and complex phrasing
5. Use the respondent's own words when referencing what they said
6. Be warm, curious, and non-judgmental
7. Avoid leading questions - stay open-ended

## Examples:
- BAD: "Beyond what you mentioned about X, what else might Y be in terms of Z?"
- GOOD: "What else does coffee do for you?"
- BAD: "When you think about being reliable through your daily routine, why does that matter?"
- GOOD: "Why does having that routine matter to you?"
{topic_instruction}
## Output:
Generate ONLY the question - no explanations, no quotation marks, just the question itself."""


def get_question_user_prompt(
    focus_concept: str,
    recent_utterances: Optional[List[Dict[str, str]]] = None,
    graph_summary: Optional[str] = None,
    strategy: str = "deepen",
    topic: Optional[str] = None,
    depth_achieved: int = 0,
) -> str:
    """
    Get user prompt for question generation.

    Args:
        focus_concept: Concept to focus the question on
        recent_utterances: Recent conversation turns [{"speaker": "user/system", "text": "..."}]
        graph_summary: Summary of what we know so far
        strategy: Strategy name
        topic: Research topic to anchor questions to (prevents drift)
        depth_achieved: Current depth in the conversation (0-4+)

    Returns:
        User prompt string
    """
    prompt_parts = []

    # Add topic context if provided
    if topic:
        prompt_parts.append(f"Research topic: {topic}")
        prompt_parts.append("")

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

    # Add topic anchoring reminder when depth is high (prevents drift to abstract philosophy)
    if topic and depth_achieved >= 2:
        prompt_parts.append("")
        prompt_parts.append(
            f"Note: We're deep in the conversation. Keep the question connected to {topic} - "
            "explore values through the lens of their specific experience, not generic life philosophy."
        )

    prompt_parts.append("")
    prompt_parts.append("Generate a natural follow-up question:")

    return "\n".join(prompt_parts)


def get_opening_question_system_prompt(
    methodology: Optional[MethodologySchema] = None,
) -> str:
    """
    Get system prompt for generating opening questions.

    Args:
        methodology: Optional methodology schema for method-specific guidance

    Returns:
        System prompt string
    """
    base_prompt = """You are an experienced qualitative moderator starting an in-depth interview.

Your goal is to warmly invite the participant to share their initial thoughts.

## Guidelines:
1. Be friendly and put the respondent at ease
2. Ask about their general thoughts, experiences, or associations
3. Keep it open-ended - don't assume anything
4. Use simple, conversational language
5. One question only

## Output:
Generate ONLY the opening question - no explanations, no quotation marks."""

    # Add methodology-specific guidance if provided
    if methodology and methodology.method:
        method_info = methodology.method
        name = method_info.get("name", "qualitative interview")
        goal = method_info.get("goal", "")

        methodology_guidance = f"""

## Methodology Context:
You are using the **{name}** method"""

        if goal:
            methodology_guidance += f"\nMethod goal: {goal}"

        base_prompt = methodology_guidance + "\n\n" + base_prompt

    return base_prompt


def get_opening_question_user_prompt(
    objective: str, methodology: Optional[MethodologySchema] = None
) -> str:
    """Generate opening question with methodology context.

    Args:
        objective: Interview objective (what we're studying)
        methodology: Optional methodology schema for method-specific guidance

    Returns:
        User prompt string
    """
    # Extract methodology information if provided
    method_info: Dict[str, Any] = {}
    if methodology and methodology.method:
        method_info = methodology.method

    name = method_info.get("name", "qualitative interview")
    goal = method_info.get("goal", "understand user experiences")
    opening_bias = method_info.get(
        "opening_bias", "Elicit concrete, experience-based responses."
    )

    return f"""You are an experienced qualitative moderator starting an in-depth interview.

**Interview objective (for you):**
{objective}

**Methodology (for you):**
{name}: {goal}

**Method-specific opening guidance:**
{opening_bias}

**Your task:**
- Briefly and naturally frame the topic for the respondent
- Ask an opening question that fits the methodology
- Prefer concrete, experience-based responses over abstract opinions
- Keep it conversational

**Generate only what the moderator would say to the respondent:**"""


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
