"""Base classes for two-tier hybrid scoring system.

Tier 1: Hard constraints (boolean veto checks)
- Early exit on first veto
- No weights, all equal veto power

Tier 2: Weighted additive scoring
- Linear combination with weights summing to 1.0
- Scores in range [0, 2] with 1.0 as neutral
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import structlog

from src.domain.models.knowledge_graph import GraphState

logger = structlog.get_logger(__name__)


class Tier1Output(BaseModel):
    """Output from a Tier 1 scorer (hard constraint).

    Contains veto decision and provenance for debugging.
    """
    scorer_id: str = Field(description="Unique identifier for the scorer")
    is_veto: bool = Field(description="Whether this candidate is vetoed")
    reasoning: str = Field(description="Human-readable explanation")
    signals: Dict[str, Any] = Field(default_factory=dict, description="State signals used")

    model_config = {"from_attributes": True}


class Tier1Scorer(ABC):
    """Abstract base class for Tier 1 hard constraint scorers.

    Design constraints:
    - Pure functions of state (no side effects)
    - Single boolean decision (veto or pass)
    - Early exit on first veto across all Tier 1 scorers
    - All vetoes have equal power (no weights)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Tier 1 scorer with configuration.

        Args:
            config: Scorer configuration with optional:
                - enabled: bool (default: True)
                - veto_threshold: float (if applicable)
                - params: dict of scorer-specific params
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.params = self.config.get("params", {})

        # Extract scorer_id from class name
        self.scorer_id = self.__class__.__name__

    @abstractmethod
    async def evaluate(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list,
        conversation_history: list[Dict[str, str]],
    ) -> Tier1Output:
        """Evaluate whether to veto this (strategy, focus) combination.

        Args:
            strategy: Strategy dict with keys:
                - id: str
                - type_category: str ("depth", "breadth", "coverage", "closing")
            focus: Focus dict with keys:
                - node_id: Optional[str]
                - focus_type: str
                - focus_description: str
                - properties: dict
            graph_state: Current graph state
            recent_nodes: List of recent node dicts from last N turns
            conversation_history: Recent conversation turns for analysis

        Returns:
            Tier1Output with is_veto flag and reasoning
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled})"


class Tier2Output(BaseModel):
    """Output from a Tier 2 scorer (weighted additive).

    Contains score and provenance for debugging.
    """
    scorer_id: str = Field(description="Unique identifier for the scorer")
    raw_score: float = Field(default=1.0, ge=0.0, le=2.0, description="Score 0-2 where 1.0=neutral")
    weight: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight in additive combination")
    contribution: float = Field(description="Contribution to final score (weight × raw_score)")
    signals: Dict[str, Any] = Field(default_factory=dict, description="State signals used")
    reasoning: str = Field(description="Human-readable explanation")

    model_config = {"from_attributes": True}


class Tier2Scorer(ABC):
    """Abstract base class for Tier 2 weighted additive scorers.

    Design constraints:
    - Pure functions of state (no side effects)
    - Single orthogonal dimension per scorer
    - Return scores in [0, 2] range with 1.0 as neutral
    - Weights sum to 1.0 across all Tier 2 scorers
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Tier 2 scorer with configuration.

        Args:
            config: Scorer configuration with optional:
                - enabled: bool (default: True)
                - weight: float (default: varies by scorer)
                - params: dict of scorer-specific params
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.weight = self.config.get("weight", 0.15)
        self.params = self.config.get("params", {})

        # Extract scorer_id from class name
        self.scorer_id = self.__class__.__name__

    @abstractmethod
    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list,
        conversation_history: list[Dict[str, str]],
    ) -> Tier2Output:
        """Score a (strategy, focus) combination along one dimension.

        Args:
            strategy: Strategy dict
            focus: Focus dict
            graph_state: Current graph state
            recent_nodes: List of recent node dicts
            conversation_history: Recent conversation turns

        Returns:
            Tier2Output with score in [0, 2] and reasoning
        """
        pass

    def make_output(
        self,
        raw_score: float,
        signals: Dict[str, Any],
        reasoning: str,
    ) -> Tier2Output:
        """Helper to construct Tier2Output with proper validation.

        Args:
            raw_score: Raw score (will be clamped to 0.0-2.0)
            signals: State signals used in scoring
            reasoning: Human-readable explanation

        Returns:
            Tier2Output with all fields populated
        """
        clamped = max(0.0, min(2.0, raw_score))
        contribution = self.weight * clamped

        return Tier2Output(
            scorer_id=self.scorer_id,
            raw_score=clamped,
            weight=self.weight,
            contribution=contribution,
            signals=signals,
            reasoning=reasoning,
        )

    def __repr__(self) -> str:
        enabled_str = f"enabled={self.enabled}" if not self.enabled else ""
        return f"{self.__class__.__name__}(weight={self.weight:.2f}, {enabled_str})"
