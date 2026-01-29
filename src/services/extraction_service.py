"""
Extraction service for processing user responses.

Pipeline:
1. Assess extractability (fast pre-filter)
2. Extract concepts and relationships via LLM
3. Parse and validate results
4. Return ExtractionResult

Graceful degradation: Returns empty result on LLM errors.
"""

import time
from typing import Optional, List, Dict

import structlog

from src.llm.client import LLMClient, get_extraction_llm_client
from src.llm.prompts.extraction import (
    get_extraction_system_prompt,
    get_extraction_user_prompt,
    get_extractability_system_prompt,
    get_extractability_user_prompt,
    parse_extraction_response,
    parse_extractability_response,
)
from src.core.concept_loader import load_concept, get_element_alias_map
from src.domain.models.extraction import (
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
)
from src.core.schema_loader import load_methodology

log = structlog.get_logger(__name__)


class ExtractionService:
    """
    Service for extracting concepts and relationships from text.

    Uses LLM to identify knowledge graph elements from user responses.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        skip_extractability_check: bool = False,
        min_word_count: int = 3,
        methodology: Optional[str] = None,
        concept_id: Optional[str] = None,
    ):
        """
        Initialize extraction service.

        Args:
            llm_client: LLM client instance (creates default if None)
            skip_extractability_check: Skip fast pre-filter (for testing)
            min_word_count: Minimum words for extractability
            methodology: Methodology schema name (e.g., "means_end_chain", "jobs_to_be_done")
                       DEPRECATED: Will be set dynamically from session context
            concept_id: Optional concept ID for element linking
        """
        self.llm = llm_client or get_extraction_llm_client()
        self.skip_extractability_check = skip_extractability_check
        self.min_word_count = min_word_count

        # P0 Fix: Methodology mismatch - remove hardcoded default
        # Methodology will be updated from session context in ExtractionStage
        if methodology is None:
            # Temporary fallback for backward compatibility
            # ExtractionStage will update this before first use
            log.warning(
                "extraction_service_no_methodology",
                message="No methodology provided - will be set from session context",
            )
            methodology = "means_end_chain"  # Temporary default for initialization

        self.methodology = methodology
        self.schema = load_methodology(methodology)
        self.concept_id = concept_id

        # Load concept for element linking if provided
        self.concept = None
        self.element_alias_map = {}
        if concept_id:
            try:
                self.concept = load_concept(concept_id)
                self.element_alias_map = get_element_alias_map(self.concept)
                log.info(
                    "extraction_service_concept_loaded",
                    concept_id=concept_id,
                    element_count=len(self.concept.elements),
                )
            except Exception as e:
                log.warning(
                    "concept_load_failed",
                    concept_id=concept_id,
                    error=str(e),
                )

        log.info(
            "extraction_service_initialized",
            methodology=methodology,
            node_types=len(self.schema.node_types),
        )

    async def extract(
        self,
        text: str,
        context: str = "",
        source_utterance_id: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract concepts and relationships from text.

        Full pipeline:
        1. Fast heuristic check (word count, yes/no detection)
        2. LLM extractability assessment (if heuristics pass)
        3. Full LLM extraction
        4. Parse and validate results

        Args:
            text: User's response text
            context: Optional context from previous turns
            source_utterance_id: Source utterance ID for traceability (ADR-010 Phase 2)

        Returns:
            ExtractionResult with concepts, relationships, and metadata
        """
        start_time = time.perf_counter()
        log.info("extraction_started", text_length=len(text))

        # Step 1: Fast heuristic check
        if not self.skip_extractability_check:
            is_extractable, reason = self._fast_extractability_check(text)
            if not is_extractable:
                log.info("extraction_skipped_heuristic", reason=reason)
                return ExtractionResult(
                    is_extractable=False,
                    extractability_reason=reason,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                )

        # Step 2: LLM extractability check (optional, can skip for speed)
        # Skipping for v2 MVP - heuristics are sufficient

        # Step 3: Full extraction via LLM
        try:
            extraction_data = await self._extract_via_llm(text, context)
        except Exception as e:
            log.error("extraction_llm_error", error=str(e))
            # Graceful degradation: return empty result
            return ExtractionResult(
                is_extractable=True,
                extractability_reason=f"LLM error: {e}",
                latency_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Step 4: Convert to domain models
        # ADR-010 Phase 2: Pass source_utterance_id for traceability
        concepts = self._parse_concepts(
            extraction_data.get("concepts", []),
            source_utterance_id or "unknown",
            self.schema,
        )

        # Build concept_types map for relationship validation
        concept_types = {c.text.lower(): c.node_type for c in concepts}

        relationships = self._parse_relationships(
            extraction_data.get("relationships", []),
            concept_types,
            source_utterance_id or "unknown",  # ADR-010 Phase 2: Traceability
        )
        discourse_markers = extraction_data.get("discourse_markers", [])

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        log.info(
            "extraction_complete",
            concept_count=len(concepts),
            relationship_count=len(relationships),
            latency_ms=latency_ms,
        )

        return ExtractionResult(
            concepts=concepts,
            relationships=relationships,
            discourse_markers=discourse_markers,
            is_extractable=True,
            latency_ms=latency_ms,
        )

    def _fast_extractability_check(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Fast heuristic check for extractability.

        Args:
            text: Input text

        Returns:
            (is_extractable, reason) tuple
        """
        # Word count check
        word_count = len(text.split())
        if word_count < self.min_word_count:
            return False, f"Too short ({word_count} words)"

        # Yes/no response check
        normalized = text.lower().strip()
        yes_no_responses = {
            "yes",
            "no",
            "yeah",
            "nope",
            "yep",
            "nah",
            "sure",
            "okay",
            "ok",
            "fine",
            "right",
            "uh huh",
            "mm hmm",
            "mhm",
        }
        if normalized in yes_no_responses:
            return False, "Yes/no or minimal response"

        # Single word check
        if word_count == 1:
            return False, "Single word response"

        return True, None

    async def _extract_via_llm(self, text: str, context: str) -> dict:
        """
        Call LLM for extraction.

        Args:
            text: Text to extract from
            context: Optional context

        Returns:
            Parsed extraction data dict

        Raises:
            ValueError: If LLM response is invalid
        """
        system_prompt = get_extraction_system_prompt(
            methodology=self.methodology,
            concept_id=self.concept_id,
        )
        user_prompt = get_extraction_user_prompt(text, context)

        response = await self.llm.complete(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_tokens=2000,
        )

        return parse_extraction_response(response.content)

    def _parse_concepts(
        self, raw_concepts: List[dict], source_utterance_id: str, schema
    ) -> List[ExtractedConcept]:
        """
        Convert raw extraction data to ExtractedConcept models.

        Args:
            raw_concepts: List of concept dicts from LLM
            source_utterance_id: Source utterance ID for traceability (ADR-010 Phase 2)
            schema: Methodology schema for validation and metadata

        Returns:
            List of ExtractedConcept models
        """
        concepts = []
        for raw in raw_concepts:
            try:
                # Get linked_elements from LLM (fallback to empty list)
                linked_elements = raw.get("linked_elements", [])
                if not isinstance(linked_elements, list):
                    linked_elements = []

                # Fallback: if LLM didn't link, use alias matching
                if not linked_elements and self.element_alias_map:
                    text_lower = raw.get("text", "").lower()
                    matched_elements = set()

                    # Check each alias for substring match
                    for alias, element_id in self.element_alias_map.items():
                        if alias in text_lower or text_lower in alias:
                            matched_elements.add(element_id)

                    linked_elements = list(matched_elements)
                    if linked_elements:
                        log.debug(
                            "concept_linked_via_alias_fallback",
                            text=raw.get("text", ""),
                            linked_elements=linked_elements,
                        )

                node_type = raw.get("node_type", "attribute")

                concept = ExtractedConcept(
                    text=raw.get("text", ""),
                    node_type=node_type,
                    confidence=float(raw.get("confidence", 0.8)),
                    source_quote=raw.get("source_quote", ""),
                    source_utterance_id=source_utterance_id,  # ADR-010 Phase 2: Traceability
                    properties=raw.get("properties", {}),
                    linked_elements=linked_elements,
                    stance=int(raw.get("stance", 0)),  # Default to neutral (0)
                )

                # Schema validation: check node type is valid
                if not schema.is_valid_node_type(concept.node_type):
                    log.warning(
                        "invalid_node_type",
                        node_type=concept.node_type,
                        text=concept.text,
                    )
                    continue  # Skip invalid concept

                # Set is_terminal and level from schema
                concept.is_terminal = schema.is_terminal_node_type(node_type)
                concept.level = schema.get_level_for_node_type(node_type)

                if concept.text:  # Skip empty concepts
                    concepts.append(concept)
            except Exception as e:
                log.warning("concept_parse_error", raw=raw, error=str(e))

        return concepts

    def _parse_relationships(
        self,
        raw_relationships: List[dict],
        concept_types: Dict[str, str],
        source_utterance_id: str,
    ) -> List[ExtractedRelationship]:
        """
        Convert raw extraction data to ExtractedRelationship models.

        Args:
            raw_relationships: List of relationship dicts from LLM
            concept_types: Map from concept text (lowercase) to node type
            source_utterance_id: Source utterance ID for traceability (ADR-010 Phase 2)

        Returns:
            List of ExtractedRelationship models
        """
        relationships = []
        for raw in raw_relationships:
            try:
                rel = ExtractedRelationship(
                    source_text=raw.get("source_text", ""),
                    target_text=raw.get("target_text", ""),
                    relationship_type=raw.get("relationship_type", "leads_to"),
                    confidence=float(raw.get("confidence", 0.7)),
                    reasoning=raw.get(
                        "reasoning"
                    ),  # ADR-010 Phase 2: Why edge was created
                    source_utterance_id=source_utterance_id,  # ADR-010 Phase 2: Traceability
                )

                # Schema validation: check edge type is valid
                if not self.schema.is_valid_edge_type(rel.relationship_type):
                    log.warning(
                        "invalid_edge_type",
                        relationship_type=rel.relationship_type,
                    )
                    continue  # Skip invalid edge type

                # Schema validation: check connection is allowed
                source_type = concept_types.get(rel.source_text.lower())
                target_type = concept_types.get(rel.target_text.lower())

                if source_type and target_type:
                    if not self.schema.is_valid_connection(
                        rel.relationship_type, source_type, target_type
                    ):
                        log.warning(
                            "invalid_connection",
                            edge_type=rel.relationship_type,
                            source_type=source_type,
                            target_type=target_type,
                        )
                        continue  # Skip invalid connection

                if rel.source_text and rel.target_text:  # Skip incomplete
                    relationships.append(rel)
            except Exception as e:
                log.warning("relationship_parse_error", raw=raw, error=str(e))

        return relationships

    async def assess_extractability(self, text: str) -> tuple[bool, str]:
        """
        Assess whether text is extractable using LLM.

        More expensive than heuristics but more accurate.

        Args:
            text: Text to assess

        Returns:
            (is_extractable, reason) tuple
        """
        # First do fast check
        is_extractable, reason = self._fast_extractability_check(text)
        if not is_extractable:
            return is_extractable, reason or ""

        # Then LLM check
        try:
            system_prompt = get_extractability_system_prompt(self.methodology)
            user_prompt = get_extractability_user_prompt(text)

            response = await self.llm.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.1,
                max_tokens=100,
            )

            return parse_extractability_response(response.content)
        except Exception as e:
            log.warning("extractability_llm_error", error=str(e))
            # Default to extractable on error
            return True, "LLM check failed, assuming extractable"
