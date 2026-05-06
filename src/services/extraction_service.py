"""
Extraction service for concept extraction from user responses.

This service implements the knowledge extraction pipeline using LLM-based analysis
with methodology-specific schema validation. Extracted concepts are linked to
canonical elements when concept_id is provided. Relationships are handled
separately by EdgeExtractionPrefetchStage (Stage 4.5B).

Pipeline:
1. Fast extractability check (word count, yes/no detection, single word)
2. LLM-based concept extraction
3. Parse and validate results against methodology schema
4. Return ExtractionResult with metadata and traceability

Fail-fast behavior: Raises ExtractionError on LLM errors to make issues
immediately visible during testing.

Dependencies:
    - LLMClient: For extraction completions
    - MethodologySchema: For ontology validation and metadata
    - ConceptLoader: For element linking via alias matching
"""

import time
from typing import Optional, List

import structlog

from src.llm.client import LLMClient
from src.llm.prompts.extraction import (
    get_extraction_system_prompt,
    get_extraction_user_prompt,
    parse_extraction_response,
)
from src.core.concept_loader import load_concept, get_element_alias_map
from src.core.exceptions import ExtractionError
from src.domain.models.extraction import (
    ExtractedConcept,
    ExtractionResult,
)
from src.domain.models.methodology_schema import MethodologySchema
from src.core.schema_loader import load_methodology

log = structlog.get_logger(__name__)


