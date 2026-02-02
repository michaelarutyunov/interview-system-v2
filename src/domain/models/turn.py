"""
Turn processing domain models.

Defines typed models for the turn processing pipeline, replacing
untyped Dict[str, Any] usage in service interfaces.

Part of ADR-008 Phase 2: Formalize Contracts
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

    def to_dict(self) -> dict:
        """Convert to dict for backward compatibility."""
        result = {
            "focus_type": self.focus_type,
            "focus_description": self.focus_description,
            "confidence": self.confidence,
        }
        if self.node_id:
            result["node_id"] = self.node_id
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Focus":
        """Create from dict for backward compatibility."""
        return cls(
            focus_type=data.get("focus_type", "depth_exploration"),
            node_id=data.get("node_id"),
            focus_description=data.get("focus_description", ""),
            confidence=data.get("confidence", 1.0),
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

    def to_response_dict(self) -> dict:
        """
        Convert to API response format.

        Provides backward compatibility with existing API contracts.
        """
        return {
            "turn_number": self.turn_number,
            "extracted": {
                "concepts": [
                    {
                        "text": c.text,
                        "type": c.node_type,
                        "confidence": c.confidence,
                    }
                    for c in self.extracted.concepts
                ],
                "relationships": [
                    {
                        "source": r.source_text,
                        "target": r.target_text,
                        "type": r.relationship_type,
                    }
                    for r in self.extracted.relationships
                ],
            },
            "graph_state": {
                "node_count": self.graph_state.node_count,
                "edge_count": self.graph_state.edge_count,
                "depth_achieved": self.graph_state.nodes_by_type,
            },
            "strategy_selected": "unknown",
            "next_question": self.next_question,
            "should_continue": self.should_continue,
            "latency_ms": self.latency_ms,
        }
