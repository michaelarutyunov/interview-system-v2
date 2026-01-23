"""
Interview state abstraction for dual-mode architecture.

Provides abstract base class and mode-specific implementations:
- InterviewState: Abstract base for interview state tracking
- CoverageState: Coverage-driven state (systematic topic exploration)
- EmergenceState: GraphState-driven state (emergent discovery)

See ADR-005: docs/adr/005-dual-mode-interview-architecture.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState, KGNode

from src.domain.models.knowledge_graph import GraphState


class InterviewMode(str, Enum):
    """Interview execution mode."""

    COVERAGE_DRIVEN = "coverage_driven"
    """Systematic topic exploration for concept testing."""

    GRAPH_DRIVEN = "graph_driven"
    """Emergent discovery for exploratory research."""


@dataclass
class FocusCandidate:
    """
    A potential focus item for the next question.

    Represents a topic, node, or theme that could be the focus
    of the next interview question.
    """

    type: str  # "topic", "node", "theme"
    id: str
    priority: str  # "high", "medium", "low"
    reason: str  # "uncovered", "novel", "saturated", etc.
    label: Optional[str] = None  # Human-readable label for UI


class InterviewState(ABC):
    """
    Abstract base for interview state tracking.

    Each interview mode (coverage-driven, graph-driven) maintains
    different state and has different completion criteria.
    """

    @abstractmethod
    def completion_ratio(self) -> float:
        """
        Return 0-1 completion score.

        Returns:
            Float between 0.0 and 1.0 representing interview completion.
        """
        pass

    @abstractmethod
    def should_close(self, turn_count: int, config: Any) -> bool:
        """
        Determine if interview should end.

        Args:
            turn_count: Current turn number
            config: Session configuration dict

        Returns:
            True if interview should close, False otherwise
        """
        pass

    @abstractmethod
    def get_focus_candidates(
        self,
        graph: GraphState,
        nodes: Optional[List["KGNode"]] = None
    ) -> List[FocusCandidate]:
        """
        Return potential focus items for next question.

        Args:
            graph: Current knowledge graph state
            nodes: Optional list of nodes (for graph-driven mode)

        Returns:
            List of focus candidates, sorted by priority
        """
        pass


# ============================================================================
# Coverage-Driven Implementation
# ============================================================================


class TopicPriority(str, Enum):
    """Priority level for a topic."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TopicState:
    """
    State tracking for a single topic in coverage-driven mode.

    Tracks whether a researcher-defined topic has been covered,
    how deeply it's been explored, and whether it's saturated.
    """

    topic_id: str
    mentioned: bool = False
    depth_score: float = 0.0
    saturation: float = 0.0
    node_ids: List[str] = field(default_factory=list)
    first_seen_turn: Optional[int] = None
    last_attempt_turn: Optional[int] = None
    attempt_count: int = 0

    # Depth thresholds (from config)
    target_depth: float = 0.7

    # Exhaustion tracking
    exhaustion_threshold: int = 3  # Attempts before giving up

    def is_mentioned(self) -> bool:
        """Check if topic has been mentioned."""
        return self.mentioned

    def is_complete(self) -> bool:
        """
        Check if topic is complete (covered with sufficient depth).

        A topic is complete if:
        - It has been mentioned
        - Depth score meets target
        - NOT exhausted (failed attempts don't count as complete)

        Returns:
            True if topic is complete, False otherwise
        """
        if not self.mentioned:
            return False
        if self.depth_score < self.target_depth:
            return False
        # Don't count exhausted topics as complete
        if self.is_exhausted():
            return False
        return True

    def is_exhausted(self) -> bool:
        """
        Check if topic is exhausted (too many attempts without progress).

        Returns:
            True if topic is exhausted, False otherwise
        """
        return self.attempt_count >= self.exhaustion_threshold

    def is_saturated(self) -> bool:
        """
        Check if topic is saturated (no new information).

        Returns:
            True if saturation < 5% threshold, False otherwise
        """
        return self.saturation < 0.05

    def is_incomplete(self) -> bool:
        """
        Check if topic was mentioned but not fully explored.

        Returns:
            True if mentioned but depth < target, False otherwise
        """
        return self.mentioned and self.depth_score < self.target_depth