class ExtractionService:
    """
    Extract concepts from user responses using LLM and methodology schemas.

    This service provides methodology-aware extraction with:
    - Fast extractability pre-filtering (heuristics for short responses)
    - LLM-based concept extraction
    - Schema validation against methodology ontology
    - Element linking to canonical concepts when concept_id is provided
    - Traceability via source utterance IDs

    Domain concepts:
        - Concepts: Knowledge graph nodes with types, confidence, stance
        - Relationships: Handled by EdgeExtractionPrefetchStage (Stage 4.5B)
        - Extractability: Whether text contains sufficient information
        - Element linking: Mapping concepts to methodology-defined elements
    """

    def __init__(
        self,
        llm_client: LLMClient,
        skip_extractability_check: bool = False,
        min_word_count: int = 3,
        concept_id: Optional[str] = None,
    ):
        """Initialize extraction service with LLM client and optional concept linking.

        Args:
            llm_client: LLM client for extraction completions
            skip_extractability_check: Skip fast pre-filter (for testing only)
            min_word_count: Minimum word threshold for extractability
            concept_id: Optional concept ID for element linking to canonical slots

        Note:
            Methodology is passed as a required parameter to extract()
            rather than set at initialization time to support multi-methodology sessions.
        """
        self.llm = llm_client
        self.skip_extractability_check = skip_extractability_check
        self.min_word_count = min_word_count
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
            concept_id=concept_id,
            element_count=len(self.concept.elements) if self.concept else 0,
        )

    async def extract(
        self,
        text: str,
        methodology: str,
        context: str = "",
        source_utterance_id: Optional[str] = None,
    ) -> ExtractionResult:
        """Extract concepts from user response text.

        Full pipeline:
        1. Fast heuristic check (word count, yes/no detection)
        2. LLM-based extraction with methodology-specific prompts
        3. Parse results into domain models with schema validation
        4. Link elements to concept ontology if concept_id provided
        5. Return ExtractionResult with traceability metadata

        Args:
            text: User's response text to extract from
            methodology: Methodology schema name for ontology validation
                        (e.g., "means_end_chain", "jobs_to_be_done", "critical_incident")
            context: Optional conversational context from previous turns
            source_utterance_id: Source utterance ID for provenance tracking

        Returns:
            ExtractionResult containing:
                - concepts: List of ExtractedConcept with node types and confidence
                - Relationships are now handled by Stage 4.5B (separated edge extraction)
                - is_extractable: Whether text contained extractable content
                - latency_ms: Extraction time in milliseconds

        Raises:
            ExtractionError: If LLM extraction fails or returns invalid JSON

        Domain concepts:
            - Extractability: Text sufficiency for knowledge extraction
            - Node types: Methodology-defined concept categories
            - Edge types: Methodology-defined relationship categories
            - Stance: Concept position (-1=negative, 0=neutral, +1=positive)
        """
        # Load methodology schema per-call (cached by load_methodology)
        schema = load_methodology(methodology)

        start_time = time.perf_counter()
        log.info(
            "extraction_started",
            text_length=len(text),
            methodology=methodology,
        )

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
            extraction_data = await self._extract_via_llm(text, context, methodology)
        except Exception as e:
            log.error("extraction_llm_error", error=str(e), exc_info=True)
            raise ExtractionError(f"LLM extraction failed: {e}") from e

        # Step 4: Convert to domain models
        # Pass source_utterance_id for traceability of extracted elements
        concepts = self._parse_concepts(
            extraction_data.get("concepts", []),
            source_utterance_id or "unknown",
            schema,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        log.info(
            "extraction_complete",
            concept_count=len(concepts),
            latency_ms=latency_ms,
        )

        return ExtractionResult(
            concepts=concepts,
            is_extractable=True,
            latency_ms=latency_ms,
        )

    def _fast_extractability_check(self, text: str) -> tuple[bool, Optional[str]]:
        """Perform fast heuristic check to determine if text is extractable.

        Checks three conditions that indicate insufficient content:
        1. Word count below minimum threshold
        2. Yes/no or minimal affirmative/negative responses
        3. Single word responses

        Args:
            text: User response text to evaluate

        Returns:
            (is_extractable, reason) tuple where:
                - is_extractable: True if text should be extracted
                - reason: String explanation if not extractable, None otherwise

        Domain concepts:
            - Extractability: Sufficiency of text for knowledge extraction
            - Minimal responses: Low-information utterances that don't add graph value
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

    async def _extract_via_llm(self, text: str, context: str, methodology: str) -> dict:
        """Perform LLM-based extraction with methodology-specific prompts.

        Constructs extraction prompts using methodology schema (node types,
        edge types, examples) and parses structured JSON response.

        Args:
            text: User response text to extract from
            context: Conversational context for implicit relationships
            methodology: Methodology name for prompt construction

        Returns:
            Parsed extraction data dict with:
                - concepts: List of concept dicts with text, node_type, confidence
                - relationships: List of relationship dicts with source, target, type

        Raises:
            ValueError: If LLM response is not valid JSON or missing required fields

        Implementation notes:
            - Uses low temperature (0.3) for consistent extraction
            - Max tokens 2000 for multiple concepts/relationships
            - Response parsed by parse_extraction_response() utility
        """
        schema = load_methodology(methodology)
        naming_convention = schema.get_concept_naming_convention()
        system_prompt = get_extraction_system_prompt(
            methodology=methodology,
            concept_id=self.concept_id,
            concept_naming_convention=naming_convention,
        )
        user_prompt = get_extraction_user_prompt(text, context)

        log.debug(
            "extraction_llm_prompt",
            context_length=len(context),
            prompt_length=len(user_prompt),
            has_context=bool(context),
        )

        # Build system prompt as block-list for Anthropic prompt caching.
        # Non-Anthropic providers flatten the block-list to a plain string.
        system_blocks = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        response = await self.llm.complete(
            prompt=user_prompt,
            system=system_blocks,  # type: ignore[arg-type]
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        try:
            return parse_extraction_response(response.content)
        except ValueError as e:
            # Log the raw response for debugging JSON parsing errors
            log.error(
                "extraction_json_parse_failed",
                error=str(e),
                response_preview=response.content[:1000],
                response_length=len(response.content),
            )
            raise

    def _parse_concepts(
        self,
        raw_concepts: List[dict],
        source_utterance_id: str,
        schema: MethodologySchema,
    ) -> List[ExtractedConcept]:
        """Parse and validate raw LLM output into ExtractedConcept domain models.

        Applies schema validation (node types) and enriches concepts with
        ontology metadata (level, terminal). Links concepts to canonical
        elements via alias matching fallback.

        Args:
            raw_concepts: List of concept dicts from LLM response
            source_utterance_id: Source utterance ID for provenance tracking
            schema: Methodology schema for validation and metadata lookup

        Returns:
            List of valid ExtractedConcept models (invalid concepts skipped)

        Domain concepts:
            - Node types: Methodology-defined concept categories
            - Terminal nodes: Leaf nodes in hierarchical ontologies
            - Level: Hierarchy depth (0=abstract, higher=more concrete)
            - Stance: Concept position (-1=negative, 0=neutral, +1=positive)
            - Element linking: Mapping concepts to canonical slots via aliases

        Implementation notes:
            - Skips concepts with invalid node types (logs warning)
            - Uses alias matching fallback if LLM doesn't provide linked_elements
            - Skips empty concepts (missing text field)
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
                    source_utterance_id=source_utterance_id,  # Links concept to source utterance
                    properties=raw.get("properties", {}),
                    linked_elements=linked_elements,
                    stance=raw.get(
                        "stance"
                    ),  # Deprecated: no longer extracted; llm.valence covers sentiment
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
                # Use defaults if schema returns None (missing ontology data)
                concept.is_terminal = schema.is_terminal_node_type(node_type) or False
                concept.level = schema.get_level_for_node_type(node_type) or 0

                if concept.text:  # Skip empty concepts
                    concepts.append(concept)
            except Exception as e:
                log.warning("concept_parse_error", raw=raw, error=str(e))

        return concepts
