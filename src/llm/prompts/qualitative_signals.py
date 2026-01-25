"""
Prompt templates for qualitative signal extraction.

These prompts guide LLM analysis of conversation history to extract
semantic signals that provide deeper insight than rule-based heuristics.

Design principles:
- Structured JSON output for parsing
- Clear classification boundaries
- Examples to ground expectations
- Minimal context to reduce cost/latency
"""

from typing import List, Dict, Any


def get_qualitative_signals_system_prompt() -> str:
    """Get system prompt for qualitative signal extraction.

    The LLM acts as an expert qualitative analyst examining interview
    transcripts for subtle signals of engagement, reasoning quality,
    and knowledge state.
    """
    return """You are an expert qualitative analyst examining interview transcripts.

Your task is to analyze recent conversation history and extract semantic signals that provide insight into:
1. The respondent's engagement level and emotional state
2. The quality and depth of their reasoning
3. The nature of any uncertainty expressed
4. Potential contradictions or knowledge ceiling signals

Focus on the LAST 3-5 user responses. Look for patterns across responses,
not just isolated statements.

Return your analysis as a JSON object with the following structure:

{
  "uncertainty_signal": {
    "uncertainty_type": "knowledge_gap|conceptual_clarity|confidence_qualification|epistemic_humility|apathy",
    "confidence": 0.0-1.0,
    "severity": 0.0-1.0,
    "examples": ["quote1", "quote2"],
    "reasoning": "brief explanation"
  },
  "reasoning_signal": {
    "reasoning_quality": "causal|counterfactual|associative|reactive|metacognitive",
    "confidence": 0.0-1.0,
    "depth_score": 0.0-1.0,
    "has_examples": true/false,
    "has_abstractions": true/false,
    "examples": ["quote1", "quote2"],
    "reasoning": "brief explanation"
  },
  "emotional_signal": {
    "intensity": "high_positive|moderate_positive|neutral|moderate_negative|high_negative",
    "confidence": 0.0-1.0,
    "trajectory": "rising|falling|stable|volatile",
    "markers": ["enthusiastic", "hesitant", "curious", etc.],
    "reasoning": "brief explanation"
  },
  "contradiction_signal": {
    "has_contradiction": true/false,
    "contradiction_type": "stance reversal|inconsistent detail|context shift|null",
    "earlier_statement": "exact quote or paraphrase",
    "current_statement": "exact quote or paraphrase",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
  },
  "knowledge_ceiling_signal": {
    "is_terminal": true/false,
    "response_type": "terminal|exploratory|transitional",
    "has_curiosity": true/false,
    "redirection_available": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
  },
  "concept_depth_signal": {
    "abstraction_level": 0.0-1.0,
    "has_concrete_examples": true/false,
    "has_abstract_principles": true/false,
    "suggestion": "deepen|broaden|stay",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
  }
}

Classification guidelines:

UNCERTAINTY TYPES:
- knowledge_gap: "I don't know enough about this topic area"
- conceptual_clarity: "I'm not sure what you're asking" or unclear about concept
- confidence_qualification: "I think", "probably", "maybe" - hedging but engaged
- epistemic_humility: "I could be wrong", acknowledging limits of knowledge
- apathy: "I don't know/care", disengaged, minimal effort

REASONING QUALITY:
- causal: Clear cause-effect relationships ("because X leads to Y")
- counterfactual: Considers alternatives ("if X were different", "one could also")
- associative: Loose connections, word associations without logical links
- reactive: Simple direct responses to questions without elaboration
- metacognitive: Reflects on own thinking process ("I'm realizing that...")

EMOTIONAL INTENSITY:
- high_positive: Enthusiasm, excitement ("love", "amazing", "!")
- moderate_positive: Interest, engagement, thoughtful responses
- neutral: Factual, calm, informational
- moderate_negative: Hesitation, discomfort, uncertainty
- high_negative: Frustration, hostility, disengagement

CONTRADICTION TYPES:
- stance reversal: Directly opposite position from earlier
- inconsistent detail: Details that don't align
- context shift: Position changed due to new context (may be valid)
- null: No contradiction detected

KNOWLEDGE CEILING:
- terminal: Hard stop, no more to explore, disengaged
- exploratory: "I don't know, but I'm curious about..."
- transitional: "I don't know about X, but I do know about Y"

CONCEPT DEPTH:
- abstraction_level: 0.0 (very concrete/specific) to 1.0 (very abstract/principled)
- suggestion: "deepen" if highly abstract, "broaden" if very concrete, "stay" if balanced

Return NULL for any signal that cannot be reliably assessed from the provided context."""


