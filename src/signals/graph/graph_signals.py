"""Graph signals - structure, depth, chain completion, canonical metrics.

Consolidated from: structure.py, depth.py, chain_completion.py, canonical_structure.py

These signals are derived from the knowledge graph snapshot and are
refreshed after each graph update (PER_TURN). They are free or low cost.
"""

from collections import deque
from typing import TYPE_CHECKING, Any, Dict, List, Set

import structlog

from src.core.exceptions import ConfigurationError, GraphError
from src.core.schema_loader import load_methodology
from src.signals.signal_base import SignalDetector

if TYPE_CHECKING:
    from src.services.turn_pipeline.context import PipelineContext

log = structlog.get_logger(__name__)


# =============================================================================
# Structure Signals (from structure.py)
# =============================================================================


class GraphNodeCountSignal(SignalDetector):
    """Number of nodes in the graph.

    Namespaced signal: graph.node_count
    """

    signal_name = "graph.node_count"
    description = "Total number of concepts extracted. Indicates breadth of coverage. Low counts (<5) suggest early exploration, higher counts (>10) indicate substantial coverage."
    dependencies = []

    async def detect(self, context, graph_state, response_text):
        """Return node count from graph state."""
        return {self.signal_name: graph_state.node_count}


class GraphEdgeCountSignal(SignalDetector):
    """Number of edges in the graph.

    Namespaced signal: graph.edge_count
    """

    signal_name = "graph.edge_count"
    description = "Total number of relationships between concepts. Edge density (edges/nodes) indicates how well-connected concepts are. Low density suggests isolated concepts, high density indicates rich relationships."
    dependencies = []

    async def detect(self, context, graph_state, response_text):
        """Return edge count from graph state."""
        return {self.signal_name: graph_state.edge_count}


class OrphanCountSignal(SignalDetector):
    """Number of orphaned nodes (no relationships).

    Namespaced signal: graph.orphan_count
    """

    signal_name = "graph.orphan_count"
    description = "Number of isolated concepts with no connections to other concepts. High counts suggest opportunities to clarify relationships between mentioned concepts."
    dependencies = []

    async def detect(self, context, graph_state, response_text):
        """Return orphan count from graph state."""
        return {self.signal_name: graph_state.orphan_count}


# =============================================================================
# Depth Signals (from depth.py)
# =============================================================================


class GraphMaxDepthSignal(SignalDetector):
    """Maximum chain depth in the graph, normalized by ontology level count.

    Namespaced signal: graph.max_depth

    Returns a float in [0.0, 1.0] where 1.0 means the graph has reached
    full ontology depth (e.g., depth 5 in a 5-level MEC ontology = 1.0).
    Normalization uses the number of ontology node types as the structural
    maximum, eliminating arbitrary max_expected constants.

    Example:
        MEC ontology has 5 levels. Depth 3 → 3/5 = 0.6
    """

    signal_name = "graph.max_depth"
    description = "Normalized depth of the longest causal chain (0.0-1.0). Normalized by ontology level count. 0.0 = no depth, 1.0 = full ontology chain depth reached."
    dependencies = []

    async def detect(self, context, graph_state, response_text):
        """Return max depth normalized by ontology level count."""
        raw_depth = graph_state.depth_metrics.max_depth
        ontology_levels = self._get_ontology_level_count(context)
        normalized = min(max(raw_depth / ontology_levels, 0.0), 1.0)
        return {self.signal_name: normalized}

    def _get_ontology_level_count(self, context) -> float:
        """Get the number of ontology levels from methodology config.

        Falls back to 5 (common for MEC-style chains with 5 node types).
        """
        methodology = getattr(context, "methodology", None)
        if not methodology:
            return 5.0

        try:
            schema = load_methodology(methodology)
            if schema.ontology and schema.ontology.nodes:
                return float(len(schema.ontology.nodes))
        except Exception:
            pass

        return 5.0


