"""Signal extraction helper functions.

These functions provide common data extraction patterns used across multiple
Tier-2 signal scorers. They encapsulate repetitive data access patterns for
conversation history, graph state, and strategy/focus structures.

Reference: ADR-006 - Enhanced Scoring and Strategy Architecture
"""

from typing import Dict, List, Optional
import re


# Mapping from EmotionalSignal intensity to numeric sentiment scale
INTENSITY_TO_SENTIMENT = {
    "high_positive": 1.0,
    "moderate_positive": 0.5,
    "neutral": 0.0,
    "moderate_negative": -0.5,
    "high_negative": -1.0,
}


def get_recent_user_responses(
    history: List[Dict], count: int = 5, lookback: int = 10
) -> List[str]:
    """Extract last N user responses from conversation history.

    Scans the most recent `lookback` turns and extracts user responses
    (identified by role == "user" or from == "user").

    Args:
        history: List of conversation turn dictionaries
        count: Maximum number of responses to extract (default: 5)
        lookback: Number of recent turns to scan (default: 10)

    Returns:
        List of user response strings (most recent first)
    """
    responses = []

    # Look at most recent turns first (reverse order)
    for turn in reversed(history[-lookback:]):
        # Handle different response formats
        if "user_response" in turn:
            response = turn.get("user_response", "")
        elif "messages" in turn:
            # Extract from messages list
            for msg in reversed(turn["messages"]):
                if msg.get("role") == "user" or msg.get("from") == "user":
                    response = msg.get("content", "")
                    break
            else:
                continue
        elif turn.get("role") == "user" or turn.get("from") == "user":
            response = turn.get("content", "")
        else:
            continue

        if response and response.strip():
            responses.append(response.strip())
            if len(responses) >= count:
                break

    return responses


def find_node_by_id(recent_nodes: List[Dict], node_id: str) -> Optional[Dict]:
    """Find a node in recent_nodes by ID.

    Args:
        recent_nodes: List of node dictionaries with 'id' field
        node_id: Node ID to search for

    Returns:
        Node dictionary if found, None otherwise
    """
    for node in recent_nodes:
        if node.get("id") == node_id:
            return node
    return None


def get_strategy_info(strategy: Dict) -> tuple[str, str]:
    """Extract (strategy_id, type_category) from strategy dict.

    Strategy dict structure: {'id': 'strategy_name', 'type': 'category'}

    Args:
        strategy: Strategy dictionary

    Returns:
        Tuple of (strategy_id, type_category)
        Returns (strategy.get('id', ''), strategy.get('type', '')) if missing fields
    """
    strategy_id = strategy.get("id", "")
    type_category = strategy.get("type", "")
    return strategy_id, type_category


def get_focus_target(focus: Dict) -> tuple[str, str]:
    """Extract (node_id, element_id) from focus dict.

    Focus dict structure: {'node_id': '...', 'element_id': '...'}

    Args:
        focus: Focus dictionary

    Returns:
        Tuple of (node_id, element_id)
        Returns ('', '') if fields are missing
    """
    node_id = focus.get("node_id", "")
    element_id = focus.get("element_id", "")
    return node_id, element_id


def get_coverage_state(graph_state) -> Dict:
    """Extract coverage_state from graph_state.properties with default handling.

    Args:
        graph_state: GraphState object with properties attribute

    Returns:
        Coverage state dictionary, or empty dict if not found
    """
    if not hasattr(graph_state, "properties"):
        return {}

    properties = graph_state.properties
    if not isinstance(properties, dict):
        return {}

    coverage_state = properties.get("coverage_state", {})
    if not isinstance(coverage_state, dict):
        return {}

    return coverage_state


def count_pattern_occurrences(text: str, patterns: List[str]) -> int:
    """Count how many patterns appear in text.

    Uses regex search for flexible pattern matching. Patterns can be
    plain strings or regex patterns.

    Args:
        text: Text to search in
        patterns: List of pattern strings to search for

    Returns:
        Number of patterns found in text (counts each pattern once)
    """
    if not text or not patterns:
        return 0

    count = 0
    text_lower = text.lower()

    for pattern in patterns:
        try:
            # Try regex match first
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        except re.error:
            # Fallback to substring search if not valid regex
            if pattern.lower() in text_lower:
                count += 1

    return count


def get_sentiment_from_signals(emotional_signal: Optional[Dict]) -> Optional[float]:
    """Convert EmotionalSignal intensity to numeric sentiment value.

    Converts the categorical intensity from LLM-extracted EmotionalSignal
    to a numeric sentiment scale (-1.0 to +1.0). This provides turn-level sentiment
    metadata without requiring additional LLM calls.

    Args:
        emotional_signal: Dict from QualitativeSignalExtractor containing
            emotional signal data with 'intensity' field

    Returns:
        Sentiment value from -1.0 (high_negative) to +1.0 (high_positive),
        or None if emotional_signal is not available or intensity not recognized

    Example:
        >>> signal = {"intensity": "moderate_positive", "confidence": 0.8}
        >>> get_sentiment_from_signals(signal)
        0.5

        >>> signal = {"intensity": "neutral"}
        >>> get_sentiment_from_signals(signal)
        0.0
    """
    if not emotional_signal:
        return None

    intensity = emotional_signal.get("intensity", "")
    return INTENSITY_TO_SENTIMENT.get(intensity)


__all__ = [
    "get_recent_user_responses",
    "find_node_by_id",
    "get_strategy_info",
    "get_focus_target",
    "get_coverage_state",
    "count_pattern_occurrences",
    "get_sentiment_from_signals",
]
