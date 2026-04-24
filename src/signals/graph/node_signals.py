"""Node-level signals - exhaustion, engagement, relationships.

Consolidated from: node_exhaustion.py, node_engagement.py, node_relationships.py

These signals are derived from NodeStateTracker and computed per node,
enabling joint strategy-node scoring. All require NodeStateTracker.
"""

from src.signals.graph.node_base import NodeSignalDetector


# =============================================================================
# Exhaustion Signals
# =============================================================================



class NodeExhaustionScoreSignal(NodeSignalDetector):
    """Continuous exhaustion score for fine-grained node ranking.

    Provides a 0.0-1.0 exhaustion metric for each node, enabling nuanced
    strategy-node scoring where partially exhausted nodes can be weighted
    differently from fresh or fully exhausted nodes.

    Scoring factors (weighted sum):
    - Turns since last yield (40% weight, max at 10 turns)
    - Current focus streak (30% weight, max at 5 consecutive)
    - Shallow response ratio (30% weight, 0.0-1.0 range)

    Namespaced signal: convgraph.node.exhaustion
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "convgraph.node.exhaustion"
    description = "Continuous exhaustion score 0.0-1.0. Higher values indicate the node has been explored thoroughly without yielding new information."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate continuous exhaustion scores for all tracked nodes.

        Generates fine-grained exhaustion metrics by combining turn-based
        and response-quality factors into a weighted score.

        Args:
            context: Pipeline context with conversation state (unused, required by base signature)
            graph_state: Current knowledge graph state (unused, required by base signature)
            response_text: User's response text (unused, required by base signature)

        Returns:
            Dict mapping node_id -> float (0.0 = fresh, 1.0 = fully exhausted)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            score = self._calculate_exhaustion_score(state)
            results[node_id] = score

        return results

    def _calculate_exhaustion_score(self, state) -> float:
        """Calculate exhaustion score using weighted multi-factor formula.

        Combines three exhaustion indicators:
        1. Turns since last yield (0.0 - 0.4, max contribution at 10 turns)
        2. Focus streak (0.0 - 0.3, max contribution at 5 consecutive)
        3. Shallow response ratio (0.0 - 0.3, direct multiplier)

        Args:
            state: NodeState to score for exhaustion

        Returns:
            Exhaustion score from 0.0 (fresh, never focused) to 1.0 (fully exhausted)
        """
        # If never focused, score is 0.0
        if state.focus_count == 0:
            return 0.0

        # Factor 1: Turns since last yield (0.0 - 0.4, max at 10 turns)
        turns_score = min(state.turns_since_last_yield, 10) / 10.0 * 0.4

        # Factor 2: Focus streak (0.0 - 0.3, max at 5 consecutive)
        streak_score = min(state.current_focus_streak, 5) / 5.0 * 0.3

        # Factor 3: Shallow ratio (0.0 - 0.3)
        shallow_ratio = self._calculate_shallow_ratio(state, recent_count=3)
        shallow_score = shallow_ratio * 0.3

        # Total score
        return turns_score + streak_score + shallow_score


class NodeYieldStagnationSignal(NodeSignalDetector):
    """Detect nodes experiencing yield stagnation during persistent focus.

    Yield stagnation occurs when a node continues to be focused on
    without producing new extracted relationships (no yield events).
    This signals that the node may be exhausted or that a different
    questioning approach is needed.

    Stagnation criteria:
    - Node has been focused on at least once (focus_count > 0)
    - No yield for 3+ consecutive turns (turns_since_last_yield >= 3)

    Namespaced signal: convgraph.node.yield_stagnation
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "convgraph.node.yield_stagnation"
    description = "Whether node has yield stagnation (no yield for 3+ consecutive turns). True if stagnated, False otherwise."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect yield stagnation for all tracked nodes.

        Identifies nodes that have been persistently focused without
        yielding new relationships, indicating potential exhaustion
        or need for strategy change.

        Args:
            context: Pipeline context with conversation state (unused, required by base signature)
            graph_state: Current knowledge graph state (unused, required by base signature)
            response_text: User's response text (unused, required by base signature)
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if stagnated, False otherwise
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            has_stagnation = self._has_yield_stagnation(state)
            results[node_id] = has_stagnation

        return results

    def _has_yield_stagnation(self, state) -> bool:
        """Check if a node has yield stagnation based on focus history.

        Stagnation is detected when a previously focused node has gone
        multiple consecutive turns without producing new relationships.

        Args:
            state: NodeState to check for stagnation indicators

        Returns:
            True if node has yield stagnation (no yield for 3+ turns), False otherwise
        """
        # Must have been focused on at least once
        if state.focus_count == 0:
            return False

        # No yield for 3+ turns
        return state.turns_since_last_yield >= 3