class GraphAvgDepthSignal(SignalDetector):
    """Average depth of all nodes in the graph.

    Namespaced signal: graph.avg_depth
    """

    signal_name = "graph.avg_depth"
    description = "Average depth across all chains. Indicates overall depth of exploration. Values below 2 suggest surface-focused conversation, 2-3 indicate balanced depth, above 3 indicate consistently deep exploration."
    dependencies = []

    async def detect(self, context, graph_state, response_text):
        """Return average depth from depth metrics."""
        return {self.signal_name: graph_state.depth_metrics.avg_depth}


class DepthByElementSignal(SignalDetector):
    """Depth of each element in the graph.

    Namespaced signal: graph.depth_by_element

    Returns a dict mapping element_id → depth.
    """

    signal_name = "graph.depth_by_element"
    description = "Depth of each specific element/node. Used to identify which concepts are at surface vs deep levels. Helps select focus concepts for deepening or broadening."
    dependencies = []

    async def detect(self, context, graph_state, response_text):
        """Return depth by element from depth metrics."""
        return {self.signal_name: graph_state.depth_metrics.depth_by_element}


# =============================================================================
# Chain Completion Signal (from chain_completion.py)
# =============================================================================


class ChainCompletionSignal(SignalDetector):
    """Chain completion ratio and presence from level 1 nodes to terminal nodes.

    Namespaced signals (flat):
        - graph.chain_completion.ratio: float [0,1] — fraction of level-1
          nodes that have a complete path to a terminal node.
        - graph.chain_completion.has_complete: bool — True if at least one
          complete chain exists.

    Uses BFS to find paths from level 1 nodes to terminal nodes.

    Example:
        Level 1 nodes: [A, B, C]
        Terminal nodes: [X, Y, Z]
        Chains: A→...→X, B→...→Y (C doesn't reach terminal)
        Result: {
            "graph.chain_completion.ratio": 0.667,
            "graph.chain_completion.has_complete": True,
        }
    """

    signal_name = "graph.chain_completion"
    description = "Chain completion metrics. graph.chain_completion.ratio is the fraction of level-1 nodes with complete chains (0.0-1.0). graph.chain_completion.has_complete is True when at least one chain reaches terminal values."
    dependencies = []

    async def detect(self, context: Any, graph_state: Any, response_text: str):
        """Count complete chains from level 1 to terminal nodes."""
        # Get methodology name from context
        methodology_name = getattr(context, "methodology", "means_end_chain")

        # Load methodology schema to get terminal node types and level info
        try:
            schema = load_methodology(methodology_name)
        except Exception as e:
            raise ConfigurationError(
                f"ChainCompletionSignal failed to load methodology schema "
                f"'{methodology_name}': {e}"
            ) from e

        # Get terminal node types from schema
        terminal_types = set(schema.get_terminal_node_types())

        # Get level 1 node types (nodes with level=1 in ontology)
        level_1_types = set()
        if schema.ontology:
            for nt in schema.ontology.nodes:
                if nt.level == 1:
                    level_1_types.add(nt.name)

        # If no terminal or level 1 types defined, return zeros
        if not terminal_types or not level_1_types:
            return {
                "graph.chain_completion.ratio": 0.0,
                "graph.chain_completion.has_complete": False,
            }

        # Get nodes and edges from graph
        nodes = await self._get_session_nodes(context)
        edges = await self._get_session_edges(context)

        if not nodes or not edges:
            return {
                "graph.chain_completion.ratio": 0.0,
                "graph.chain_completion.has_complete": False,
            }

        # Build adjacency list for BFS
        adj_list = self._build_adjacency_list(nodes, edges)

        # Filter level 1 nodes
        level_1_nodes = [n for n in nodes if n.node_type in level_1_types]
        level_1_node_count = len(level_1_nodes)

        # Count chains that reach terminal nodes
        complete_chain_count = 0
        for start_node in level_1_nodes:
            if self._bfs_to_terminal(start_node.id, adj_list, terminal_types, nodes):
                complete_chain_count += 1

        has_complete_chain = complete_chain_count > 0
        ratio = complete_chain_count / max(level_1_node_count, 1)

        return {
            "graph.chain_completion.ratio": ratio,
            "graph.chain_completion.has_complete": has_complete_chain,
        }

    async def _get_session_nodes(self, context: Any) -> List[Any]:
        """Get all nodes for the session."""
        session_id = getattr(context, "session_id", None)
        if not session_id:
            raise GraphError(
                "ChainCompletionSignal failed to load nodes: session_id is None"
            )

        try:
            from src.persistence.repositories.graph_repo import GraphRepository
            from src.persistence.database import get_db_connection

            repo = GraphRepository(await get_db_connection())
            return await repo.get_nodes_by_session(session_id)
        except Exception as e:
            raise GraphError(
                f"ChainCompletionSignal failed to load nodes for session "
                f"'{session_id}': {e}"
            ) from e

    async def _get_session_edges(self, context: Any) -> List[Any]:
        """Get all edges for the session."""
        session_id = getattr(context, "session_id", None)
        if not session_id:
            raise GraphError(
                "ChainCompletionSignal failed to load edges: session_id is None"
            )

        try:
            from src.persistence.repositories.graph_repo import GraphRepository
            from src.persistence.database import get_db_connection

            repo = GraphRepository(await get_db_connection())
            return await repo.get_edges_by_session(session_id)
        except Exception as e:
            raise GraphError(
                f"ChainCompletionSignal failed to load edges for session "
                f"'{session_id}': {e}"
            ) from e

    def _build_adjacency_list(
        self, nodes: List[Any], edges: List[Any]
    ) -> Dict[str, List[str]]:
        """Build adjacency list from nodes and edges."""
        adj_list = {node.id: [] for node in nodes}

        for edge in edges:
            if edge.source_node_id in adj_list:
                adj_list[edge.source_node_id].append(edge.target_node_id)

        return adj_list

    def _bfs_to_terminal(
        self,
        start_node_id: str,
        adj_list: Dict[str, List[str]],
        terminal_types: Set[str],
        nodes: List[Any],
    ) -> bool:
        """BFS from start node to check if path to terminal exists."""
        node_type_map = {node.id: node.node_type for node in nodes}

        visited = set()
        queue = deque([start_node_id])
        visited.add(start_node_id)

        while queue:
            current_id = queue.popleft()

            current_type = node_type_map.get(current_id)
            if current_type in terminal_types:
                return True

            for neighbor_id in adj_list.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)

        return False


