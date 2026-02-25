"""
API request/response schemas.

Pydantic models for API validation and serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.domain.models.interview_state import InterviewMode


# ============ SESSION SCHEMAS ============


class SessionCreate(BaseModel):
    """Request to create a new session."""

    methodology: str = Field(default="means_end_chain")
    concept_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    mode: InterviewMode = Field(
        default=InterviewMode.EXPLORATORY,
        description="Interview execution mode",
    )


class SessionResponse(BaseModel):
    """Session details response."""

    id: str
    methodology: str
    concept_id: str
    status: str
    config: Dict[str, Any]
    turn_count: int = 0
    created_at: datetime
    updated_at: datetime
    mode: InterviewMode = InterviewMode.EXPLORATORY


class SessionListResponse(BaseModel):
    """List of sessions response."""

    sessions: List[SessionResponse]
    total: int


# ============ TURN SCHEMAS ============


class TurnRequest(BaseModel):
    """Request to process a turn."""

    text: str = Field(..., min_length=1, max_length=5000, description="User's response text")


class ExtractedConceptSchema(BaseModel):
    """Extracted concept in response."""

    text: str
    type: str
    confidence: float


class ExtractedRelationshipSchema(BaseModel):
    """Extracted relationship in response."""

    source: str
    target: str
    type: str


class ExtractionSchema(BaseModel):
    """Extraction results in turn response."""

    concepts: List[ExtractedConceptSchema] = Field(default_factory=list)
    relationships: List[ExtractedRelationshipSchema] = Field(default_factory=list)


class GraphStateSchema(BaseModel):
    """Graph state in turn response."""

    node_count: int
    edge_count: int
    depth_achieved: Dict[str, int] = Field(default_factory=dict)


class ScoringSchema(BaseModel):
    """Scoring results in turn response."""

    depth: float = 0.0
    saturation: float = 0.0


class TurnResponse(BaseModel):
    """Response from processing a turn.

    Matches PRD Section 8.6.
    """

    turn_number: int
    extracted: ExtractionSchema
    graph_state: GraphStateSchema
    scoring: ScoringSchema
    strategy_selected: str
    next_question: str
    should_continue: bool
    latency_ms: int = 0
    # Methodology-based signal detection observability
    signals: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Methodology signals from signal pools (graph, llm, temporal, meta)",
    )
    strategy_alternatives: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Alternative strategies with scores (including node_id for joint scoring)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "turn_number": 3,
                "extracted": {
                    "concepts": [
                        {
                            "text": "creamy texture",
                            "type": "attribute",
                            "confidence": 0.9,
                        }
                    ],
                    "relationships": [
                        {
                            "source": "creamy texture",
                            "target": "satisfying",
                            "type": "leads_to",
                        }
                    ],
                },
                "graph_state": {
                    "node_count": 5,
                    "edge_count": 3,
                    "depth_achieved": {"attribute": 3, "functional_consequence": 2},
                },
                "scoring": {"depth": 0.15, "saturation": 0.0},
                "strategy_selected": "deepen",
                "next_question": "You mentioned the creamy texture feels satisfying. Why is that feeling important to you?",
                "should_continue": True,
                "latency_ms": 1250,
            }
        }


class StartSessionResponse(BaseModel):
    """Response from starting a session."""

    session_id: str
    opening_question: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str
    error_type: Optional[str] = None


# ============ SYNTHETIC SCHEMAS ============


class SyntheticRespondRequest(BaseModel):
    """Request to generate a synthetic response."""

    question: str = Field(..., description="The interviewer's question")
    session_id: str = Field(..., description="Session identifier")
    persona: str = Field(default="baseline_cooperative", description="Persona ID")
    interview_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional interview context with product_name, turn_number",
    )
    use_deflection: Optional[bool] = Field(
        default=None, description="Override deflection behavior (None = use chance)"
    )


class SyntheticRespondResponse(BaseModel):
    """Response from synthetic generation."""

    response: str = Field(..., description="Generated synthetic response")
    persona: str = Field(..., description="Persona ID used")
    persona_name: str = Field(..., description="Human-readable persona name")
    question: str = Field(..., description="Original question")
    latency_ms: float = Field(..., description="LLM latency in milliseconds")
    tokens_used: Dict[str, int] = Field(..., description="Token usage from LLM")
    used_deflection: bool = Field(..., description="Whether deflection prompt was used")


class SyntheticMultiRequest(BaseModel):
    """Request to generate multiple synthetic responses."""

    question: str = Field(..., description="The interviewer's question")
    session_id: str = Field(..., description="Session identifier")
    personas: Optional[List[str]] = Field(
        default=None, description="List of persona IDs (None = all available)"
    )
    interview_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional interview context"
    )


class SyntheticSequenceRequest(BaseModel):
    """Request to generate interview sequence."""

    questions: List[str] = Field(..., description="List of interview questions")
    session_id: str = Field(..., description="Session identifier")
    persona: str = Field(default="baseline_cooperative", description="Persona ID")
    product_name: str = Field(default="the product", description="Product name for context")


# ============ STATUS AND GRAPH SCHEMAS ============


class NodeSchema(BaseModel):
    """Knowledge graph node."""

    id: str
    label: str
    node_type: str
    confidence: float
    properties: Dict[str, Any] = Field(default_factory=dict)


class EdgeSchema(BaseModel):
    """Knowledge graph edge."""

    id: str
    source_id: str
    target_id: str
    edge_type: str
    confidence: float
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    """Knowledge graph response."""

    nodes: List[NodeSchema] = Field(default_factory=list)
    edges: List[EdgeSchema] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


class SessionStatusResponse(BaseModel):
    """Session status response."""

    turn_number: int
    max_turns: int
    status: str
    should_continue: bool
    strategy_selected: str = "unknown"
    strategy_reasoning: Optional[str] = None
    phase: str = "unknown"  # Interview phase: exploratory, focused, or closing
    focus_tracing: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered sequence of strategy-node decisions across turns for post-hoc analysis",
    )


# ============ SIMULATION SCHEMAS ============


class SimulationTurnSchema(BaseModel):
    """Single turn in simulated interview."""

    turn_number: int
    question: str
    response: str
    persona: str
    persona_name: str
    strategy_selected: Optional[str] = None
    should_continue: bool = True
    latency_ms: float = 0.0
    # Methodology-based signal detection observability
    signals: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Methodology signals from signal pools (graph, llm, temporal, meta)",
    )
    strategy_alternatives: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Alternative strategies with scores (including node_id for joint scoring)",
    )
    termination_reason: Optional[str] = Field(
        default=None,
        description="Reason for termination (e.g., 'max_turns_reached', 'graph_saturated', 'close_strategy')",
    )


class SimulationRequest(BaseModel):
    """Request to simulate an interview."""

    concept_id: str = Field(..., description="Concept ID (e.g., 'headphones_mec')")
    persona_id: str = Field(default="baseline_cooperative", description="Persona ID")
    max_turns: int = Field(default=10, description="Maximum turns before forcing stop")
    session_id: Optional[str] = Field(default=None, description="Optional session ID")


class SimulationResponse(BaseModel):
    """Result of simulated interview."""

    concept_id: str
    concept_name: str
    product_name: str
    objective: str
    methodology: str
    persona_id: str
    persona_name: str
    session_id: str
    total_turns: int
    turns: List[SimulationTurnSchema]
    status: str = "completed"  # completed, max_turns_reached, error

    # Graph diagnostics (nodes and edges for diagnostic visibility)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