@dataclass
class CoverageState(InterviewState):
    """
    Coverage-driven state (systematic topic exploration).

    Tracks researcher-defined topics to ensure systematic coverage.
    Used for concept testing and semi-structured interviews.
    """

    topics: Dict[str, TopicState] = field(default_factory=dict)

    def __post_init__(self):
        """Validate state after initialization."""
        # Ensure all topic_ids are strings
        self.topics = {str(k): v for k, v in self.topics.items()}

    def completion_ratio(self) -> float:
        """
        Calculate completion ratio based on complete topics.

        Returns:
            Float between 0.0 and 1.0
        """
        if not self.topics:
            return 0.0

        complete = sum(1 for t in self.topics.values() if t.is_complete())
        return complete / len(self.topics)

    def should_close(self, turn_count: int, config: Any) -> bool:
        """
        Determine if interview should close based on coverage.

        Closing criteria:
        - Target coverage ratio met (default 0.8)
        - Minimum turns reached (default 10)
        - All topics either complete OR exhausted

        Args:
            turn_count: Current turn number
            config: Session configuration with target_coverage, min_turns, max_turns

        Returns:
            True if interview should close, False otherwise
        """
        # Extract config values with defaults from interview_config
        from src.core.config import interview_config
        target_coverage = getattr(config, "target_coverage", interview_config.session.target_coverage)
        min_turns = getattr(config, "min_turns", interview_config.session.min_turns)
        max_turns = getattr(config, "max_turns", interview_config.session.max_turns)

        # Must meet minimum turns
        if turn_count < min_turns:
            return False

        # Hard stop at max turns
        if turn_count >= max_turns:
            return True

        # Target coverage met
        if self.completion_ratio() >= target_coverage:
            return True

        # All topics either complete or exhausted (nothing more to do)
        if all(t.is_complete() or t.is_exhausted() for t in self.topics.values()):
            return True

        return False

    def get_focus_candidates(
        self,
        graph: GraphState,
        nodes: Optional[List["KGNode"]] = None
    ) -> List[FocusCandidate]:
        """
        Return focus candidates based on topic coverage needs.

        Priority order:
        1. Uncovered topics (high priority)
        2. Incomplete topics (medium priority)
        3. Novel nodes within current topic (low priority)

        Args:
            graph: Current knowledge graph
            nodes: Ignored (coverage mode uses topics)

        Returns:
            List of focus candidates sorted by priority
        """
        candidates = []

        for topic_id, topic in self.topics.items():
            if topic.is_exhausted():
                # Skip exhausted topics
                continue

            if not topic.is_mentioned():
                # Uncovered topic - high priority
                candidates.append(
                    FocusCandidate(
                        type="topic",
                        id=topic_id,
                        priority="high",
                        reason="uncovered"
                    )
                )
            elif topic.is_incomplete():
                # Mentioned but not deep enough - medium priority
                candidates.append(
                    FocusCandidate(
                        type="topic",
                        id=topic_id,
                        priority="medium",
                        reason="incomplete"
                    )
                )

        return candidates

    # Topic access helpers

    def get_topic(self, topic_id: str) -> Optional[TopicState]:
        """Get topic state by ID."""
        return self.topics.get(topic_id)

    def update_topic(
        self,
        topic_id: str,
        mentioned: Optional[bool] = None,
        depth_score: Optional[float] = None,
        saturation: Optional[float] = None,
        node_id: Optional[str] = None,
        turn_number: Optional[int] = None
    ) -> None:
        """
        Update topic state.

        Args:
            topic_id: Topic identifier
            mentioned: Whether topic has been mentioned
            depth_score: Depth score (0-1)
            saturation: Saturation score (0-1)
            node_id: Node ID to add to topic
            turn_number: Current turn number
        """
        if topic_id not in self.topics:
            return

        topic = self.topics[topic_id]

        if mentioned is not None:
            topic.mentioned = mentioned
            if mentioned and topic.first_seen_turn is None:
                topic.first_seen_turn = turn_number

        if depth_score is not None:
            topic.depth_score = max(topic.depth_score, depth_score)

        if saturation is not None:
            topic.saturation = saturation

        if node_id is not None and node_id not in topic.node_ids:
            topic.node_ids.append(node_id)

        if turn_number is not None:
            topic.last_attempt_turn = turn_number
            topic.attempt_count += 1


# ============================================================================
# GraphState-Driven Implementation
# ============================================================================


@dataclass
class ThemeState:
    """
    State tracking for an emergent theme in graph-driven mode.

    Themes are auto-discovered clusters of related nodes.
    """

    theme_id: str
    label: str
    node_ids: List[str] = field(default_factory=list)
    saturation: float = 1.0  # Starts high, decreases as new info emerges
    first_seen_turn: int = 0
    last_active_turn: int = 0
    is_active: bool = False

    def add_node(self, node_id: str) -> None:
        """Add node to theme."""
        if node_id not in self.node_ids:
            self.node_ids.append(node_id)

    def is_saturated(self) -> bool:
        """Check if theme is saturated (< 5% new info)."""
        return self.saturation < 0.05

    def node_count(self) -> int:
        """Return number of nodes in theme."""
        return len(self.node_ids)


