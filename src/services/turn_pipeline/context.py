"""
Context object for turn processing pipeline.

ADR-008 Phase 3: TurnContext carries state through all pipeline stages.
ADR-010: Added graph_state_computed_at for freshness validation.
Phase 4: Added signals and strategy_alternatives for methodology-based selection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.domain.models.knowledge_graph import GraphState, KGNode
from src.domain.models.extraction import ExtractionResult
from src.domain.models.utterance import Utterance


@dataclass
class PipelineContext:
    """
    Context object that accumulates state through pipeline stages.

    Each stage reads and/or modifies fields in this context.
    """

    # Input parameters (immutable after creation)
    session_id: str
    user_input: str

    # Session metadata (loaded in ContextLoadingStage)
    methodology: str = ""
    concept_id: str = ""
    concept_name: str = ""
    turn_number: int = 1
    mode: str = "coverage_driven"  # Interview mode from session
    max_turns: int = 20
    recent_utterances: List[Dict[str, str]] = field(default_factory=list)
    strategy_history: List[str] = field(
        default_factory=list
    )  # Recent strategies for diversity

    # Graph state (loaded in ContextLoadingStage, updated in GraphUpdateStage)
    graph_state: Optional[GraphState] = None
    graph_state_computed_at: Optional[datetime] = field(
        default=None,
        metadata={
            "description": "When graph_state was computed (ADR-010 freshness tracking)"
        },
    )
    recent_nodes: List[KGNode] = field(default_factory=list)

    # Extraction results (computed in ExtractionStage)
    extraction: Optional[ExtractionResult] = None

    # Utterances (saved in UtteranceSavingStage)
    user_utterance: Optional[Utterance] = None
    system_utterance: Optional[Utterance] = None

    # Graph updates (computed in GraphUpdateStage)
    nodes_added: List[KGNode] = field(default_factory=list)
    edges_added: List[Dict[str, Any]] = field(default_factory=list)

    # Strategy selection (computed in StrategySelectionStage)
    strategy: str = "deepen"
    selection_result: Optional[Any] = None
    focus: Optional[Dict[str, Any]] = None

    # Phase 4: Methodology-based strategy selection
    signals: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={
            "description": "Detected signals from methodology-specific signal detector"
        },
    )
    strategy_alternatives: List[tuple[str, float]] = field(
        default_factory=list,
        metadata={
            "description": "Alternative strategies with scores for observability"
        },
    )

    # Continuation decision (computed in ContinuationStage)
    should_continue: bool = True
    focus_concept: str = ""

    # Generated question (computed in QuestionGenerationStage)
    next_question: str = ""

    # Scoring data (computed in ScoringPersistenceStage)
    scoring: Dict[str, Any] = field(default_factory=dict)

    # Performance tracking
    stage_timings: Dict[str, float] = field(default_factory=dict)
