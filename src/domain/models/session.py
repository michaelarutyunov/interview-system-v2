"""Session domain models for interview lifecycle management.

This module defines data structures for interview session persistence and
state tracking throughout the conversation.

Core Models:
    - Session: Top-level interview entity with metadata and status
    - SessionState: Mutable interview state tracked across turns

Session Lifecycle:
    1. Created with methodology, concept_id, concept_name
    2. State updates on each turn (turn_count increment, last_strategy)
    3. Closed when max_turns reached or termination condition met
    4. Status: active -> completed (or abandoned if error)

State Transition:
    - ContextLoadingStage reads SessionState for turn_number
    - ScoringPersistenceStage writes updated state back to database
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from src.domain.models.interview_state import InterviewMode


class FocusEntry(BaseModel):
    """Single entry in focus history tracking strategy-node decisions.

    Records the strategy and optional node focus for each turn, enabling
    post-hoc analysis of the exploration path through the knowledge graph.
    """

    turn: int = Field(description="Turn number (1-indexed)")
    node_id: str = Field(
        default="", description="Target node ID, empty if no node focus"
    )
    label: str = Field(default="", description="Human-readable node label")
    strategy: str = Field(description="Strategy selected for this turn")


class SessionState(BaseModel):
    """Mutable interview state tracked across conversation turns.

    Session-level state that updates on each turn and drives
    interview behavior and progression.

    Fields:
        - turn_count: Number of turns completed (0-indexed, increments post-turn)
        - last_strategy: Most recent strategy for temporal diversity signals
        - mode: InterviewMode (EXPLORATORY/FOCUSED/CLOSING) for phasing

    Update Flow:
        1. ContextLoadingStage (Stage 1) reads current state
        2. Pipeline uses turn_number for decisions
        3. ScoringPersistenceStage (Stage 10) writes updated state
    """

    methodology: str  # e.g., "mec" (Means-End Chain), "zmet" (Zmet)
    concept_id: str
    concept_name: str
    turn_count: int = 0
    last_strategy: Optional[str] = None
    mode: InterviewMode = InterviewMode.EXPLORATORY

    # Velocity tracking for saturation signals (updated by ScoringPersistenceStage each turn)
    surface_velocity_peak: float = Field(
        default=0.0, description="Peak surface node delta observed in this session"
    )
    prev_surface_node_count: int = Field(
        default=0, description="Surface node count at end of previous turn"
    )
    canonical_velocity_peak: float = Field(
        default=0.0, description="Peak canonical node delta observed in this session"
    )
    prev_canonical_node_count: int = Field(
        default=0, description="Canonical node count at end of previous turn"
    )

    # Focus history for tracing strategy-node decisions across turns
    focus_history: List[FocusEntry] = Field(
        default_factory=list,
        description="Ordered sequence of strategy-node decisions across turns",
    )


class Session(BaseModel):
    """Top-level interview session entity for lifecycle management.

    Represents a complete interview instance from creation to completion.
    Stored in database sessions table and loaded by ContextLoadingStage.

    Attributes:
        - methodology: Interview framework (e.g., 'mec', 'jtbd', 'rep_grid')
        - concept_id: Topic identifier from concept configuration
        - concept_name: Human-readable topic name
        - status: Session lifecycle state (active/completed/abandoned)
        - mode: InterviewMode (EXPLORATORY/FOCUSED/CLOSING)
        - state: Embedded SessionState for mutable turn-tracking data

    Status Transitions:
        - 'active' -> 'completed': Normal termination (max_turns or saturation)
        - 'active' -> 'abandoned': Error or user cancellation
    """

    id: str
    methodology: str
    concept_id: str
    concept_name: str
    created_at: datetime
    updated_at: datetime
    state: SessionState
    status: str = Field(default="active")  # "active", "completed", "abandoned"
    mode: InterviewMode = InterviewMode.EXPLORATORY