# =============================================================================
# Engagement Signals
# =============================================================================


class NodeFocusStreakSignal(NodeSignalDetector):
    """Categorize consecutive turns each node has been in focus.

    Tracks the current focus streak for each node, which resets when
    focus changes or when the node yields. High focus streaks indicate
    persistent questioning on a single concept without yield.

    Categories:
    - none: 0 consecutive turns (not currently focused)
    - low: 1 consecutive turn (initial focus)
    - medium: 2-3 consecutive turns (moderate persistence)
    - high: 4+ consecutive turns (strong persistence, may need strategy change)

    Namespaced signal: convgraph.node.focus.streak
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "convgraph.node.focus.streak"
    description = "Current focus streak category: none (0), low (1), medium (2-3), high (4+). Indicates persistent focus on a node."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect and categorize focus streak for all tracked nodes.

        Converts numeric focus streak counts into categorical levels
        for use in strategy selection rules and YAML configuration.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> "none" | "low" | "medium" | "high"
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            streak_category = self._categorize_streak(state.current_focus_streak)
            results[node_id] = streak_category

        return results

    def _categorize_streak(self, streak: int) -> str:
        """Categorize numeric focus streak into ordinal levels.

        Maps continuous streak values to discrete categories for use in
        strategy selection rules and YAML-based scoring configuration.

        Args:
            streak: Current focus streak count (consecutive turns focused)

        Returns:
            Category string: "none" (0), "low" (1), "medium" (2-3), or "high" (4+)
        """
        if streak == 0:
            return "none"
        elif streak == 1:
            return "low"
        elif streak <= 3:
            return "medium"
        else:
            return "high"


class NodeIsCurrentFocusSignal(NodeSignalDetector):
    """Identify which node is currently the system focus.

    Returns a boolean flag indicating whether each node is the current
    focus node. Exactly one node returns True (the previous turn's
    focus), all others return False. Used for strategy selection
    rules that need to know the active focus.

    CRITICAL TIMING NOTE: This signal is detected at Stage 6 (StrategySelectionStage),
    but the focus update happens in Stage 6.1 (update_focus() at the end of strategy
    selection). At signal-detection time, update_focus() has NOT yet been called,
    so this signal reflects the PREVIOUS TURN's focus node, not the turn being
    currently processed. Strategy YAML weights should account for this: if targeting
    a "current" node, you're actually targeting the node that was focused in the
    prior turn. This is by design (to allow strategies to reference the incumbent
    focus) but the name is slightly misleading due to pipeline stage ordering.

    Namespaced signal: convgraph.node.is_current_focus
    Cost: low (reads from NodeStateTracker.previous_focus)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "convgraph.node.is_current_focus"
    description = "Whether this node is the current focus. True for focused node, False for others."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect which node is the current focus for all tracked nodes.

        Compares each node_id against the tracker's previous_focus
        value to determine which node is currently active.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if current focus, False otherwise
        """
        results = {}
        current_focus = self.node_tracker.previous_focus

        for node_id in self._get_all_node_states().keys():
            is_current = node_id == current_focus
            results[node_id] = is_current

        return results


class NodeRecencyScoreSignal(NodeSignalDetector):
    """Calculate recency score based on how recently each node was focused.

    Provides a time-decay metric where 1.0 means focused this turn
    and 0.0 means not focused for 20+ turns. Used for strategy
    selection to prefer fresh nodes or implement spacing effects.

    Scoring formula: max(0.0, 1.0 - (turns_since_last_focus / 20.0))

    Namespaced signal: convgraph.node.recency
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "convgraph.node.recency"
    description = "Recency score 0.0-1.0. Higher values indicate the node was focused more recently. Decays over 20 turns."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate recency scores for all tracked nodes.

        Applies linear time decay to the turns_since_last_focus
        metric, producing a continuous score for strategy selection.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> float (0.0 = old, 1.0 = just focused)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            recency_score = self._calculate_recency_score(state)
            results[node_id] = recency_score

        return results

    def _calculate_recency_score(self, state) -> float:
        """Calculate recency score using linear time decay.

        Applies a 20-turn decay window where nodes focused more
        recently receive higher scores. Never-focused nodes return 0.0.

        Args:
            state: NodeState to score for recency

        Returns:
            Recency score from 0.0 (never focused or 20+ turns ago) to 1.0 (focused this turn)
        """
        # If never focused, score is 0.0
        if state.last_focus_turn is None:
            return 0.0

        # Decay over 20 turns
        turns_since = state.turns_since_last_focus
        return max(0.0, 1.0 - (turns_since / 20.0))


