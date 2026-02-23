"""
Prompts for question generation.

Generates follow-up questions based on:
- Selected strategy (loaded from methodology config)
- Active signals with their descriptions
- Current graph state (what we know so far)
- Recent conversation context
- Focus concept (what to ask about)

Strategy definitions are loaded from methodology YAML configs.
"""

from typing import Optional, List, Dict, Any
import structlog

from src.domain.models.methodology_schema import MethodologySchema
from src.methodologies import get_registry

log = structlog.get_logger(__name__)


def get_question_system_prompt(
    strategy: str = "deepen",
    topic: Optional[str] = None,
    methodology: Optional[MethodologySchema] = None,
) -> str:
    """
    Get system prompt for question generation.

    Args:
        strategy: Strategy name (e.g., deepen, explore, clarify, reflect, revitalize)
                  - must match methodology config
        topic: Research topic to anchor questions to (prevents drift)
        methodology: Optional methodology schema for method-specific context

    Returns:
        System prompt string
    """
    # Load strategy from methodology config
    methodology_name = (
        methodology.method["name"] if methodology and methodology.method else "means_end_chain"
    )
    registry = get_registry()
    try:
        config = registry.get_methodology(methodology_name)
        strategy_config = next((s for s in config.strategies if s.name == strategy), None)
        if strategy_config:
            strat_name = strategy.replace("_", " ").title()
            strat_description = strategy_config.description
        else:
            # Fallback to strategy name
            strat_name = strategy.replace("_", " ").title()
            strat_description = ""
    except Exception:
        # Fallback on error
        strat_name = strategy.replace("_", " ").title()
        strat_description = ""

    # Build methodology section
    methodology_section = ""
    if methodology and methodology.method:
        method_info = methodology.method
        method_name = method_info.get("name", "qualitative interview")
        method_goal = method_info.get("goal", "")
        method_desc = method_info.get("description", "")

        methodology_section = f"\n\nMethod: {method_name}"
        if method_desc:
            methodology_section += f"\n{method_desc}"
        if method_goal:
            methodology_section += f"\nGoal: {method_goal}"

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

Your current strategy is: **{strat_name}**
Strategy: {strat_description}{methodology_section}

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
    signals: Optional[Dict[str, Any]] = None,
    signal_descriptions: Optional[Dict[str, str]] = None,
    methodology: Optional[MethodologySchema] = None,
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
        signals: Active signal values dict (signal_name -> value)
        signal_descriptions: Signal descriptions dict (signal_name -> description)
        methodology: Optional methodology schema for method-specific context

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

    # Build signal rationale section (inline formatting - Option B)
    if signals and signal_descriptions:
        signal_lines = ["## Active Signals:"]
        for signal_name, value in signals.items():
            description = signal_descriptions.get(signal_name, "")
            if description:
                signal_lines.append(f"- {signal_name}: {value}")
                signal_lines.append(f'  → "{description}"')
            else:
                signal_lines.append(f"- {signal_name}: {value}")

        # Add "Why This Strategy" section
        signal_lines.append("")
        signal_lines.append("## Why This Strategy Was Selected:")
        signal_lines.append(_build_strategy_rationale(signals, strategy))

        prompt_parts.append("\n".join(signal_lines))
        prompt_parts.append("")

    # Add focus and strategy
    # Load strategy description from methodology config
    methodology_name = (
        methodology.method["name"] if methodology and methodology.method else "means_end_chain"
    )
    registry = get_registry()
    try:
        config = registry.get_methodology(methodology_name)
        strategy_config = next((s for s in config.strategies if s.name == strategy), None)
        if strategy_config:
            strat_name = strategy.replace("_", " ").title()
            strat_description = strategy_config.description
        else:
            strat_name = strategy.replace("_", " ").title()
            strat_description = ""
    except Exception:
        strat_name = strategy.replace("_", " ").title()
        strat_description = ""

    prompt_parts.append(f"Focus concept: {focus_concept}")
    if strat_description:
        prompt_parts.append(f"Strategy: {strat_name} - {strat_description}")
    else:
        prompt_parts.append(f"Strategy: {strat_name}")

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


def _build_strategy_rationale(signals: Dict[str, Any], strategy: str) -> str:
    """Build explanation of why this strategy was selected based on active signals.

    Args:
        signals: Active signal values
        strategy: Selected strategy ID

    Returns:
        Formatted rationale string
    """
    rationale_parts = []

    # Common signal-based rationales
    if "graph.max_depth" in signals:
        depth = signals["graph.max_depth"]
        if depth < 2:
            rationale_parts.append("- Low depth suggests we're still at surface level")
        elif depth >= 4:
            rationale_parts.append("- High depth indicates we've reached deep values")

    if "graph.chain_completion.has_complete" in signals:
        has_chain = signals["graph.chain_completion.has_complete"]
        if not has_chain:
            rationale_parts.append("- No complete chains exist - need to reach terminal values")

    if "llm.response_depth" in signals:
        resp_depth = signals["llm.response_depth"]
        if resp_depth == "surface":
            rationale_parts.append("- Surface-level response suggests need for deeper probing")
        elif resp_depth == "deep":
            rationale_parts.append("- Deep response indicates strong engagement")

    if "llm.hedging_language" in signals:
        hedging = signals["llm.hedging_language"]
        if hedging in ["medium", "high"]:
            rationale_parts.append(f"- Hedging language ({hedging}) suggests uncertainty")
        elif hedging in ["none", "low"]:
            rationale_parts.append("- Confident response with low uncertainty")

    # Strategy rationale (description already in system/user prompt from YAML)
    rationale_parts.append(f"- Strategy: {strategy}")

    if not rationale_parts:
        return f"Selected {strategy} strategy based on current state"

    return "\n".join(rationale_parts)


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
    opening_bias = method_info.get("opening_bias", "Elicit concrete, experience-based responses.")

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
