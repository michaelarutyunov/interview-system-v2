"""Session domain models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from src.domain.models.interview_state import InterviewMode


class SessionState(BaseModel):
    """Current state of an interview session."""

    methodology: str  # e.g., "mec" (Means-End Chain), "zmet" (Zmet)
    concept_id: str
    concept_name: str
    turn_count: int = 0
    coverage_score: float = 0.0
    last_strategy: Optional[str] = None
    mode: InterviewMode = InterviewMode.EXPLORATORY


class Session(BaseModel):
    """Interview session."""

    id: str
    methodology: str
    concept_id: str
    concept_name: str
    created_at: datetime
    updated_at: datetime
    state: SessionState
    status: str = Field(default="active")  # "active", "completed", "abandoned"
    mode: InterviewMode = InterviewMode.EXPLORATORY