# =============================================================================
# Relationship Signals
# =============================================================================


class NodeIsOrphanSignal(NodeSignalDetector):
    """Identify orphan nodes that have no connections to other nodes.

    An orphan node has zero incoming and zero outgoing edges, meaning
    it was extracted but never connected to other concepts. Orphans
    represent opportunities to clarify relationships or may indicate
    extracted concepts that need contextualization.

    Namespaced signal: convgraph.node.is_orphan
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "convgraph.node.is_orphan"
    description = (
        "Whether node is an orphan (no edges). True if isolated, False if connected."
    )

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect orphan status for all tracked nodes.

        Reads edge counts from node state to determine which
        nodes are disconnected from the graph structure.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if orphan (no edges), False if connected
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            is_orphan = state.is_orphan
            results[node_id] = is_orphan

        return results


class NodeEdgeCountSignal(NodeSignalDetector):
    """Count total connections for each node in the graph.

    Returns the sum of incoming and outgoing edges, indicating how
    well-connected each concept is. High edge counts suggest
    central, important concepts; low counts indicate peripheral
    or under-explored nodes.

    Namespaced signal: convgraph.node.edge_count
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "convgraph.node.edge_count"
    description = "Total number of edges (incoming + outgoing) connected to this node. Higher values indicate more connected concepts."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate total edge counts for all tracked nodes.

        Sums incoming and outgoing edge counts from node state
        to provide a connectivity metric for each concept.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> int (total edge count, 0 if orphan)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            total_edges = state.edge_count_incoming + state.edge_count_outgoing
            results[node_id] = total_edges

        return results


