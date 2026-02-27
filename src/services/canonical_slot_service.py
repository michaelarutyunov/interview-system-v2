"""
Canonical slot discovery service for dual-graph architecture.

Abstracts surface-level KGNodes into stable canonical slots via:
- LLM-proposed slot groupings with granular, specific categories (batched per turn)
- Embedding similarity for merging near-duplicates and grammatical variants
- Candidate promotion based on support_count thresholds

Preserves node_type for methodology-aware slot discovery and edge aggregation.
"""

import asyncio
import json
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

# Max surface nodes to process in a single LLM call to avoid timeouts
# Remaining nodes will be processed in subsequent turns
MAX_SLOT_DISCOVERY_BATCH_SIZE = 8


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
        """Discover canonical slots via a single batched LLM call across all node types.

        Groups surface nodes by node_type, fetches existing slots per type in
        parallel, then issues ONE LLM call covering all types. Proposals are
        processed per type via embedding similarity matching.

        Args:
            session_id: Session identifier for slot scoping
            surface_nodes: Surface KGNodes extracted this turn
            turn_number: Current turn number for promotion tracking
            methodology: Methodology name for node_type descriptions

        Returns:
            List of all discovered or matched CanonicalSlot objects

        Raises:
            ValueError: If any surface node has empty or missing node_type
        """
        if not surface_nodes:
            return []

        # Group by node_type
        groups: Dict[str, List[KGNode]] = {}
        for node in surface_nodes:
            if not node.node_type:
                raise ValueError(f"Surface node {node.id} has empty node_type")
            groups.setdefault(node.node_type, []).append(node)

        # Limit batch size to avoid LLM timeouts - process remaining nodes in subsequent turns
        total_nodes = sum(len(nodes) for nodes in groups.values())
        if total_nodes > MAX_SLOT_DISCOVERY_BATCH_SIZE:
            log.warning(
                "slot_discovery_batch_limited",
                total_nodes=total_nodes,
                batch_size=MAX_SLOT_DISCOVERY_BATCH_SIZE,
                session_id=session_id,
                turn=turn_number,
            )
            # Flatten, truncate, and regroup
            all_nodes = [node for nodes in groups.values() for node in nodes][
                :MAX_SLOT_DISCOVERY_BATCH_SIZE
            ]
            groups = {}
            for node in all_nodes:
                groups.setdefault(node.node_type, []).append(node)

        # Load schema once for all types
        schema = load_methodology(methodology)
        node_descriptions = schema.get_node_descriptions()

        # Fetch existing active slots per type concurrently (cheap DB queries)
        node_types = list(groups.keys())
        slot_lists = await asyncio.gather(
            *[self.slot_repo.get_active_slots(session_id, nt) for nt in node_types]
        )
        existing_slots_per_type = {
            nt: [s.slot_name for s in slots]
            for nt, slots in zip(node_types, slot_lists)
        }

        # Single batched LLM call for all node types
        proposals_per_type = await self._llm_propose_slots_batched(
            groups, node_descriptions, existing_slots_per_type
        )

        # Find or create slots for each type's proposals
        all_slots: List[CanonicalSlot] = []
        for node_type, proposals in proposals_per_type.items():
            valid_node_ids = {n.id for n in groups.get(node_type, [])}
            for proposal in proposals:
                # Guard against LLM returning IDs from other types
                surface_ids = [
                    nid for nid in proposal["surface_node_ids"] if nid in valid_node_ids
                ]
                if not surface_ids:
                    continue
                slot = await self._find_or_create_slot(
                    session_id=session_id,
                    node_type=node_type,
                    proposed_name=proposal["slot_name"],
                    description=proposal["description"],
                    surface_node_ids=surface_ids,
                    turn_number=turn_number,
                )
                all_slots.append(slot)

        log.info(
            "slots_discovered",
            session_id=session_id,
            turn=turn_number,
            total_slots=len(all_slots),
            per_type={nt: len(ns) for nt, ns in groups.items()},
        )

        return all_slots

    async def _llm_propose_slots_batched(
        self,
        groups: Dict[str, List[KGNode]],
        node_descriptions: Dict[str, str],
        existing_slots_per_type: Dict[str, List[str]],
    ) -> Dict[str, List[Dict]]:
        """Single LLM call proposing slot groupings for all node types.

        Combines all node types and their surface nodes into one prompt,
        reducing N sequential LLM calls (one per type) to a single round-trip.

        Args:
            groups: Map of node_type → List[KGNode]
            node_descriptions: Map of node_type → human-readable description
            existing_slots_per_type: Map of node_type → existing active slot names

        Returns:
            Map of node_type → List[proposal dicts] (slot_name, description, surface_node_ids)

        Raises:
            ValueError: If LLM returns invalid JSON or unexpected structure
        """
        # Build concepts section grouped by type
        concepts_section = ""
        for node_type, nodes in groups.items():
            desc = node_descriptions.get(node_type, node_type)
            concepts_section += f"\n### {node_type} ({desc}):\n"
            concepts_section += "\n".join(f"- {n.id}: {n.label}" for n in nodes) + "\n"

        # Build existing slots context (only if any exist)
        existing_lines = [
            f"### {nt}: {', '.join(names)}"
            for nt, names in existing_slots_per_type.items()
            if names
        ]
        existing_section = (
            "\n## Existing Canonical Slots (reuse if applicable):\n"
            + "\n".join(existing_lines)
            + "\n"
            if existing_lines
            else ""
        )

        # Build example JSON — show concrete slot structure for first type,
        # collapsed placeholder for the rest (prevents LLM from guessing field names)
        slot_example = (
            '{"slot_name": "example_slot", '
            '"description": "Brief description of the concept", '
            '"surface_node_ids": ["id1", "id2"]}'
        )
        type_entries_parts = []
        for i, nt in enumerate(groups):
            if i == 0:
                type_entries_parts.append(
                    f'"{nt}": {{\n      "proposed_slots": [\n        {slot_example}\n      ]\n    }}'
                )
            else:
                type_entries_parts.append(
                    f'"{nt}": {{"proposed_slots": [...same structure...]}}'
                )
        type_entries = ",\n    ".join(type_entries_parts)

        prompt = (
            f"You are analyzing interview-extracted concepts grouped by type.\n\n"
            f"## Concepts by Type:\n{concepts_section}"
            f"{existing_section}\n"
            f"## Task:\n"
            f"Group each type's concepts into SPECIFIC, GRANULAR canonical slots.\n\n"
            f"Rules:\n"
            f"- Create specific, focused categories (NOT broad)\n"
            f"- Use snake_case for slot names (2-3 words)\n"
            f"- Each surface node assigned to exactly one slot within its type\n"
            f"- Reuse existing slots when a surface node matches them\n\n"
            f"Respond with ONLY valid JSON:\n"
            f'{{\n  "groupings": {{\n    {type_entries}\n  }}\n}}'
        )

        system = (
            "You are a qualitative research analyst grouping interview "
            "concepts into canonical categories. Respond with valid JSON only."
        )

        # Use extended timeout for slot discovery (complex reasoning + JSON generation)
        response = await self.llm.complete(
            prompt=prompt,
            system=system,
            temperature=0.3,
            max_tokens=2000,
            timeout=60.0,
        )

        return self._parse_batched_proposals(response.content)

    def _parse_batched_proposals(self, raw_response: str) -> Dict[str, List[Dict]]:
        """Parse batched LLM JSON response into per-type proposal lists.

        Handles markdown code blocks and validates structure.

        Args:
            raw_response: Raw LLM response containing JSON

        Returns:
            Map of node_type → List[proposal dicts] (slot_name, description, surface_node_ids)

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
                f"Invalid JSON from batched slot discovery LLM: {e}\n"
                f"Raw response: {raw_response[:500]}"
            )

        if not isinstance(data, dict) or "groupings" not in data:
            raise ValueError(
                f'Expected {{"groupings": {{...}}}} structure, '
                f"got: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
            )

        groupings = data["groupings"]
        if not isinstance(groupings, dict):
            raise ValueError(
                f"groupings must be a dict, got {type(groupings).__name__}"
            )

        result: Dict[str, List[Dict]] = {}
        for node_type, type_data in groupings.items():
            if not isinstance(type_data, dict) or "proposed_slots" not in type_data:
                raise ValueError(
                    f"node_type '{node_type}' missing 'proposed_slots' key"
                )
            proposals = type_data["proposed_slots"]
            if not isinstance(proposals, list):
                raise ValueError(f"proposed_slots for '{node_type}' must be a list")
            for i, proposal in enumerate(proposals):
                for key in ("slot_name", "description", "surface_node_ids"):
                    if key not in proposal:
                        raise ValueError(
                            f"Proposal {i} for '{node_type}' missing required key '{key}'"
                        )
            result[node_type] = proposals

        return result

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