@dataclass
class EmergenceState(InterviewState):
    """
    GraphState-driven state (emergent discovery).

    Tracks emergent themes that arise from respondent's natural
    associations. Used for exploratory research and grounded theory.
    """

    themes: Dict[str, ThemeState] = field(default_factory=dict)
    auto_discovery: bool = True
    theme_discovery_threshold: int = 3  # Nodes needed to form a theme

    def __post_init__(self):
        """Validate state after initialization."""
        self.themes = {str(k): v for k, v in self.themes.items()}

    def completion_ratio(self) -> float:
        """
        Calculate completion based on theme saturation.

        Returns:
            Float between 0.0 and 1.0
        """
        if not self.themes:
            return 0.0

        active_themes = [t for t in self.themes.values() if t.is_active]
        if not active_themes:
            return 0.0

        saturated = sum(1 for t in active_themes if t.is_saturated())
        return saturated / len(active_themes)

    def should_close(self, turn_count: int, config: Any) -> bool:
        """
        Determine if interview should close based on theme saturation.

        Closing criteria:
        - Minimum turns reached (default 15)
        - All active themes saturated
        - No novel nodes for extended period

        Args:
            turn_count: Current turn number
            config: Session configuration

        Returns:
            True if interview should close, False otherwise
        """
        from src.core.config import interview_config
        min_turns = getattr(config, "min_turns", interview_config.session.min_turns)
        max_turns = getattr(config, "max_turns", interview_config.session.max_turns)

        # Must meet minimum turns
        if turn_count < min_turns:
            return False

        # Hard stop at max turns
        if turn_count >= max_turns:
            return True

        # All active themes saturated
        active_themes = [t for t in self.themes.values() if t.is_active]
        if active_themes and all(t.is_saturated() for t in active_themes):
            return True

        return False

    def get_focus_candidates(
        self,
        graph: GraphState,
        nodes: Optional[List["KGNode"]] = None
    ) -> List[FocusCandidate]:
        """
        Return focus candidates based on graph emergence.

        Priority order:
        1. Novel nodes (not in any active theme) - high priority
        2. Nodes in unsaturated themes - medium priority
        3. Nodes in saturated themes - low priority

        Args:
            graph: Current knowledge graph
            nodes: List of nodes to analyze (required for graph mode)

        Returns:
            List of focus candidates sorted by priority
        """
        candidates = []

        if not nodes:
            return candidates

        # Track which nodes are in active themes
        nodes_in_themes = set()
        for theme in self.themes.values():
            if theme.is_active:
                nodes_in_themes.update(theme.node_ids)

        for node in nodes:
            if node.id not in nodes_in_themes:
                # Novel node - high priority
                candidates.append(
                    FocusCandidate(
                        type="node",
                        id=node.id,
                        priority="high",
                        reason="novel",
                        label=node.label
                    )
                )

        # Nodes in unsaturated themes
        for theme_id, theme in self.themes.items():
            if theme.is_active and not theme.is_saturated():
                for node_id in theme.node_ids:
                    candidates.append(
                        FocusCandidate(
                            type="node",
                            id=node_id,
                            priority="medium",
                            reason=f"theme:{theme_id}"
                        )
                    )

        return candidates

    # Theme management helpers

    def get_or_create_theme(self, theme_id: str, label: Optional[str] = None) -> ThemeState:
        """Get existing theme or create new one."""
        if theme_id not in self.themes:
            self.themes[theme_id] = ThemeState(
                theme_id=theme_id,
                label=label or theme_id
            )
        return self.themes[theme_id]

    def activate_theme(self, theme_id: str, turn_number: int) -> None:
        """Mark theme as active."""
        if theme_id in self.themes:
            theme = self.themes[theme_id]
            theme.is_active = True
            theme.last_active_turn = turn_number

    def add_node_to_theme(
        self,
        theme_id: str,
        node_id: str,
        turn_number: int
    ) -> None:
        """Add node to theme."""
        theme = self.get_or_create_theme(theme_id)
        theme.add_node(node_id)
        theme.last_active_turn = turn_number

    def is_node_in_active_theme(self, node_id: str) -> bool:
        """Check if node belongs to any active theme."""
        for theme in self.themes.values():
            if theme.is_active and node_id in theme.node_ids:
                return True
        return False


# ============================================================================
# Factory
# ============================================================================


def create_interview_state(
    mode: InterviewMode,
    topics: Optional[List[Dict[str, Any]]] = None
) -> InterviewState:
    """
    Create interview state instance for specified mode.

    Args:
        mode: Interview mode (coverage_driven or graph_driven)
        topics: Optional list of topic definitions for coverage-driven mode

    Returns:
        InterviewState instance (CoverageState or EmergenceState)
    """
    if mode == InterviewMode.COVERAGE_DRIVEN:
        if not topics:
            raise ValueError(
                "Coverage-driven mode requires topics. "
                "Provide topics in concept configuration."
            )

        topic_states = {}
        for topic_config in topics:
            topic_id = topic_config.get("id", str(len(topic_states)))
            priority = TopicPriority(topic_config.get("priority", "medium"))

            topic_states[topic_id] = TopicState(
                topic_id=topic_id,
                target_depth=_depth_for_priority(priority)
            )

        return CoverageState(topics=topic_states)

    else:  # GRAPH_DRIVEN
        return EmergenceState(
            themes={},
            auto_discovery=True
        )


def _depth_for_priority(priority: TopicPriority) -> float:
    """Map topic priority to target depth score."""
    mapping = {
        TopicPriority.HIGH: 0.8,
        TopicPriority.MEDIUM: 0.6,
        TopicPriority.LOW: 0.4
    }
    return mapping.get(priority, 0.6)