class NodeHasOutgoingSignal(NodeSignalDetector):
    """Detect which nodes have outgoing relationships.

    Returns a boolean indicating whether each node has at least one
    outgoing edge. Nodes with outgoing edges have been explored
    and connected to other concepts; nodes without may be leaf
    concepts that haven't been elaborated on.

    Namespaced signal: convgraph.node.has_outgoing
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "convgraph.node.has_outgoing"
    description = "Whether node has outgoing edges. True if node has been explored and has connections, False otherwise."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect outgoing edge presence for all tracked nodes.

        Checks edge_count_outgoing for each node to determine
        which nodes have been connected to downstream concepts.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if has outgoing edges, False otherwise
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            has_outgoing = state.edge_count_outgoing > 0
            results[node_id] = has_outgoing

        return results


# =============================================================================
# Novelty Signals
# =============================================================================


class NodeNoveltySignal(NodeSignalDetector):
    """Age-based novelty score for recently-created nodes.

    Detects how recently a node was created relative to the current turn,
    providing a freshness bonus that decays linearly over DECAY_WINDOW turns.
    This counteracts the structural advantage of early-created nodes that
    accumulate more edges and yields over time.

    Scoring formula: max(0.0, 1.0 - (age / DECAY_WINDOW))
    where age = current_turn - created_at_turn

    Categories:
    - high: score >= 0.6 (created within last 2 turns)
    - medium: 0.3 <= score < 0.6 (3-4 turns old)
    - low: score < 0.3 (5+ turns old, novelty exhausted)

    Namespaced signal: convgraph.node.novelty
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn
    """

    signal_name = "convgraph.node.novelty"
    description = "Age-based novelty score: 1.0 for nodes created this turn, decays to 0.0 over 5 turns."

    DECAY_WINDOW: int = 5

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        results = {}
        current_turn = context.turn_number

        for node_id, state in self._get_all_node_states().items():
            age = current_turn - state.created_at_turn
            novelty_score = max(0.0, 1.0 - (age / self.DECAY_WINDOW))
            results[node_id] = self._categorize_novelty(novelty_score)

        return results

    def _categorize_novelty(self, score: float) -> str:
        if score >= 0.6:
            return "high"
        elif score >= 0.3:
            return "medium"
        else:
            return "low"


# =============================================================================
# Exports
# =============================================================================


class NodeFocusCountSignal(NodeSignalDetector):
    """Cumulative focus count across entire interview — never resets.

    Unlike NodeFocusStreakSignal (which resets on defocus), this signal
    tracks the total number of turns a node has ever been selected as focus.
    Used to penalize nodes that have been overused across the interview,
    even if questioning alternated between them.

    This is the node-level analogue of temporal.strategy_repetition_count:
    just as repeated strategy use is penalized, repeated node focus is penalized.

    Categories:
    - none: 0 total focuses (never explored)
    - low: 1-2 total focuses
    - medium: 3-4 total focuses
    - high: 5+ total focuses (overused node)

    Namespaced signal: convgraph.node.focus.count
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn
    """

    signal_name = "convgraph.node.focus.count"
    description = "Cumulative total times this node has been selected as focus across the entire interview. Never resets."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        results = {}

        for node_id, state in self._get_all_node_states().items():
            results[node_id] = self._categorize_count(state.focus_count)

        return results

    def _categorize_count(self, count: int) -> str:
        if count == 0:
            return "none"
        elif count <= 2:
            return "low"
        elif count <= 4:
            return "medium"
        else:
            return "high"


class NodeCanonicalNoveltySignal(NodeSignalDetector):
    """Canonical-slot-based novelty: new concept vs confirming existing.

    Detects whether a node introduced a NEW canonical concept (a slot
    not previously seen in the interview) vs confirming existing territory
    (mapping to a pre-existing canonical slot).

    This provides semantic novelty detection: a node that says the same
    thing in different words (maps to existing slot) is less novel than
    one that introduces a genuinely new concept (creates a new slot).

    Categories:
    - new: node maps to a canonical slot first seen this turn
    - confirming: node maps to a pre-existing canonical slot
    - orphan: node has no canonical slot mapping (treat as novel)

    Implementation: Reads/writes `canonical_slot_first_seen` dict from
    NodeStateTracker, which persists via to_dict/from_dict to the database.
    Cross-turn memory survives signal re-instantiation and process restarts.

    When enable_canonical_slots is False (canonical_slot_repo is None),
    returns an empty dict to gracefully skip.

    Namespaced signal: canongraph.node.novelty
    Cost: low (reads from NodeStateTracker canonical mapping)
    Refresh: per_turn
    """

    signal_name = "canongraph.node.novelty"
    description = "Whether this node introduced a new canonical concept (new) vs confirming existing territory (confirming) or is unmapped (orphan)."

    def __init__(self, node_tracker=None) -> None:
        super().__init__(node_tracker)

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect canonical novelty for all tracked nodes.

        For each tracked node, resolves its canonical slot mapping and
        determines whether the slot is new (first seen this turn),
        confirming (pre-existing slot), or orphan (no mapping).

        Args:
            context: Pipeline context with turn_number and settings
            graph_state: Current knowledge graph state (unused)
            response_text: User's response text (unused)

        Returns:
            Dict mapping node_id -> "new" | "confirming" | "orphan"
            Empty dict if canonical slots are disabled.
        """
        canonical_repo = self.node_tracker.canonical_slot_repo
        if canonical_repo is None:
            # enable_canonical_slots=False — gracefully skip
            return {}

        current_turn = context.turn_number
        results: dict[str, str] = {}

        for node_id in self._get_all_node_states():
            mapping = await canonical_repo.get_mapping_for_node(node_id)
            if mapping is None:
                results[node_id] = "orphan"
                continue

            slot_id = mapping.canonical_slot_id
            slot_first_seen = self.node_tracker.canonical_slot_first_seen
            if slot_id not in slot_first_seen:
                slot_first_seen[slot_id] = current_turn

            if slot_first_seen[slot_id] == current_turn:
                results[node_id] = "new"
            else:
                results[node_id] = "confirming"

        return results


