"""Turn processing domain models for pipeline data flow.

This module defines typed models that encapsulate turn processing data,
replacing untyped Dict[str, Any] usage between services (ADR-010).

Core Models:
    - TurnContext: Complete input context for processing a turn
    - Focus: Typed focus target for strategy selection (what to ask about)
    - TurnResult: Complete output from turn processing

Pipeline Integration:
    - ContextLoadingStage builds TurnContext from Session + database
    - Stages pass TurnContext through pipeline (immutability preferred)
    - StrategySelectionStage produces Focus for question generation
    - Final TurnResult returned to API layer

Design Principles:
    - Type safety: Eliminate runtime type errors from dict passing
    - Immutability: Context should not mutate across stages
    - Explicit fields: Make data flow visible vs hidden dict keys
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from src.domain.models.knowledge_graph import GraphState, KGNode
from src.domain.models.utterance import Utterance
from src.domain.models.extraction import ExtractionResult
from src.domain.models.interview_state import InterviewMode


class TurnContext(BaseModel):
    """Complete input context for single turn processing.

    Encapsulates all data needed by pipeline stages to process
    one interview turn. Built by ContextLoadingStage (Stage 1)
    from Session database state, recent graph queries, and user input.

    Core Fields:
        - session_id: Links to database session record
        - turn_number: Current turn position (1-indexed)
        - user_input: Raw participant response text
        - graph_state: Current knowledge graph metrics for signal detection
        - recent_nodes: Most recently created nodes for focus selection
        - conversation_history: Recent utterances for LLM context

    Design Principle:
        Immutable data structure - stages should return modified copies
        rather than mutating this instance (ADR-008 pipeline pattern).
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
    """Typed focus target defining what next question should explore.

    Replaces untyped dict focus objects with validated Pydantic model.
    Produced by StrategySelectionStage (Stage 6) and consumed by
    QuestionGenerationStage (Stage 8) to guide question framing.

    Focus Types:
        - depth_exploration: Probe deeper into current concept chain
        - breadth_exploration: Explore new, unrelated concepts
        - closing: Summary and conclusion questions
        - reflection: Meta-cognitive prompts about reasoning
        - lateral_bridge: Connect across different concept areas
        - counter_example: Test boundaries with exception requests
        - rapport_repair: Clarify misunderstanding or disengagement
        - synthesis: Integrate multiple concepts into higher-level understanding

    Fields:
        - node_id: Optional specific node to focus on (None for breadth)
        - focus_description: Human-readable explanation for logging/debugging
        - confidence: 0.0-1.0 score for focus quality (if applicable)
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
    node_id: Optional[str] = Field(None, description="Node ID if focusing on a specific node")
    focus_description: str = Field(..., description="Human-readable description of the focus")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score for this focus"
    )


class TurnResult(BaseModel):
    """Complete output from processing a single interview turn.

    Encapsulates all results produced by the turn processing pipeline,
    providing a structured return type to the API service layer.

    Output Fields:
        - turn_number: Echo input for response correlation
        - extracted: ExtractionResult with concepts/relationships found
        - graph_state: Updated knowledge graph state after graph mutations
        - next_question: Generated question for participant
        - should_continue: Termination decision (False = end interview)
        - latency_ms: Performance metric for pipeline timing

    Usage:
        Returned by SessionService.process_turn() method to API layer,
        which extracts next_question for HTTP response while
        persisting other fields to database.

    Design Note:
        This model captures the complete pipeline contract output,
        combining results from multiple stages into single
        coherent response object.
    """

    turn_number: int
    extracted: ExtractionResult
    graph_state: GraphState
    next_question: str
    should_continue: bool
    latency_ms: int = 0

    model_config = {"arbitrary_types_allowed": True}