# =============================================================================
# Canonical Graph Signals (from canonical_structure.py)
# =============================================================================


class CanonicalConceptCountSignal(SignalDetector):
    """Number of deduplicated canonical concepts (active slots).

    Namespaced signal: graph.canonical_concept_count

    Lower than surface node_count because paraphrases are merged into
    canonical slots. Reduces noise from respondent language variation.
    """

    signal_name = "graph.canonical_concept_count"
    description = (
        "Number of deduplicated canonical concepts (active slots). "
        "Lower than surface node_count because paraphrases are merged. "
        "Counts stable latent concepts rather than surface language variations."
    )
    dependencies = []

    async def detect(
        self, context: "PipelineContext", graph_state, response_text
    ) -> dict:
        """Return canonical concept count from canonical graph state."""
        cg_state = context.canonical_graph_state

        if cg_state is None:
            log.debug("canonical_graph_state_not_available", signal=self.signal_name)
            return {}

        return {self.signal_name: cg_state.concept_count}


class CanonicalEdgeDensitySignal(SignalDetector):
    """Edge-to-concept ratio in canonical graph.

    Namespaced signal: graph.canonical_edge_density

    Higher values indicate more connected structure among deduplicated
    concepts. Replaces coverage breadth signal (not relevant for exploration).
    """

    signal_name = "graph.canonical_edge_density"
    description = (
        "Edge-to-concept ratio in canonical graph. Higher = more connected structure. "
        "Uses deduplicated concepts, so reflects relationship density among stable concepts "
        "rather than surface paraphrases."
    )
    dependencies = []

    async def detect(
        self, context: "PipelineContext", graph_state, response_text
    ) -> dict:
        """Return canonical edge density from canonical graph state."""
        cg_state = context.canonical_graph_state

        if cg_state is None:
            log.debug("canonical_graph_state_not_available", signal=self.signal_name)
            return {}

        concept_count = cg_state.concept_count
        edge_count = cg_state.edge_count

        density = edge_count / concept_count if concept_count > 0 else 0.0

        return {self.signal_name: density}


