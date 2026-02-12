"""Utterance domain models for conversation provenance tracking.

This module defines the Utterance model that represents individual
conversation turns in the interview.

Core Concepts:
    - Speaker identification: USER vs SYSTEM for role tracking
    - Turn numbering: Sequential ordering for conversation history
    - Provenance tracking: Source utterance IDs link graph entities to origin
    - Discourse markers: Linguistic signals (because, so, but) for reasoning

Pipeline Integration:
    - UtteranceSavingStage (Stage 2): Creates utterance records
    - ExtractionStage (Stage 3): References source_utterance_id for traceability
    - KGNode/Edge: Store source_utterance_ids for ADR-010 provenance
"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime, timezone  # noqa: F401 (imported for datetime.now(timezone.utc))
from enum import Enum


class Speaker(str, Enum):
    """Speaker role for utterance attribution.

    Distinguishes between participant and system contributions
    for conversation history and provenance tracking.

    Values:
        - USER: Interview participant response (primary knowledge source)
        - SYSTEM: Interviewer question or prompt (for context, not extraction)

    Used by:
        - Utterance.speaker field for role attribution
        - Conversation history rendering in context windows
    """

    USER = "user"
    SYSTEM = "system"


class Utterance(BaseModel):
    """Single conversation turn with provenance tracking.

    Atomic unit of conversation stored in database utterances table.
    Provides traceability from graph entities back to original
    user responses (ADR-010 provenance chain).

    Key Attributes:
        - speaker: USER or SYSTEM for role identification
        - turn_number: Sequential position in conversation (1-indexed)
        - discourse_markers: Linguistic cues (because, so, but) for reasoning signals
        - created_at: Timestamp for temporal ordering and staleness detection

    Provenance Chain:
        1. UtteranceSavingStage (Stage 2) creates Utterance record
        2. ExtractionStage (Stage 3) records source_utterance_id
        3. GraphUpdateStage (Stage 4) stores source_utterance_ids on nodes/edges
        4. Enables traceability: Node -> Utterance -> Turn -> User Input
    """

    id: str
    session_id: str
    turn_number: int
    speaker: str  # "user" or "system"
    text: str
    discourse_markers: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}
