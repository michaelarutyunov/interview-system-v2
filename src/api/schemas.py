"""
API request/response schemas.

Pydantic models for API validation and serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


# ============ SESSION SCHEMAS (from Phase 1) ============

class SessionCreate(BaseModel):
    """Request to create a new session."""
    methodology: str = Field(default="means_end_chain")
    concept_id: str
    config: Dict[str, Any] = Field(default_factory=dict)


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


class SessionListResponse(BaseModel):
    """List of sessions response."""
    sessions: List[SessionResponse]
    total: int


# ============ TURN SCHEMAS (Phase 2) ============

class TurnRequest(BaseModel):
    """Request to process a turn."""
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's response text"
    )


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
    """Scoring results in turn response (Phase 3)."""
    coverage: float = 0.0
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

    class Config:
        json_schema_extra = {
            "example": {
                "turn_number": 3,
                "extracted": {
                    "concepts": [
                        {"text": "creamy texture", "type": "attribute", "confidence": 0.9}
                    ],
                    "relationships": [
                        {"source": "creamy texture", "target": "satisfying", "type": "leads_to"}
                    ]
                },
                "graph_state": {
                    "node_count": 5,
                    "edge_count": 3,
                    "depth_achieved": {"attribute": 3, "functional_consequence": 2}
                },
                "scoring": {
                    "coverage": 0.25,
                    "depth": 0.15,
                    "saturation": 0.0
                },
                "strategy_selected": "deepen",
                "next_question": "You mentioned the creamy texture feels satisfying. Why is that feeling important to you?",
                "should_continue": True,
                "latency_ms": 1250
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


# ============ SYNTHETIC SCHEMAS (Phase 4) ============

class SyntheticRespondRequest(BaseModel):
    """Request to generate a synthetic response."""
    question: str = Field(..., description="The interviewer's question")
    session_id: str = Field(..., description="Session identifier")
    persona: str = Field(default="health_conscious", description="Persona ID")
    interview_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional interview context with product_name, turn_number, coverage_achieved"
    )
    use_deflection: Optional[bool] = Field(
        default=None,
        description="Override deflection behavior (None = use chance)"
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
        default=None,
        description="List of persona IDs (None = all available)"
    )
    interview_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional interview context"
    )


class SyntheticSequenceRequest(BaseModel):
    """Request to generate interview sequence."""
    questions: List[str] = Field(..., description="List of interview questions")
    session_id: str = Field(..., description="Session identifier")
    persona: str = Field(default="health_conscious", description="Persona ID")
    product_name: str = Field(default="the product", description="Product name for context")


class PersonasResponse(BaseModel):
    """Response with available personas."""
    personas: Dict[str, str] = Field(..., description="Mapping of persona_id to persona_name")
