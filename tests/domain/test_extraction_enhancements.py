"""Tests for enhanced ExtractionResult models (ADR-010 Phase 2).

RED Phase: Write failing tests first.
Tests for new traceability fields (source_utterance_id, reasoning).
"""

import pytest

from src.domain.models.extraction import (
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
)


class TestExtractedConceptEnhancements:
    """Tests for ExtractedConcept with source_utterance_id traceability."""

    def test_creates_concept_with_source_utterance_id(self):
        """Should create concept with source utterance ID for traceability."""
        concept = ExtractedConcept(
            text="oat milk is creamy",
            node_type="attribute",
            confidence=0.9,
            source_quote="oat milk is creamy",
            source_utterance_id="utter_123",  # NEW: Traceability
            linked_elements=[42],
            stance=1,  # Positive stance
        )

        assert concept.source_utterance_id == "utter_123"
        assert concept.stance == 1

    def test_stance_is_optional(self):
        """Should allow stance to be None if not applicable."""
        concept = ExtractedConcept(
            text="oat milk",
            node_type="attribute",
            confidence=0.8,
            source_quote="oat milk",
            source_utterance_id="utter_123",
            stance=None,  # Optional field
        )

        assert concept.stance is None


class TestExtractedRelationshipEnhancements:
    """Tests for ExtractedRelationship with reasoning and traceability."""

    def test_creates_relationship_with_reasoning(self):
        """Should create relationship with reasoning explaining why edge was created."""
        relationship = ExtractedRelationship(
            source_text="oat milk",
            target_text="creamy texture",
            relationship_type="has_attribute",
            confidence=0.85,
            reasoning="User explicitly described this quality",  # NEW
            source_utterance_id="utter_123",  # NEW: Traceability
        )

        assert relationship.reasoning == "User explicitly described this quality"
        assert relationship.source_utterance_id == "utter_123"

    def test_reasoning_is_optional(self):
        """Should allow reasoning to be None for implicit relationships."""
        relationship = ExtractedRelationship(
            source_text="oat milk",
            target_text="dairy alternative",
            relationship_type="similar_to",
            confidence=0.7,
            reasoning=None,  # Optional field
            source_utterance_id="utter_123",
        )

        assert relationship.reasoning is None


class TestExtractionResultTraceability:
    """Tests for ExtractionResult with traceability support."""

    def test_full_traceability_chain(self):
        """Should maintain traceability from utterance to graph."""
        result = ExtractionResult(
            concepts=[
                ExtractedConcept(
                    text="oat milk",
                    node_type="product",
                    confidence=0.95,
                    source_quote="oat milk",
                    source_utterance_id="utter_123",
                    linked_elements=[],
                    stance=0,
                )
            ],
            relationships=[
                ExtractedRelationship(
                    source_text="oat milk",
                    target_text="creamy",
                    relationship_type="has_attribute",
                    confidence=0.8,
                    reasoning="Explicit attribute",
                    source_utterance_id="utter_123",
                )
            ],
            # timestamp will be set by default factory
        )

        # Verify all concepts have source_utterance_id
        for concept in result.concepts:
            assert concept.source_utterance_id is not None

        # Verify all relationships have source_utterance_id
        for rel in result.relationships:
            assert rel.source_utterance_id is not None
