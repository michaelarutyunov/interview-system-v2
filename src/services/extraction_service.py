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
from typing import Optional, List

import structlog

from src.llm.client import LLMClient, get_llm_client
from src.llm.prompts.extraction import (
    get_extraction_system_prompt,
    get_extraction_user_prompt,
    get_extractability_system_prompt,
    get_extractability_user_prompt,
    parse_extraction_response,
    parse_extractability_response,
)
from src.domain.models.extraction import (
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
)

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
    ):
        """
        Initialize extraction service.

        Args:
            llm_client: LLM client instance (creates default if None)
            skip_extractability_check: Skip fast pre-filter (for testing)
            min_word_count: Minimum words for extractability
        """
        self.llm = llm_client or get_llm_client()
        self.skip_extractability_check = skip_extractability_check
        self.min_word_count = min_word_count

        log.info("extraction_service_initialized")

    async def extract(
        self,
        text: str,
        context: str = "",
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
        concepts = self._parse_concepts(extraction_data.get("concepts", []))
        relationships = self._parse_relationships(extraction_data.get("relationships", []))
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
            "yes", "no", "yeah", "nope", "yep", "nah",
            "sure", "okay", "ok", "fine", "right",
            "uh huh", "mm hmm", "mhm",
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
        system_prompt = get_extraction_system_prompt()
        user_prompt = get_extraction_user_prompt(text, context)

        response = await self.llm.complete(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_tokens=2000,
        )

        return parse_extraction_response(response.content)

    def _parse_concepts(self, raw_concepts: List[dict]) -> List[ExtractedConcept]:
        """
        Convert raw extraction data to ExtractedConcept models.

        Args:
            raw_concepts: List of concept dicts from LLM

        Returns:
            List of ExtractedConcept models
        """
        concepts = []
        for raw in raw_concepts:
            try:
                concept = ExtractedConcept(
                    text=raw.get("text", ""),
                    node_type=raw.get("node_type", "attribute"),
                    confidence=float(raw.get("confidence", 0.8)),
                    source_quote=raw.get("source_quote", ""),
                    properties=raw.get("properties", {}),
                )
                if concept.text:  # Skip empty concepts
                    concepts.append(concept)
            except Exception as e:
                log.warning("concept_parse_error", raw=raw, error=str(e))

        return concepts

    def _parse_relationships(
        self, raw_relationships: List[dict]
    ) -> List[ExtractedRelationship]:
        """
        Convert raw extraction data to ExtractedRelationship models.

        Args:
            raw_relationships: List of relationship dicts from LLM

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
                    source_quote=raw.get("source_quote", ""),
                )
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
            system_prompt = get_extractability_system_prompt()
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
