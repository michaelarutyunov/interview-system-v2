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
    methodology: MethodologySchema,
    strategy: str = "ascend",
    topic: Optional[str] = None,
) -> str:
    """
    Get system prompt for question generation.

    Args:
        methodology: Methodology schema for method-specific context (required)
        strategy: Strategy name (e.g., ascend, ground, bridge, branch, anchor, revitalize)
                  - must match methodology config
        topic: Research topic to anchor questions to (prevents drift)

    Returns:
        System prompt string

    Raises:
        ValueError: If methodology.method is None
    """
    # Load strategy from methodology config - fail fast if missing
    if methodology.method is None:
        raise ValueError("MethodologySchema.method is required but is None")
    methodology_name = methodology.method["name"]
    registry = get_registry()
    config = registry.get_methodology(methodology_name)
    strategy_config = next((s for s in config.strategies if s.name == strategy), None)
    if strategy_config:
        strat_name = strategy.replace("_", " ").title()
        strat_description = strategy_config.description
    else:
        strat_name = strategy.replace("_", " ").title()
        strat_description = ""

    # Build methodology section - method already validated above
    method_info = methodology.method
    assert method_info is not None  # for type checker
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
8. Do not presuppose the level of abstraction — never add "as a person", "to your identity", or "in your life" unless the respondent used those words first

## Examples:
- BAD: "Beyond what you mentioned about X, what else might Y be in terms of Z?"
- GOOD: "What else does coffee do for you?"
- BAD: "When you think about being reliable through your daily routine, why does that matter?"
- GOOD: "Why does having that routine matter to you?"
{topic_instruction}
## Output:
Before outputting your final question:
1. Generate 3 distinct candidate questions that follow the strategy
2. Score each silently: clarity (1-5), strategy_fit (1-5), naturalness (1-5)×2, topic_anchor (1-5), focus_fit (1-5)×3
3. Select the highest-scoring candidate
4. Output ONLY the selected question — no candidates, no scores, no explanation"""


# Simple prompt: Generate ONLY the question - no explanations, no quotation marks, just the question itself.
def get_question_user_prompt(
    focus_concept: str,
    methodology: MethodologySchema,
    recent_utterances: Optional[List[Dict[str, str]]] = None,
    graph_summary: Optional[str] = None,
    strategy: str = "ascend",
    topic: Optional[str] = None,
    depth_achieved: int = 0,
    signals: Optional[Dict[str, Any]] = None,
    signal_descriptions: Optional[Dict[str, str]] = None,
    focus_node_type: Optional[str] = None,
    focus_node_level: Optional[int] = None,
) -> str:
    """
    Get user prompt for question generation.

    Args:
        focus_concept: Concept to focus the question on
        methodology: Methodology schema for method-specific context
        recent_utterances: Recent conversation turns [{"speaker": "user/system", "text": "..."}]
        graph_summary: Summary of what we know so far
        strategy: Strategy name
        topic: Research topic to anchor questions to (prevents drift)
        depth_achieved: Current depth in the conversation (0-4+)
        signals: Active signal values dict (signal_name -> value)
        signal_descriptions: Signal descriptions dict (signal_name -> description)
        focus_node_type: Methodology node type of focus concept (e.g., 'attribute',
            'functional_consequence') — helps the LLM tailor question phrasing
        focus_node_level: Ontology level of the focus node type (e.g., 0-4) —
            helps the LLM understand what level to target next

    Returns:
        User prompt string
    """
    prompt_parts = []

    # ── Section 1: Focus concept + strategy (FIRST — primacy) ──

    # Load strategy description from methodology config
    if methodology.method is None:
        raise ValueError("MethodologySchema.method is required but is None")
    methodology_name = methodology.method["name"]
    registry = get_registry()
    config = registry.get_methodology(methodology_name)
    strategy_config = next((s for s in config.strategies if s.name == strategy), None)
    if strategy_config:
        strat_name = strategy.replace("_", " ").title()
        strat_description = strategy_config.description
    else:
        strat_name = strategy.replace("_", " ").title()
        strat_description = ""

    # Build level info for the focus node
    level_info = ""
    if focus_node_level is not None and focus_node_type and methodology.ontology:
        max_level = max(
            (nt.level for nt in methodology.ontology.nodes if nt.level is not None),
            default=4,
        )
        if focus_node_level < max_level:
            level_info = (
                f" (ontology level L{focus_node_level}, "
                f"target L{focus_node_level + 1}–L{max_level})"
            )
        elif focus_node_level == max_level:
            level_info = f" (ontology level L{focus_node_level} — terminal, already at chain end)"

    # Constraint — tells the LLM the focus concept is non-negotiable
    if focus_node_type:
        prompt_parts.append(
            f"Your question MUST be about this concept: \"{focus_concept}\" "
            f"(type: {focus_node_type}){level_info}."
        )
    else:
        prompt_parts.append(
            f"Your question MUST be about this concept: \"{focus_concept}\"."
        )
    prompt_parts.append(
        "The respondent's answer below provides context — use it to phrase "
        "the question naturally, but the question's primary subject must be "
        "the focus concept above."
    )
    prompt_parts.append(f"Strategy: {strat_name} — {strat_description}")
    prompt_parts.append("")

    # ── Section 2: Recent conversation (reference, not primary signal) ──

    # Add topic context if provided
    if topic:
        prompt_parts.append(f"Research topic: {topic}")
        prompt_parts.append("")

    if recent_utterances:
        context_lines = []
        for utt in recent_utterances[-5:]:  # Last 5 turns
            speaker = "Respondent" if utt.get("speaker") == "user" else "Interviewer"
            context_lines.append(f"{speaker}: {utt['text']}")

        prompt_parts.append("Recent conversation (use as context, not as the question subject):")
        prompt_parts.append("\n".join(context_lines))
        prompt_parts.append("")

    # ── Section 3: Supplementary context ──

    if graph_summary:
        prompt_parts.append(f"What we know so far: {graph_summary}")
        prompt_parts.append("")

    # ── Section 4: Active signals (compact — only values, no rationale) ──

    if signals and signal_descriptions:
        signal_lines = ["## Active Signals:"]
        for signal_name, value in signals.items():
            signal_lines.append(f"- {signal_name}: {value}")
        prompt_parts.append("\n".join(signal_lines))
        prompt_parts.append("")

    # ── Section 5: Strategy-specific notes ──

    # Add topic anchoring reminder when depth is high
    if topic and depth_achieved >= 2:
        prompt_parts.append(
            f"IMPORTANT: We're deep in the conversation. Your question MUST reference "
            f"the respondent's specific experience with {topic}, not abstract life philosophy. "
            f"Ask how {topic} connects to the value they just expressed — not why the value matters in general."
        )
        prompt_parts.append("")

    if strategy == "revitalize":
        prompt_parts.append(
            "Note: The conversation history above includes the opening question. "
            "Your revitalize question must explore a DIFFERENT aspect or domain "
            "that has not yet been discussed — do not repeat or rephrase questions already asked."
        )
        prompt_parts.append("")

    # ── Final instruction (recency — reinforces focus constraint) ──

    prompt_parts.append(
        f"Generate a natural follow-up question about \"{focus_concept}\":"
    )

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