# =============================================================================
# Per-Concept LLM Quality Signals (from NodeStateTracker.quality_history)
# =============================================================================
#
# These signals surface per-concept LLM ratings (elaboration, charge) recorded
# via NodeStateTracker.append_quality() in the MethodologyStrategyService
# bridge step. They emit dict-valued signals whose sub-keys are binary bins;
# NodeSignalDetectionService flattens them into `convgraph.node.llm.{name}.{bin}` so
# YAML `signal_weights` can reference e.g. `convgraph.node.llm.elaboration.low`.
#
# Spec: docs/drafts/signal-migration-contract.md §C


_ELAB_LOW = 0.375
_ELAB_HIGH = 0.625
_CHARGE_NEG = 0.375
_CHARGE_POS = 0.625


def _mean_or_none(xs):
    return (sum(xs) / len(xs)) if xs else None


class NodeElaborationSignal(NodeSignalDetector):
    """Per-node mean LLM elaboration → categorical bins (low/mid/high).

    Read from NodeState.quality_history.elaboration_scores, populated by
    NodeStateTracker.append_quality() during the per-concept signal bridge.
    """

    signal_name = "convgraph.node.llm.elaboration"
    description = (
        "Per-node elaboration bin (low/mid/high) from LLM per-concept ratings."
    )

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        results = {}
        for node_id, state in self._get_all_node_states().items():
            mean_elab = _mean_or_none(state.quality_history.elaboration_scores)
            if mean_elab is None:
                continue
            # Sub-keys use dot notation so the flattener (prefix=convgraph.node.llm.,
            # tail=signal_name dropped) produces YAML-matching keys like
            # 'convgraph.node.llm.elaboration.low'.
            results[node_id] = {
                "elaboration.low": mean_elab < _ELAB_LOW,
                "elaboration.mid": _ELAB_LOW <= mean_elab < _ELAB_HIGH,
                "elaboration.high": mean_elab >= _ELAB_HIGH,
            }
        return results


class NodeChargeSignal(NodeSignalDetector):
    """Per-node mean LLM emotional charge → categorical bins (negative/neutral/positive)."""

    signal_name = "convgraph.node.llm.charge"
    description = (
        "Per-node charge bin (negative/neutral/positive) from LLM per-concept ratings."
    )

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        results = {}
        for node_id, state in self._get_all_node_states().items():
            mean_charge = _mean_or_none(state.quality_history.charge_scores)
            if mean_charge is None:
                continue
            results[node_id] = {
                "charge.negative": mean_charge < _CHARGE_NEG,
                "charge.neutral": _CHARGE_NEG <= mean_charge < _CHARGE_POS,
                "charge.positive": mean_charge >= _CHARGE_POS,
            }
        return results


class NodeHasQualityDataSignal(NodeSignalDetector):
    """True if a node has any per-concept LLM ratings recorded yet.

    Used as a gate for elaboration/charge-dependent strategies to avoid acting
    on nodes that haven't been rated (e.g. first-turn orphans).
    """

    signal_name = "convgraph.node.llm.has_quality_data"
    description = "True if node has any per-concept LLM elaboration/charge history."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        results = {}
        for node_id, state in self._get_all_node_states().items():
            qh = state.quality_history
            results[node_id] = bool(qh.elaboration_scores or qh.charge_scores)
        return results


__all__ = [
    # Exhaustion
    "NodeExhaustionScoreSignal",
    "NodeYieldStagnationSignal",
    # Engagement
    "NodeFocusStreakSignal",
    "NodeFocusCountSignal",
    "NodeIsCurrentFocusSignal",
    "NodeRecencyScoreSignal",
    # Relationships
    "NodeIsOrphanSignal",
    "NodeEdgeCountSignal",
    "NodeHasOutgoingSignal",
    # Novelty
    "NodeNoveltySignal",
    "NodeCanonicalNoveltySignal",
    # Per-concept LLM quality
    "NodeElaborationSignal",
    "NodeChargeSignal",
    "NodeHasQualityDataSignal",
]