def get_qualitative_signals_user_prompt(
    conversation_history: List[Dict[str, Any]],
    turn_count: int,
) -> str:
    """Get user prompt for qualitative signal extraction.

    Args:
        conversation_history: Recent conversation turns (may include extraction metadata)
        turn_count: Current turn number (for context)

    Returns:
        Formatted prompt with conversation history
    """
    # Format conversation history
    formatted_history = _format_conversation_for_analysis(
        conversation_history, max_turns=10
    )

    return f"""Analyze the following conversation history from a qualitative research interview.

Current turn: {turn_count}

Recent conversation:
{formatted_history}

Based on the LAST 3-5 user responses, extract the qualitative signals described in the system prompt.

Focus on:
1. Overall engagement trajectory across responses
2. Reasoning patterns (not just content)
3. Subtle cues in language choice and structure
4. Consistency or shifts in stance

Return ONLY a valid JSON object. Do not include any explanatory text outside the JSON."""


def _format_conversation_for_analysis(
    history: List[Dict[str, Any]], max_turns: int = 10
) -> str:
    """Format conversation history for LLM analysis.

    Args:
        history: Conversation history (may include extraction metadata)
        max_turns: Maximum number of recent turns to include

    Returns:
        Formatted conversation string with optional extraction annotations
    """
    recent_history = history[-max_turns:] if len(history) > max_turns else history

    lines = []
    for i, turn in enumerate(recent_history, start=1):
        speaker = turn.get("speaker", "unknown")
        text = turn.get("text", "")
        role = turn.get("role", speaker)  # Some use "role" instead of "speaker"

        # Format: [Turn N] Speaker: text
        lines.append(f"[Turn {i}] {role}: {text}")

        # If extraction metadata available, include summary
        extraction = turn.get("extraction")
        if extraction and speaker == "user":
            concepts_count = len(extraction.get("concepts", []))
            avg_conf = extraction.get("avg_confidence", 0)
            extractable = extraction.get("is_extractable", True)

            if not extractable:
                lines.append("  [Extraction: Low elaboration - minimal extraction]")
            elif concepts_count > 0:
                lines.append(
                    f"  [Extraction: {concepts_count} concept(s), "
                    f"avg confidence: {avg_conf:.2f}]"
                )

    return "\n".join(lines)


def parse_qualitative_signals_response(
    response_content: str,
) -> Dict[str, Any]:
    """Parse LLM response into qualitative signals dict.

    Args:
        response_content: Raw LLM response (JSON string)

    Returns:
        Parsed signals dictionary

    Raises:
        ValueError: If response is not valid JSON
    """
    import json

    try:
        # Try direct JSON parse
        return json.loads(response_content)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        if "```json" in response_content:
            start = response_content.find("```json") + 7
            end = response_content.find("```", start)
            if end > start:
                return json.loads(response_content[start:end].strip())
        elif "```" in response_content:
            start = response_content.find("```") + 3
            end = response_content.find("```", start)
            if end > start:
                return json.loads(response_content[start:end].strip())

        # If all else fails, raise
        raise ValueError(
            f"Could not parse LLM response as JSON: {response_content[:200]}..."
        )
