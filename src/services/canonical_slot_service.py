"""
Canonical slot discovery service for dual-graph architecture.

Abstracts surface-level KGNodes into stable canonical slots via:
- LLM-proposed slot groupings with granular, specific categories
- Embedding similarity for merging near-duplicates and grammatical variants
- Candidate promotion based on support_count thresholds

Preserves node_type for methodology-aware slot discovery and edge aggregation.
"""

import json
from collections import defaultdict
from typing import List, Dict

import structlog

from src.core.config import settings
from src.core.schema_loader import load_methodology
from src.domain.models.canonical_graph import CanonicalSlot
from src.domain.models.knowledge_graph import KGNode
from src.llm.client import LLMClient
from src.persistence.repositories.canonical_slot_repo import CanonicalSlotRepository
from src.services.embedding_service import EmbeddingService

log = structlog.get_logger(__name__)


class CanonicalSlotService:
    """LLM-based canonical slot discovery for dual-graph architecture.

    Abstracts surface KGNodes into stable canonical slots to handle respondent
    language variation. Uses LLM for slot proposal and embedding similarity
    for merging near-duplicates and grammatical variants.

    Lifecycle:
    - Candidate slots created from LLM proposals
    - Merged via embedding similarity (spaCy en_core_web_md)
    - Promoted to active when support_count >= canonical_min_support_nodes

    Node Type Preservation:
        node_type preserved from surface nodes to enable methodology-aware
        slot discovery and type-specific edge aggregation.

    Dependencies:
        LLMClient: Propose canonical slot groupings
        CanonicalSlotRepository: CRUD operations on slots and mappings
        EmbeddingService: Compute embeddings for similarity matching
    """

    def __init__(
        self,
        llm_client: LLMClient,
        slot_repo: CanonicalSlotRepository,
        embedding_service: EmbeddingService,
    ):
        self.llm = llm_client
        self.slot_repo = slot_repo
        self.embedding_service = embedding_service

    async def discover_slots_for_nodes(
        self,
        session_id: str,
        surface_nodes: List[KGNode],
        turn_number: int,
        methodology: str,
    ) -> List[CanonicalSlot]:
        """Discover canonical slots via node_type grouping and LLM proposal.

        Groups surface nodes by node_type, then discovers slots per type
        using LLM proposals and embedding similarity matching. Each surface
        node maps to exactly one canonical slot (one-to-one relationship).

        Args:
            session_id: Session identifier for slot scoping
            surface_nodes: Surface KGNodes extracted this turn
            turn_number: Current turn number for promotion tracking
            methodology: Methodology name for node_type descriptions (e.g., 'means_end_chain')

        Returns:
            List of all discovered or matched CanonicalSlot objects

        Raises:
            ValueError: If any surface node has empty or missing node_type
        """
        if not surface_nodes:
            return []

        # Group by node_type
        groups: Dict[str, List[KGNode]] = defaultdict(list)
        for node in surface_nodes:
            if not node.node_type:
                raise ValueError(f"Surface node {node.id} has empty node_type")
            groups[node.node_type].append(node)

        # Discover slots per type
        all_slots: List[CanonicalSlot] = []
        for node_type, nodes in groups.items():
            slots = await self._discover_slots_for_type(
                session_id, node_type, nodes, turn_number, methodology
            )
            all_slots.extend(slots)

        log.info(
            "slots_discovered",
            session_id=session_id,
            turn=turn_number,
            total_slots=len(all_slots),
            per_type={nt: len(ns) for nt, ns in groups.items()},
        )

        return all_slots

    async def _discover_slots_for_type(
        self,
        session_id: str,
        node_type: str,
        surface_nodes: List[KGNode],
        turn_number: int,
        methodology: str,
    ) -> List[CanonicalSlot]:
        """Discover canonical slots for surface nodes of a single node_type.

        Workflow:
        1. Load node_type description from methodology schema for LLM context
        2. Fetch existing active slots to enable reuse
        3. LLM proposes granular slot groupings for surface nodes
        4. Find or create each proposed slot via embedding similarity

        Args:
            session_id: Session identifier for slot scoping
            node_type: Methodology node type (e.g., 'attribute', 'consequence')
            surface_nodes: Surface KGNodes of this type to process
            turn_number: Current turn number for promotion tracking
            methodology: Methodology name for node_type descriptions

        Returns:
            List of CanonicalSlot objects (existing matched or newly created)
        """
        # Get node type description from methodology schema
        schema = load_methodology(methodology)
        node_descriptions = schema.get_node_descriptions()
        node_type_description = node_descriptions.get(node_type, node_type)

        # Get existing slot names for LLM context (helps reuse)
        active_slots = await self.slot_repo.get_active_slots(session_id, node_type)
        existing_slot_names = [s.slot_name for s in active_slots]

        # LLM proposes slot groupings
        proposals = await self._llm_propose_slots(
            surface_nodes, node_type, node_type_description, existing_slot_names
        )

        # Find or create each proposed slot
        slots: List[CanonicalSlot] = []
        for proposal in proposals:
            slot = await self._find_or_create_slot(
                session_id=session_id,
                node_type=node_type,
                proposed_name=proposal["slot_name"],
                description=proposal["description"],
                surface_node_ids=proposal["surface_node_ids"],
                turn_number=turn_number,
            )
            slots.append(slot)

        return slots

    async def _llm_propose_slots(
        self,
        surface_nodes: List[KGNode],
        node_type: str,
        node_type_description: str,
        existing_slot_names: List[str],
    ) -> List[Dict]:
        """Propose canonical slot groupings using LLM analysis.

        Instructs LLM to create granular, specific categories (not broad)
        and reuse existing slots when applicable. Returns structured JSON
        with slot names, descriptions, and surface node assignments.

        Args:
            surface_nodes: Surface KGNodes to group into slots
            node_type: Methodology node type for categorization
            node_type_description: Human-readable node type description for LLM context
            existing_slot_names: Active slot names to encourage reuse

        Returns:
            List of dicts with keys: slot_name, description, surface_node_ids

        Raises:
            ValueError: If LLM returns invalid JSON or unexpected structure
        """
        # Build surface nodes list
        nodes_text = "\n".join(f"- {node.id}: {node.label}" for node in surface_nodes)

        # Build existing slots context
        if existing_slot_names:
            existing_text = "\n".join(f"- {name}" for name in existing_slot_names)
            existing_section = (
                f"\n## Existing Canonical Slots (reuse if applicable):\n"
                f"{existing_text}\n"
            )
        else:
            existing_section = ""

        prompt = (
            f"You are analyzing interview-extracted concepts of type "
            f'"{node_type}" ({node_type_description}).\n\n'
            f"## Surface Nodes:\n{nodes_text}\n"
            f"{existing_section}\n"
            f"## Task:\n"
            f"Group the surface nodes into SPECIFIC, GRANULAR canonical slots.\n\n"
            f"Rules:\n"
            f"- Create specific, focused categories\n"
            f"- NOT broad categories\n"
            f"- Use snake_case for slot names (2-3 words)\n"
            f"- Each surface node should be assigned to exactly one slot\n"
            f"- Reuse existing slots when a surface node matches them\n\n"
            f"Respond with ONLY valid JSON:\n"
            f"{{\n"
            f'  "proposed_slots": [\n'
            f"    {{\n"
            f'      "slot_name": "example_slot",\n'
            f'      "description": "Brief description of the concept",\n'
            f'      "surface_node_ids": ["id1", "id2"]\n'
            f"    }}\n"
            f"  ]\n"
            f"}}"
        )

        system = (
            "You are a qualitative research analyst grouping interview "
            "concepts into canonical categories. Respond with valid JSON only."
        )

        response = await self.llm.complete(
            prompt=prompt,
            system=system,
            temperature=0.3,
            max_tokens=2000,
        )

        return self._parse_slot_proposals(response.content)

    def _parse_slot_proposals(self, raw_response: str) -> List[Dict]:
        """Parse LLM JSON response into structured slot proposals.

        Handles markdown code blocks (```json...```) and validates structure.
        Follows parse_extraction_response pattern from extraction.py for
        consistent error handling.

        Args:
            raw_response: Raw LLM response text containing JSON

        Returns:
            List of validated proposal dicts with slot_name, description, surface_node_ids

        Raises:
            ValueError: If response is not valid JSON or has unexpected structure
        """
        text = raw_response.strip()

        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON from slot discovery LLM: {e}\n"
                f"Raw response: {raw_response[:500]}"
            )

        if not isinstance(data, dict) or "proposed_slots" not in data:
            raise ValueError(
                f"Expected {{'proposed_slots': [...]}} structure, "
                f"got: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
            )

        proposals = data["proposed_slots"]
        if not isinstance(proposals, list):
            raise ValueError(
                f"proposed_slots must be a list, got {type(proposals).__name__}"
            )

        # Validate each proposal
        for i, proposal in enumerate(proposals):
            for key in ("slot_name", "description", "surface_node_ids"):
                if key not in proposal:
                    raise ValueError(f"Proposal {i} missing required key '{key}'")

        return proposals

    def _lemmatize_name(self, name: str) -> str:
        """
        Lemmatize a slot name to normalize grammatical variants.

        Processes each underscore-separated word independently to avoid
        context-sensitive POS tagging (spaCy tags "reduced" as ADJ in
        "reduced inflammation" but as VERB when standalone, giving
        different lemmas).

        Uses the spaCy model already loaded by EmbeddingService.

        Bead: 00cw (reduce canonical slot fragmentation)
        """
        nlp = self.embedding_service.nlp
        words = name.split("_")
        lemmas = [nlp(word)[0].lemma_.lower() for word in words]
        return "_".join(lemmas)

    async def _find_or_create_slot(
        self,
        session_id: str,
        node_type: str,
        proposed_name: str,
        description: str,
        surface_node_ids: List[str],
        turn_number: int,
    ) -> CanonicalSlot:
        """Find existing similar slot or create new candidate via embedding similarity.

        Resolution pipeline:
        1. Lemmatize proposed_name to normalize grammatical variants (reduce/reduced)
        2. Check for exact lemmatized match to prevent UNIQUE violations
        3. If no exact match, search by embedding similarity (active + candidate)
        4. Merge into best match or create new candidate
        5. Map all surface nodes to resulting slot
        6. Promote to active if support_count >= canonical_min_support_nodes

        Args:
            session_id: Session identifier for slot scoping
            node_type: Methodology node type for slot categorization
            proposed_name: LLM-proposed slot name (will be lemmatized)
            description: LLM-proposed slot description
            surface_node_ids: Surface node IDs to map to this slot
            turn_number: Current turn number for promotion tracking

        Returns:
            Matched existing CanonicalSlot or newly created slot (may be promoted)
        """
        # Lemmatize to normalize grammatical variants
        original_proposed_name = proposed_name
        proposed_name = self._lemmatize_name(proposed_name)

        # Check for exact match first to prevent duplicates
        existing_slot = await self.slot_repo.find_slot_by_name_and_type(
            session_id, proposed_name, node_type
        )
        if existing_slot is not None:
            # Exact match found - use existing slot
            slot = existing_slot

            # Map each surface node to this existing slot
            for node_id in surface_node_ids:
                await self.slot_repo.map_surface_to_slot(
                    surface_node_id=node_id,
                    slot_id=slot.id,
                    similarity_score=1.0,  # Perfect match (exact name)
                    assigned_turn=turn_number,
                )

            log.debug(
                "canonical_slot_discovery",
                proposed_slot=original_proposed_name,
                matched_slot=slot.slot_name,
                similarity=1.0,
                threshold=settings.canonical_similarity_threshold,
                outcome="exact_match",
                surface_node_count=len(surface_node_ids),
            )

            log.info(
                "slot_found_exact",
                slot_name=slot.slot_name,
                slot_id=slot.id,
                surface_count=len(surface_node_ids),
            )

            # Check promotion (re-read for updated support_count)
            updated_slot = await self.slot_repo.get_slot(slot.id)
            if updated_slot is None:
                raise RuntimeError(f"Slot {slot.id} not found after mapping")

            if (
                updated_slot.status == "candidate"
                and updated_slot.support_count >= settings.canonical_min_support_nodes
            ):
                await self.slot_repo.promote_slot(updated_slot.id, turn_number)
                log.info(
                    "slot_promoted",
                    slot_name=updated_slot.slot_name,
                    slot_id=updated_slot.id,
                    support_count=updated_slot.support_count,
                )
                # Re-read to get promoted status
                updated_slot = await self.slot_repo.get_slot(slot.id)
                if updated_slot is None:
                    raise RuntimeError(f"Slot {slot.id} not found after promotion")

            return updated_slot

        # No exact match - proceed with similarity search
        # Embed name + description for richer semantic signal (gjb5)
        embedding = await self.embedding_service.encode(
            f"{proposed_name} :: {description}"
        )

        # Find similar existing slots (both statuses)
        active_matches = await self.slot_repo.find_similar_slots(
            session_id, node_type, embedding, status="active"
        )
        candidate_matches = await self.slot_repo.find_similar_slots(
            session_id, node_type, embedding, status="candidate"
        )

        # Combine and sort descending by similarity
        all_matches = active_matches + candidate_matches
        all_matches.sort(key=lambda x: x[1], reverse=True)

        if all_matches:
            # Merge into best match
            best_slot, best_similarity = all_matches[0]
            slot = best_slot

            # Map each surface node to this slot
            for node_id in surface_node_ids:
                await self.slot_repo.map_surface_to_slot(
                    surface_node_id=node_id,
                    slot_id=slot.id,
                    similarity_score=best_similarity,
                    assigned_turn=turn_number,
                )

            log.debug(
                "canonical_slot_discovery",
                proposed_slot=original_proposed_name,
                matched_slot=slot.slot_name,
                similarity=round(best_similarity, 4),
                threshold=settings.canonical_similarity_threshold,
                outcome="merged",
                surface_node_count=len(surface_node_ids),
            )

            log.info(
                "slot_merged",
                slot_name=slot.slot_name,
                slot_id=slot.id,
                similarity=round(best_similarity, 3),
                surface_count=len(surface_node_ids),
            )
        else:
            # Create new candidate slot
            slot = await self.slot_repo.create_slot(
                session_id=session_id,
                slot_name=proposed_name,
                description=description,
                node_type=node_type,
                first_seen_turn=turn_number,
                embedding=embedding,
            )

            # Map surface nodes to the new slot
            for node_id in surface_node_ids:
                await self.slot_repo.map_surface_to_slot(
                    surface_node_id=node_id,
                    slot_id=slot.id,
                    similarity_score=1.0,  # Perfect match (slot created from these nodes)
                    assigned_turn=turn_number,
                )

            log.debug(
                "canonical_slot_discovery",
                proposed_slot=original_proposed_name,
                matched_slot=None,
                similarity=None,
                threshold=settings.canonical_similarity_threshold,
                outcome="new_candidate",
                surface_node_count=len(surface_node_ids),
            )

            log.info(
                "slot_created",
                slot_name=slot.slot_name,
                slot_id=slot.id,
                surface_count=len(surface_node_ids),
            )

        # Check promotion: re-read slot for updated support_count
        updated_slot = await self.slot_repo.get_slot(slot.id)
        if updated_slot is None:
            raise RuntimeError(f"Slot {slot.id} not found after mapping")

        if (
            updated_slot.status == "candidate"
            and updated_slot.support_count >= settings.canonical_min_support_nodes
        ):
            await self.slot_repo.promote_slot(updated_slot.id, turn_number)
            log.info(
                "slot_promoted",
                slot_name=updated_slot.slot_name,
                slot_id=updated_slot.id,
                support_count=updated_slot.support_count,
            )
            # Re-read to get promoted status
            updated_slot = await self.slot_repo.get_slot(slot.id)
            if updated_slot is None:
                raise RuntimeError(f"Slot {slot.id} not found after promotion")

        return updated_slot
