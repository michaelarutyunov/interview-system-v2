#!/usr/bin/env python3
"""
Streaming Canonical Slot Discovery System for Interview-Extracted Nodes
Colab-ready implementation with KIMI API integration.

Colab Setup:
    !pip install sentence-transformers scikit-learn numpy requests

Then set KIMI_API_KEY in Colab secrets (left sidebar key icon).
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional
from collections import defaultdict

import numpy as np
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# =============================================================================
# CONSTANTS
# =============================================================================

SLOT_MERGE_THRESHOLD = 0.75  # This is a hyperparameter that sets the similarity threshold for merging slots
MIN_SUPPORT_NODES = 2  # This is a hyperparameter that sets the minimum number of supporting surface nodes
MIN_TURNS = 1  # This is a hyperparameter that sets the minimum number of turns for a slot to be considered active

KIMI_API_URL = "https://api.moonshot.ai/v1/chat/completions"

# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class SlotHypothesis:
    """A candidate slot that may become canonical."""
    slot_id: str
    slot_name: str
    description: str
    supported_surface_ids: Set[str] = field(default_factory=set)
    turns_seen: Set[int] = field(default_factory=set)
    embedding: Optional[np.ndarray] = None
    status: str = "candidate"  # "candidate" or "active"


@dataclass
class CanonicalSlot:
    """A confirmed canonical slot."""
    slot_id: str
    slot_name: str
    description: str
    surface_ids: Set[str] = field(default_factory=set)
    turns_seen: Set[int] = field(default_factory=set)


# =============================================================================
# INPUT DATA - HARDCODED SURFACE NODES
# =============================================================================

SURFACE_NODES = [
    {"id": "3e035ebe-8e23-4ca8-ae45-12d75ab0f4a3", "label": "minimal ingredients", "node_type": "attribute"},
    {"id": "e821e47a-417b-42c1-94ae-4f8037018b9b", "label": "no added oils", "node_type": "attribute"},
    {"id": "720c91cc-450c-4c67-9d24-6f10db00c018", "label": "low sugar content", "node_type": "attribute"},
    {"id": "3894828f-82c3-40c6-a930-9f87bdc39531", "label": "no weird additives or gums", "node_type": "attribute"},
    {"id": "b56b69ac-a837-4f3e-884c-4ace11dacc23", "label": "healthier alternative", "node_type": "functional_consequence"},
    {"id": "6d22179f-d58c-45c1-8b5a-3d6da2a2ba97", "label": "avoid added oils", "node_type": "instrumental_value"},
    {"id": "1c0b8060-604f-4c5e-805b-a208a6e4267c", "label": "excessive sugar in alternatives", "node_type": "attribute"},
    {"id": "cf2fb77f-a0cb-4085-898a-895cdc5c7abe", "label": "avoiding oils and additives", "node_type": "attribute"},
    {"id": "e0429b07-57d9-4c22-8025-e4e6d89ba4d7", "label": "processed ingredients", "node_type": "attribute"},
    {"id": "20a02fc9-c282-4d55-973b-2820f2676afc", "label": "can cause inflammation in the body", "node_type": "functional_consequence"},
    {"id": "34d82b76-1912-40f6-97c9-da13648bc0a0", "label": "feel better", "node_type": "psychosocial_consequence"},
    {"id": "cc5fd363-716f-4af4-8908-89820d9ad165", "label": "cleaner foods", "node_type": "attribute"},
    {"id": "41c84453-821f-4e14-9391-c42c87562b33", "label": "better digestion", "node_type": "functional_consequence"},
    {"id": "490f03c6-e7bb-408e-b904-9d5ad015d7c5", "label": "being mindful about what I'm putting into my body", "node_type": "instrumental_value"},
    {"id": "5ff5e713-6097-4fc9-bb67-d6908deda503", "label": "long-term health", "node_type": "terminal_value"},
    {"id": "285e4b9c-6b8f-4caf-927b-0e4e29411184", "label": "being intentional with what I put into my body", "node_type": "instrumental_value"},
    {"id": "3c7edb3d-87cf-4148-af3e-d63a09089adf", "label": "affect my energy levels", "node_type": "functional_consequence"},
    {"id": "ef4cdc22-35f3-485d-9251-594f0b7e7c5a", "label": "affect my gut health", "node_type": "functional_consequence"},
    {"id": "65652292-f892-4e86-9a68-7f434f899f21", "label": "how I age down the line", "node_type": "psychosocial_consequence"},
    {"id": "4d184b1e-593b-4e24-b5ee-256c8a86d30f", "label": "whole, minimally processed foods", "node_type": "attribute"},
    {"id": "e2789588-ee62-4b91-b670-4478305efc67", "label": "ingredients I can actually recognize and pronounce", "node_type": "attribute"},
    {"id": "5431ee81-ebe6-415a-9966-956c21660b88", "label": "being mindful", "node_type": "instrumental_value"},
    {"id": "56f1323d-e8e0-4f39-9acf-1e27781be098", "label": "treat it well", "node_type": "instrumental_value"},
    {"id": "7e525afe-0fe9-4b4b-9480-68a73d7294f8", "label": "my body is going to be with me for hopefully a long time", "node_type": "terminal_value"},
    {"id": "7f08213e-8e79-4d90-b920-315695087565", "label": "I only get one body", "node_type": "instrumental_value"},
    {"id": "36af4ec1-e322-4dbd-8269-df37fb0ce621", "label": "want it to last", "node_type": "terminal_value"},
    {"id": "6ed1d334-12a6-47d0-bab9-36d08b5c80b1", "label": "difference in energy levels", "node_type": "functional_consequence"},
    {"id": "f876bc6d-50e9-4bbd-8b2d-bf7718a40fa7", "label": "overall how I feel", "node_type": "psychosocial_consequence"},
    {"id": "136d1f78-9713-45e1-a5c8-6d767502e2db", "label": "putting good things in versus processed stuff", "node_type": "instrumental_value"},
    {"id": "7b58a7d6-b276-450a-9809-a173d95781f1", "label": "mom dealt with health issues", "node_type": "psychosocial_consequence"},
    {"id": "5a771079-899d-4934-bbe2-91cca8dc6f8a", "label": "could've been prevented with better nutrition", "node_type": "functional_consequence"},
    {"id": "73b8bd1e-b0f6-471c-a58a-0b6eb832b01b", "label": "being proactive now", "node_type": "instrumental_value"},
    {"id": "2bb5bb0b-0c9b-48e3-895d-7285ada49f21", "label": "avoiding problems later", "node_type": "terminal_value"},
    {"id": "36cb7938-1da6-4c95-b962-810f2f1e4eb0", "label": "making intentional choices", "node_type": "instrumental_value"},
    {"id": "652f4e27-ba1e-4a1c-a1eb-c7a47811ce0b", "label": "plant-based", "node_type": "attribute"},
    {"id": "c2290692-aa49-4739-b149-1625967aa55b", "label": "easier on my digestive system", "node_type": "functional_consequence"},
    {"id": "e66f968e-44ce-412b-b74d-b06dc65f610f", "label": "has fiber", "node_type": "attribute"},
    {"id": "5a2d74e9-66b6-4923-be2f-8ecf753d3214", "label": "good for gut health", "node_type": "functional_consequence"},
    {"id": "fb6de899-38eb-4196-acc9-b95e7056695b", "label": "avoiding the hormones and antibiotics", "node_type": "functional_consequence"},
    {"id": "86b0aa7a-3b91-4f5d-beca-f271e3ff8295", "label": "daily decisions that add up", "node_type": "instrumental_value"},
    {"id": "5e71c308-7b49-46db-a70e-b5564135adab", "label": "preventing issues before they start", "node_type": "instrumental_value"},
    {"id": "dbbff737-f482-48bf-84e4-b430b20c904e", "label": "fortified with vitamins D and B12", "node_type": "attribute"},
    {"id": "c4206fd3-9699-4d0f-bf91-51364b6cb5d7", "label": "nourishing my body", "node_type": "psychosocial_consequence"},
    {"id": "ebe38f53-7db6-4928-827d-2dd5597a8e83", "label": "being intentional about what I'm putting into my body", "node_type": "instrumental_value"},
    {"id": "d73b01fa-8fdf-41a1-b99b-370b2ead8537", "label": "sustained energy throughout the day", "node_type": "functional_consequence"},
    {"id": "e026f74a-0aec-48d7-a32a-e9eb0467cec3", "label": "support my immune system", "node_type": "functional_consequence"},
    {"id": "362bd4de-b809-42d5-8774-6e7c3f4a0a70", "label": "whole ingredients that my body can actually recognize and use", "node_type": "attribute"},
    {"id": "731e2cf9-9672-4c37-8989-d112add6a70a", "label": "not empty calories", "node_type": "attribute"},
    {"id": "9f680ddc-2877-4e94-bfdb-38c7aa7aa31b", "label": "not processed stuff", "node_type": "attribute"},
    {"id": "66e7f426-944f-4f47-ba72-1023c69dae3b", "label": "feel good from the inside out", "node_type": "psychosocial_consequence"},
    {"id": "6f44d2b8-6d75-4cc4-983f-c1e919040666", "label": "feeling sluggish", "node_type": "functional_consequence"},
    {"id": "e064c817-3915-459f-b923-e215481b8efd", "label": "more energy to get through my day", "node_type": "functional_consequence"},
    {"id": "ccf0e73a-c7e6-4371-90f4-775eeeeeef39", "label": "not dealing with afternoon crash", "node_type": "functional_consequence"},
    {"id": "84fe26b0-e01d-42f4-b32d-78f608ac6583", "label": "not feeling sluggish", "node_type": "functional_consequence"},
    {"id": "6ddda529-94c8-4e22-acba-edcd13735611", "label": "can actually focus at work", "node_type": "functional_consequence"},
    {"id": "46d93088-e6bc-4dae-8979-5923726b120f", "label": "have energy to hit the gym", "node_type": "functional_consequence"},
    {"id": "093b27ba-6378-4c86-af03-c672c6fa3eb2", "label": "have energy to meet up with friends", "node_type": "functional_consequence"},
    {"id": "f2b913c9-9287-465d-9a04-4d9e4e2290d8", "label": "everything else just flows better", "node_type": "psychosocial_consequence"},
    {"id": "56bc5843-5b13-4006-a6dd-1aa1ea7c479e", "label": "feeling good", "node_type": "psychosocial_consequence"},
    {"id": "e3e4a244-8882-446c-a2a2-194478143b65", "label": "digestion working smoothly", "node_type": "functional_consequence"},
    {"id": "0faa51be-9950-4a2f-9814-d30e85933d44", "label": "more energy throughout the day", "node_type": "functional_consequence"},
    {"id": "bb20878e-b60c-4490-8005-92cf3e7554cc", "label": "not feeling bloated or sluggish", "node_type": "functional_consequence"},
    {"id": "94baa6e7-8cfd-4cb7-9718-151d6e8e4162", "label": "better workouts", "node_type": "functional_consequence"},
    {"id": "e7e353fe-8df2-4112-9e54-9eb9b692b304", "label": "better focus at work", "node_type": "functional_consequence"},
    {"id": "10dd8037-9b22-4a36-a1fc-d052d9ea8e9c", "label": "better mood", "node_type": "psychosocial_consequence"},
    {"id": "819154cf-a365-460e-a51f-a35483525d28", "label": "gut health connected to immunity and inflammation", "node_type": "functional_consequence"},
    {"id": "3db81f45-c7c0-451f-95cd-dcc388892846", "label": "keeping things regular", "node_type": "functional_consequence"},
    {"id": "e1581c72-ad88-46c7-aacf-3e556b60e791", "label": "foundational for overall wellness", "node_type": "instrumental_value"}
]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def split_into_unequal_chunks(nodes: List[dict], n_turns: int = 10, seed: int = 42) -> List[List[dict]]:
    """
    Split nodes into unequal chunks deterministically.

    Args:
        nodes: List of surface nodes to split
        n_turns: Number of chunks to create
        seed: Random seed for reproducibility

    Returns:
        List of node chunks (roughly equal sizes, preserving original order)
    """
    nodes = nodes.copy()  # Work on a copy to avoid modifying input

    # Calculate target chunk size
    base_size = len(nodes) // n_turns
    remainder = len(nodes) % n_turns

    chunks = []
    start = 0

    for i in range(n_turns):
        # First 'remainder' chunks get one extra node
        chunk_size = base_size + (1 if i < remainder else 0)
        end = start + chunk_size
        chunks.append(nodes[start:end])
        start = end

    return chunks


def embed_text(text: str, model: SentenceTransformer) -> np.ndarray:
    """
    Generate embedding for text using sentence-transformers.

    Args:
        text: Text to embed
        model: SentenceTransformer model instance

    Returns:
        Embedding vector as numpy array
    """
    return model.encode(text)


# =============================================================================
# KIMI API INTEGRATION
# =============================================================================

def propose_slots_with_kimi(surface_nodes: List[dict], existing_slot_names: List[str], api_key: str) -> List[dict]:
    """
    Call KIMI API to propose canonical slots from surface nodes.

    Args:
        surface_nodes: List of surface nodes with id, label, node_type
        existing_slot_names: List of already-discovered slot names (for reuse)
        api_key: KIMI API key

    Returns:
        List of proposed slot dicts with slot_name, description, supporting_surface_ids

    Raises:
        ValueError: If API returns invalid JSON or malformed response
    """
    # Build the context for KIMI (labels only, no node_type)
    nodes_text = "\n".join([
        f"- {n['id']}: {n['label']}"
        for n in surface_nodes
    ])

    existing_slots_text = "\n".join([
        f"- {name}" for name in existing_slot_names
    ]) if existing_slot_names else "(none yet)"

    prompt = f"""You are analyzing interview-extracted concept nodes to discover latent canonical slots (conceptual categories).

