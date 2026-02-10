"""
Canonical graph service for dual-graph architecture state computation.

Computes aggregate metrics for the canonical graph, including concept count,
edge count, orphan detection, max depth, and average support.
"""

import structlog
from typing import Dict, List, Set

from src.domain.models.canonical_graph import (
    CanonicalEdge,
    CanonicalGraphState,
    CanonicalSlot,
)
from src.persistence.repositories.canonical_slot_repo import CanonicalSlotRepository

log = structlog.get_logger(__name__)


class CanonicalGraphService:
    """
    Service for canonical graph state computation.

    Computes aggregate metrics for the canonical graph, parallel to
    GraphService but operating on canonical slots and edges instead of
    surface nodes and edges.

    Key metrics:
    - concept_count: Number of active canonical slots
    - edge_count: Number of canonical edges
    - orphan_count: Active slots with no canonical edges
    - max_depth: Longest path in canonical graph (handles cycles)
    - avg_support: Average support_count per active slot
    """

    def __init__(self, canonical_slot_repo: CanonicalSlotRepository):
        """
        Initialize canonical graph service.

        Args:
            canonical_slot_repo: CanonicalSlotRepository for data access
        """
        self.repo = canonical_slot_repo

    async def compute_canonical_state(self, session_id: str) -> CanonicalGraphState:
        """
        Compute canonical graph state for a session.

        Queries active slots and canonical edges, then computes:
        - concept_count: Number of active slots
        - edge_count: Number of canonical edges
        - orphan_count: Slots not appearing in any edge (as source or target)
        - max_depth: Longest path length (iterative BFS with cycle handling)
        - avg_support: Mean support_count across active slots

        Args:
            session_id: Session ID

        Returns:
            CanonicalGraphState with all metrics

        Note:
            Empty graph returns all zeros (not an error). max_depth uses
            iterative BFS with visited set (handles cycles). Orphan detection
            uses set operations for efficiency.
        """
        import time

        start_time = time.time()

        # Get active slots and canonical edges
        active_slots = await self.repo.get_active_slots(session_id)
        canonical_edges = await self.repo.get_canonical_edges(session_id)

        concept_count = len(active_slots)
        edge_count = len(canonical_edges)

        # Build slot_id sets for orphan detection
        all_slot_ids: Set[str] = {slot.id for slot in active_slots}
        slots_in_edges: Set[str] = set()

        for edge in canonical_edges:
            slots_in_edges.add(edge.source_slot_id)
            slots_in_edges.add(edge.target_slot_id)

        orphan_count = len(all_slot_ids - slots_in_edges)

        # Compute max depth using iterative BFS (handles cycles)
        max_depth = self._compute_max_depth(active_slots, canonical_edges)

        # Compute average support
        avg_support = (
            sum(slot.support_count for slot in active_slots) / concept_count
            if concept_count > 0
            else 0.0
        )

        elapsed_ms = (time.time() - start_time) * 1000

        if elapsed_ms > 100:
            log.warning(
                "canonical_state_computation_slow",
                session_id=session_id,
                elapsed_ms=round(elapsed_ms, 2),
            )

        log.debug(
            "canonical_state_computed",
            session_id=session_id,
            concept_count=concept_count,
            edge_count=edge_count,
            orphan_count=orphan_count,
            max_depth=max_depth,
            avg_support=round(avg_support, 2),
            elapsed_ms=round(elapsed_ms, 2),
        )

        return CanonicalGraphState(
            concept_count=concept_count,
            edge_count=edge_count,
            orphan_count=orphan_count,
            max_depth=max_depth,
            avg_support=avg_support,
        )

    def _compute_max_depth(
        self, slots: List[CanonicalSlot], edges: List[CanonicalEdge]
    ) -> int:
        """
        Compute the longest path length in the canonical graph.

        Uses iterative BFS from each root node (nodes with no incoming edges),
        tracking visited nodes to handle cycles without infinite loops.

        Args:
            slots: List of canonical slots (for slot_id set)
            edges: List of canonical edges

        Returns:
            Maximum depth (longest path length), 0 if no edges

        Note:
            Uses iterative BFS (not recursive DFS) to avoid stack overflow.
            Visited set prevents infinite loops on cycles. Returns longest
            non-repeating path length.
        """
        if not edges:
            return 0

        slot_ids = {slot.id for slot in slots}

        # Build adjacency list and find root nodes
        adjacency: Dict[str, List[str]] = {sid: [] for sid in slot_ids}
        has_incoming: Set[str] = set()

        for edge in edges:
            if edge.source_slot_id in adjacency:
                adjacency[edge.source_slot_id].append(edge.target_slot_id)
            has_incoming.add(edge.target_slot_id)

        # Root nodes = nodes with no incoming edges
        roots = slot_ids - has_incoming

        if not roots:
            # Cycle with no clear roots - use all nodes as potential starts
            roots = slot_ids

        # BFS from each root to find longest path
        max_depth = 0

        for root in roots:
            depth = self._bfs_depth(adjacency, root)
            max_depth = max(max_depth, depth)

        return max_depth

    def _bfs_depth(self, adjacency: Dict[str, List[str]], start: str) -> int:
        """
        Compute max depth from start node using iterative BFS.

        Args:
            adjacency: Adjacency list mapping slot_id to neighbors
            start: Starting node ID

        Returns:
            Maximum depth from start node
        """
        from collections import deque

        visited: Set[str] = set()
        queue = deque([(start, 0)])  # (node, depth)
        max_depth = 0

        while queue:
            node, depth = queue.popleft()

            if node in visited:
                continue
            visited.add(node)

            max_depth = max(max_depth, depth)

            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

        return max_depth