class CanonicalExhaustionScoreSignal(SignalDetector):
    """Average exhaustion score across canonical slots.

    Namespaced signal: graph.canonical_exhaustion_score

    Aggregates exhaustion scores from all tracked canonical slots using
    the NodeStateTracker. Tracks by canonical_slot_id, so this reflects
    exhaustion of deduplicated concepts rather than surface paraphrases.

    Values range 0.0 (fresh) to 1.0 (fully exhausted).
    """

    signal_name = "graph.canonical_exhaustion_score"
    description = (
        "Average exhaustion score across canonical slots. "
        "Aggregates exhaustion from deduplicated concepts (canonical slots). "
        "Higher values indicate concepts have been thoroughly explored. "
        "Tracks exhaustion of stable concepts rather than surface paraphrases."
    )
    dependencies = []

    async def detect(
        self, context: "PipelineContext", graph_state, response_text
    ) -> dict:
        """Return average canonical slot exhaustion score."""
        node_tracker = context.node_tracker

        if node_tracker is None or not node_tracker.states:
            log.debug("node_tracker_not_available", signal=self.signal_name)
            return {}

        exhaustion_scores = [
            self._calculate_exhaustion_score(state)
            for state in node_tracker.states.values()
        ]

        if not exhaustion_scores:
            return {}

        avg_exhaustion = sum(exhaustion_scores) / len(exhaustion_scores)

        return {self.signal_name: avg_exhaustion}

    def _calculate_exhaustion_score(self, state) -> float:
        """Calculate exhaustion score for a node state.

        Returns: Exhaustion score from 0.0 (fresh) to 1.0 (exhausted)
        """
        if state.focus_count == 0:
            return 0.0

        # Factor 1: Turns since last yield (0.0 - 0.4, max at 10 turns)
        turns_score = min(state.turns_since_last_yield, 10) / 10.0 * 0.4

        # Factor 2: Focus streak (0.0 - 0.3, max at 5 consecutive)
        streak_score = min(state.current_focus_streak, 5) / 5.0 * 0.3

        # Factor 3: Shallow ratio (0.0 - 0.3)
        shallow_ratio = self._calculate_shallow_ratio(state, recent_count=3)
        shallow_score = shallow_ratio * 0.3

        return turns_score + streak_score + shallow_score

    def _calculate_shallow_ratio(self, state, recent_count: int = 3) -> float:
        """Calculate ratio of shallow responses in recent N responses."""
        if not state.all_response_depths:
            return 0.0

        recent_responses = state.all_response_depths[-recent_count:]
        shallow_count = sum(
            1 for depth in recent_responses if depth in ("surface", "shallow")
        )

        return shallow_count / len(recent_responses)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Structure
    "GraphNodeCountSignal",
    "GraphEdgeCountSignal",
    "OrphanCountSignal",
    # Depth
    "GraphMaxDepthSignal",
    "GraphAvgDepthSignal",
    "DepthByElementSignal",
    # Chain completion
    "ChainCompletionSignal",
    # Canonical
    "CanonicalConceptCountSignal",
    "CanonicalEdgeDensitySignal",
    "CanonicalExhaustionScoreSignal",
]