## Surface Nodes Extracted:
{nodes_text}

## Existing Canonical Slots (prefer reusing if applicable):
{existing_slots_text}

## Task:
Analyze the surface nodes above and extract latent conceptual slots that group related nodes together.

For each slot:
1. Use snake_case for slot_name (e.g., "processing_level", "energy_outcome")
2. Provide a clear description of the latent concept
3. List supporting_surface_ids - MUST be a subset of the node IDs provided above
4. Prefer reusing existing slot names if the concept matches
5. Do NOT invent slots without clear evidence in the data

## Response Format (STRICT JSON):
Return ONLY a JSON array. No markdown, no explanation outside the JSON.

[
  {{
    "slot_name": "processing_level",
    "description": "degree of processing or clean label perception",
    "supporting_surface_ids": ["id1", "id2", "id3"]
  }},
  {{
    "slot_name": "energy_outcome",
    "description": "energy-related functional consequences",
    "supporting_surface_ids": ["id4", "id5"]
  }}
]"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "moonshot-v1-8k",
        "messages": [
            {
                "role": "system",
                "content": "You are a conceptual analysis assistant. Always respond with valid JSON only - no markdown, no explanations outside the JSON."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    # Initialize for exception handlers
    content = ""
    result = {}

    try:
        response = requests.post(KIMI_API_URL, headers=headers, json=payload, timeout=60)

        # Better error handling - extract error details from response
        if not response.ok:
            try:
                error_detail = response.json()
                error_msg = error_detail.get("error", {}).get("message", str(error_detail))
            except Exception:
                error_msg = response.text
            raise ValueError(f"KIMI API returned {response.status_code}: {error_msg}")

        result = response.json()

        # Handle different response structures
        if "choices" not in result or not result["choices"]:
            raise ValueError(f"Unexpected response structure: {result}")

        content = result["choices"][0]["message"]["content"]

        # Strip markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # Parse JSON response
        proposed_slots = json.loads(content)

        # Validate structure
        if not isinstance(proposed_slots, list):
            raise ValueError("KIMI response must be a JSON array")

        for slot in proposed_slots:
            if not all(k in slot for k in ["slot_name", "description", "supporting_surface_ids"]):
                raise ValueError(f"Invalid slot structure: {slot}")

            if not isinstance(slot["supporting_surface_ids"], list):
                raise ValueError(f"supporting_surface_ids must be a list: {slot}")

            # Verify all IDs are from the input
            valid_ids = {n["id"] for n in surface_nodes}
            invalid_ids = set(slot["supporting_surface_ids"]) - valid_ids
            if invalid_ids:
                raise ValueError(f"Slot contains invalid surface IDs: {invalid_ids}")

        return proposed_slots

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from KIMI: {e}\n\nRaw content:\n{content}")
    except requests.RequestException as e:
        raise ValueError(f"KIMI API network error: {e}")
    except KeyError as e:
        raise ValueError(f"Unexpected KIMI response structure: {e}\n\nResponse: {result}")


# =============================================================================
# SLOT DISCOVERY STATE
# =============================================================================

class SlotDiscoverySystem:
    """Main system for streaming canonical slot discovery."""

    def __init__(self):
        # Core data structures
        self.slot_hypotheses: Dict[str, SlotHypothesis] = {}
        self.canonical_slots: Dict[str, CanonicalSlot] = {}
        self.surface_to_slot: Dict[str, str] = {}  # surface_id -> slot_id

        # Embedding model (lazy loaded)
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load sentence transformer model."""
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def get_existing_slot_names(self) -> List[str]:
        """Get list of all active slot names for KIMI context."""
        return [
            h.slot_name for h in self.slot_hypotheses.values()
            if h.status == "active"
        ]

    def merge_or_create_slot(self, proposed_slot: dict, current_turn: int) -> str:
        """
        Merge proposed slot into existing hypothesis or create new one.

        First checks for identical slot_name (case-insensitive) and forces merge.
        Then uses cosine similarity to find the best matching existing slot.
        Merges if similarity >= SLOT_MERGE_THRESHOLD.

        Args:
            proposed_slot: Dict with slot_name, description, supporting_surface_ids
            current_turn: Current turn number

        Returns:
            The slot_id of the merged or created slot
        """
        slot_name = proposed_slot["slot_name"]
        description = proposed_slot["description"]
        surface_ids = set(proposed_slot["supporting_surface_ids"])

        # Generate embedding for proposed slot
        slot_text = f"{slot_name} :: {description}"
        proposed_embedding = embed_text(slot_text, self.model)

        # DEBUG: Show existing slots
        existing_names = [s.slot_name for s in self.slot_hypotheses.values()]
        if existing_names:
            print(f"  [DEBUG] Existing slots: {existing_names}")

        # First check: force merge if slot_name matches (case-insensitive)
        for existing_id, existing_slot in self.slot_hypotheses.items():
            if existing_slot.slot_name.lower() == slot_name.lower():
                # Force merge on identical name
                print(f"  [FORCE-MERGE] {slot_name} -> {existing_id[:8]} (name match)")
                existing_slot.supported_surface_ids.update(surface_ids)
                existing_slot.turns_seen.add(current_turn)

                # Update surface mappings
                for surface_id in surface_ids:
                    self.surface_to_slot[surface_id] = existing_id

                return existing_id

        # Second check: find best matching existing slot by embedding similarity
        best_match_id = None
        best_similarity = -1.0

        for existing_id, existing_slot in self.slot_hypotheses.items():
            if existing_slot.embedding is None:
                continue

            similarity = cosine_similarity(
                proposed_embedding.reshape(1, -1),
                existing_slot.embedding.reshape(1, -1)
            )[0][0]

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = existing_id

        # Merge or create
        if best_match_id is not None and best_similarity >= SLOT_MERGE_THRESHOLD:
            # Merge into existing slot
            existing_slot = self.slot_hypotheses[best_match_id]
            existing_slot.supported_surface_ids.update(surface_ids)
            existing_slot.turns_seen.add(current_turn)

            # Update surface mappings
            for surface_id in surface_ids:
                self.surface_to_slot[surface_id] = best_match_id

            return best_match_id
        else:
            # Create new slot hypothesis
            new_slot_id = str(uuid.uuid4())
            new_slot = SlotHypothesis(
                slot_id=new_slot_id,
                slot_name=slot_name,
                description=description,
                supported_surface_ids=surface_ids.copy(),
                turns_seen={current_turn},
                embedding=proposed_embedding,
                status="candidate"
            )

            self.slot_hypotheses[new_slot_id] = new_slot

            # Update surface mappings
            for surface_id in surface_ids:
                self.surface_to_slot[surface_id] = new_slot_id

            return new_slot_id

    def promote_slots_if_ready(self, current_turn: int) -> List[CanonicalSlot]:
        """
        Promote eligible SlotHypotheses to CanonicalSlots.

        Promotion criteria:
        - At least MIN_SUPPORT_NODES surface nodes
        - Seen in at least MIN_TURNS turns

        Args:
            current_turn: Current turn number

        Returns:
            List of newly promoted CanonicalSlots
        """
        newly_promoted = []

        for slot_id, slot in list(self.slot_hypotheses.items()):
            if slot.status == "candidate":
                if (len(slot.supported_surface_ids) >= MIN_SUPPORT_NODES and
                        len(slot.turns_seen) >= MIN_TURNS):

                    # Promote to canonical
                    slot.status = "active"

                    canonical = CanonicalSlot(
                        slot_id=slot.slot_id,
                        slot_name=slot.slot_name,
                        description=slot.description,
                        surface_ids=slot.supported_surface_ids.copy(),
                        turns_seen=slot.turns_seen.copy()
                    )

                    self.canonical_slots[slot_id] = canonical
                    newly_promoted.append(canonical)

        return newly_promoted

    def process_turn(self, surface_chunk: List[dict], turn_id: int, api_key: str) -> dict:
        """
        Process a single turn of the interview.

        Args:
            surface_chunk: Nodes received this turn
            turn_id: Turn number (1-indexed)
            api_key: KIMI API key

        Returns:
            Dict with processing summary
        """
        print(f"\n{'=' * 60}")
        print(f"TURN {turn_id}: Processing {len(surface_chunk)} nodes")
        print(f"{'=' * 60}")

        results = {
            "turn_id": turn_id,
            "proposed_count": 0,
            "merged_count": 0,
            "created_count": 0,
            "promoted_count": 0,
            "canonical_total": len(self.canonical_slots)
        }

        if not surface_chunk:
            print("No nodes to process.")
            return results

        # 1. Get existing slot names for context
        existing_names = self.get_existing_slot_names()

        # 2. Call KIMI for slot proposals
        print("\n[KIMI] Calling API for slot proposals...")
        proposed_slots = propose_slots_with_kimi(surface_chunk, existing_names, api_key)
        results["proposed_count"] = len(proposed_slots)

        print(f"[KIMI] Proposed {len(proposed_slots)} slots:")
        for slot in proposed_slots:
            print(f"  - {slot['slot_name']}: {len(slot['supporting_surface_ids'])} nodes")

        # 3. Merge or create slots
        print("\n[MERGE] Processing proposals...")
        for proposed in proposed_slots:
            slot_id = self.merge_or_create_slot(proposed, turn_id)

            if self.slot_hypotheses[slot_id].status == "candidate":
                # Check if this was newly created
                if len(self.slot_hypotheses[slot_id].turns_seen) == 1:
                    results["created_count"] += 1
                    print(f"  + Created: {proposed['slot_name']} -> {slot_id[:8]}")
                else:
                    results["merged_count"] += 1
                    print(f"  ~ Merged: {proposed['slot_name']} -> {slot_id[:8]}")
            else:
                results["merged_count"] += 1
                print(f"  ~ Merged into active: {proposed['slot_name']} -> {slot_id[:8]}")

        # 4. Promote eligible slots
        print("\n[PROMOTE] Checking for promotion eligibility...")
        promoted = self.promote_slots_if_ready(turn_id)
        results["promoted_count"] = len(promoted)

        for canonical in promoted:
            print(f"  ★ PROMOTED: {canonical.slot_name}")
            print(f"    - {len(canonical.surface_ids)} surface nodes")
            print(f"    - Seen in {len(canonical.turns_seen)} turns")

        # 5. Update totals
        results["canonical_total"] = len(self.canonical_slots)

        print(f"\n[SUMMARY] Turn {turn_id} complete:")
        print(f"  - Proposed: {results['proposed_count']}")
        print(f"  - Created: {results['created_count']}")
        print(f"  - Merged: {results['merged_count']}")
        print(f"  - Promoted: {results['promoted_count']}")
        print(f"  - Total canonical slots: {results['canonical_total']}")

        return results


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Run the streaming canonical slot discovery simulation.
    """
    print("=" * 60)
    print("STREAMING CANONICAL SLOT DISCOVERY")
    print("=" * 60)

    # Get API key from Colab secrets
    try:
        from google.colab import userdata
        api_key = userdata.get("KIMI_API_KEY")
        if not api_key:
            raise ValueError("KIMI_API_KEY not found in Colab secrets")
    except ImportError:
        # Fallback for local testing
        import os
        api_key = os.environ.get("KIMI_API_KEY")
        if not api_key:
            print("\n⚠️  ERROR: KIMI_API_KEY not found!")
            print("Set the KIMI_API_KEY in Colab secrets or environment variable.")
            return

    print("\n✓ API key loaded")
    print(f"✓ {len(SURFACE_NODES)} surface nodes loaded")

    # Initialize system
    system = SlotDiscoverySystem()

    # Split into unequal chunks
    chunks = split_into_unequal_chunks(SURFACE_NODES, n_turns=10, seed=42)
    print(f"✓ Split into {len(chunks)} chunks (sizes: {[len(c) for c in chunks]})")

    # Process each turn
    turn_results = []
    for turn_id, chunk in enumerate(chunks, start=1):
        result = system.process_turn(chunk, turn_id, api_key)
        turn_results.append(result)

    # Final output
    print(f"\n{'=' * 60}")
    print("FINAL RESULTS")
    print(f"{'=' * 60}")

    print(f"\n📊 CANONICAL SLOTS ({len(system.canonical_slots)} total):")
    print("-" * 60)

    # Sort by number of surface nodes (descending)
    sorted_canonical = sorted(
        system.canonical_slots.values(),
        key=lambda s: len(s.surface_ids),
        reverse=True
    )

    for i, slot in enumerate(sorted_canonical, 1):
        print(f"\n{i}. {slot.slot_name}")
        print(f"   Description: {slot.description}")
        print(f"   Surface nodes: {len(slot.surface_ids)}")
        print(f"   Turns seen: {sorted(slot.turns_seen)}")

    print(f"\n{'=' * 60}")
    print("SURFACE → SLOT MAPPING")
    print(f"{'=' * 60}")

    # DEBUG: Show discrepancy
    print(f"\n[DEBUG] Canonical slot IDs: {list(system.canonical_slots.keys())}")
    print(f"[DEBUG] Surface-to-slot has {len(system.surface_to_slot)} entries")
    print(f"[DEBUG] Slot IDs in surface_to_slot: {set(system.surface_to_slot.values())}")

    # Build mapping by surface label
    surface_labels = {n["id"]: n["label"] for n in SURFACE_NODES}

    # Group surfaces by slot
    slot_to_surfaces = defaultdict(list)
    for surface_id, slot_id in system.surface_to_slot.items():
        if slot_id in system.canonical_slots:
            slot_name = system.canonical_slots[slot_id].slot_name
            label = surface_labels.get(surface_id, surface_id)
            slot_to_surfaces[slot_name].append(label)

    # Print mapping
    for slot_name in sorted(slot_to_surfaces.keys()):
        surfaces = slot_to_surfaces[slot_name]
        print(f"\n{slot_name}:")
        for surface in surfaces:
            print(f"  - {surface}")

    print(f"\n{'=' * 60}")
    print("SIMULATION COMPLETE")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
