"""
Domain models for interview concepts.

Concepts define WHAT to explore (semantic targets) and are methodology-agnostic.
The methodology defines HOW to explore (node types, ladder, opening style).
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ConceptContext(BaseModel):
    """
    Research brief context for a concept.

    Provides LLM context about the research focus without being methodology-specific.

    For exploratory interviews, the 'objective' field serves as the primary task
    description, guiding the interviewer on what specific aspect of the concept
    to explore. This is particularly useful when combined with methodology-specific
    opening_bias to generate targeted opening questions.
    """

    objective: Optional[str] = Field(
        None,
        description="Primary research objective or task for exploratory interviews. "
        "This field provides focused guidance on what specific aspect to explore, "
        "making it particularly valuable for generating methodology-appropriate "
        "opening questions when combined with the methodology's opening_bias. "
        "Example: 'Explore how consumers make decisions about plant-based milk "
        "alternatives, focusing on the attributes that matter most to them.'",
    )


class ConceptElement(BaseModel):
    """
    A semantic element within a concept (LEGACY - evaluative interviews).

    NOTE: Elements are legacy feature for evaluative interviews with predefined topics.
    Current system is EXPLORATORY ONLY - elements are not used in practice.
    This class exists for backward compatibility with old concept formats.
    """

    id: int = Field(..., description="Unique integer identifier (1, 2, 3...)", ge=1)
    label: str = Field(
        ...,
        description="Human-readable label, used for substring matching like aliases",
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Additional terms for fuzzy matching (label is implicitly an alias)",
    )


class Concept(BaseModel):
    """
    An interview concept defining what topics to explore.

    Concepts are decoupled from methodologies - the same concept can
    be used with different methodologies (MEC, JTBD, Repertory Grid, etc.).

    NOTE: elements field is legacy (evaluative interviews). Current system
    is EXPLORATORY ONLY - elements list is always empty in practice.

    Key changes from v1 format:
    - Element IDs are integers (1, 2, 3) instead of strings
    - Elements have no 'type' field (methodology-agnostic)
    - 'context' contains topic/insight/promise/rtb for LLM context
    - 'aliases' field on elements for fuzzy matching
    """

    id: str = Field(..., description="Unique concept identifier (e.g., 'oat_milk_v2')")
    name: str = Field(..., description="Human-readable concept name")
    methodology: str = Field(
        ...,
        description="Which methodology to use (e.g., 'means_end_chain', 'jobs_to_be_done')",
    )
    context: ConceptContext = Field(
        ...,
        description="Research brief context (topic, insight, promise, rtb)",
    )
    elements: List[ConceptElement] = Field(
        ...,
        description="Semantic elements to explore (methodology-agnostic)",
    )
