"""
Turn processing domain models.

Defines typed models for the turn processing pipeline, replacing
untyped Dict[str, Any] usage in service interfaces.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from src.domain.models.knowledge_graph import GraphState, KGNode
from src.domain.models.utterance import Utterance
from src.domain.models.extraction import ExtractionResult
from src.domain.models.interview_state import InterviewMode


class TurnContext(BaseModel):
    """
    Complete context for turn processing.

    Encapsulates all data needed to process a single interview turn,
    replacing untyped dict passing between services.
    """

    session_id: str
    turn_number: int
    user_input: str
    graph_state: GraphState
    recent_nodes: List[KGNode] = Field(default_factory=list)
    conversation_history: List[Utterance] = Field(default_factory=list)
    mode: InterviewMode = InterviewMode.EXPLORATORY

    # Additional context fields
    methodology: str = ""
    concept_id: str = ""
    concept_name: str = ""
    max_turns: int = 20

    model_config = {"arbitrary_types_allowed": True}


class Focus(BaseModel):
    """
    Typed focus target for strategy selection.

    Replaces Dict[str, Any] focus objects with properly typed model.
    Defines what the next question should focus on.
    """

    focus_type: Literal[
        "depth_exploration",
        "breadth_exploration",
        "closing",
        "reflection",
        "lateral_bridge",
        "counter_example",
        "rapport_repair",
        "synthesis",
    ]
    node_id: Optional[str] = Field(
        None, description="Node ID if focusing on a specific node"
    )
    focus_description: str = Field(
        ..., description="Human-readable description of the focus"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score for this focus"
    )


class TurnResult(BaseModel):
    """
    Complete result of turn processing.

    Encapsulates all output from processing a single turn,
    providing structured return type for the service layer.
    """

    turn_number: int
    extracted: ExtractionResult
    graph_state: GraphState
    next_question: str
    should_continue: bool
    latency_ms: int = 0

    model_config = {"arbitrary_types_allowed": True}
