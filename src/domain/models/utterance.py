"""Domain model for utterances (conversation turns)."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Speaker(str, Enum):
    """Who produced the utterance."""
    USER = "user"
    SYSTEM = "system"


class Utterance(BaseModel):
    """A single turn in the conversation.

    Stored in utterances table, used for provenance tracking.
    """
    id: str
    session_id: str
    turn_number: int
    speaker: str  # "user" or "system"
    text: str
    discourse_markers: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}
