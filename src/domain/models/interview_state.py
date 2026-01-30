"""
Interview state abstraction.

Provides abstract base class and mode-specific implementations:
- InterviewState: Abstract base for interview state tracking
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
    """Interview mode."""

    EXPLORATORY = "exploratory"
    """Emergent discovery for exploratory research (graph-driven)."""


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

    Each interview mode maintains different state and has different
    completion criteria.
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
        self, graph: GraphState, nodes: Optional[List["KGNode"]] = None
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
        self, graph: GraphState, nodes: Optional[List["KGNode"]] = None
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
                        label=node.label,
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
                            reason=f"theme:{theme_id}",
                        )
                    )

        return candidates

    # Theme management helpers

    def get_or_create_theme(
        self, theme_id: str, label: Optional[str] = None
    ) -> ThemeState:
        """Get existing theme or create new one."""
        if theme_id not in self.themes:
            self.themes[theme_id] = ThemeState(
                theme_id=theme_id, label=label or theme_id
            )
        return self.themes[theme_id]

    def activate_theme(self, theme_id: str, turn_number: int) -> None:
        """Mark theme as active."""
        if theme_id in self.themes:
            theme = self.themes[theme_id]
            theme.is_active = True
            theme.last_active_turn = turn_number

    def add_node_to_theme(self, theme_id: str, node_id: str, turn_number: int) -> None:
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

