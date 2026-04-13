# Graph & Node Signal Detection

## Core Mechanics

Graph and node signals are computed from in-memory state — no LLM calls, no DB queries (except `ChainCompletionSignal`, `ChainTopologySignalDetector`, and `GlobalChainTopologySignal` which each load nodes/edges once per detection pass). They run after Stage 7 (StateComputation) so graph_state and NodeStateTracker are fresh when signal detection occurs in Stage 8.

**Global graph signals** (`graph.*`) return a single value keyed by the signal name and are derived from `GraphState` metrics: node count, edge count, max depth, chain completion, canonical concept count, etc. A float value like `graph.max_depth = 0.6` is matched against YAML weight keys via threshold binning (`.low`, `.mid`, `.high`). A boolean like `graph.chain_completion.has_complete` is matched via `.true` / `.false`.

**Chain topology global signals** (`graph.global.*`) return aggregate metrics about chain structure:
- `graph.global.frontier_count` (int): Count of nodes with `gap_above=True` (chain frontiers waiting to be extended)
- `graph.global.ungrounded_count` (int): Count of nodes with `gap_below=True` (high-level nodes without causal antecedents)

**Node-level signals** (`graph.node.*`, `graph.node.canonical_*`) return `dict[node_id, value]` — one entry per tracked node. They inherit from `NodeSignalDetector` (which wraps `NodeStateTracker`) and always call `self._get_all_node_states()` to iterate every tracked node. Categorical signals (e.g., `graph.node.focus_streak`) return string values (`none`, `low`, `medium`, `high`) matched directly. Float signals (`graph.node.exhaustion_score`, `graph.node.recency_score`) use threshold binning.

**Chain topology node signals** are computed by `ChainTopologySignalDetector` and cover 8 structural properties per node. The detector internally produces a nested dict per node; `NodeSignalDetectionService` **flattens** this into individual signal keys so they are directly addressable in YAML `signal_weights` and `valid_when`:

| Flat key | Type | Meaning |
|---|---|---|
| `graph.node.gap_above` | bool | Node is highest in its chain AND non-terminal (chain frontier) |
| `graph.node.gap_below` | bool | No incoming edges from lower level AND above origin (ungrounded) |
| `graph.node.level_skip` | bool | Direct edge to a node that skips >1 ontology level |
| `graph.node.branching_deficit` | float [0,1] | `1 - (actual_siblings / expected_siblings)` at this node's level |
| `graph.node.fan_in` | int | Distinct origin-level nodes with paths to this node |
| `graph.node.level_gap_size` | int | Ontology levels between this node and terminal/origin |
| `graph.node.chain.has_attribute_foundation` | bool | Transitive downward path (reverse `leads_to`) reaches an attribute-level node |
| `graph.node.chain.has_terminal_apex` | bool | Transitive upward path (forward `leads_to`) reaches a terminal-value node |

The parent key `graph.node.chain_topology` also remains available (holds the raw dict). The 8 flat keys are registered via sentinel classes in `chain_topology_signals.py` so the YAML registry validator accepts them in `valid_when` and `signal_weights`.

**Flattening mechanics** (`NodeSignalDetectionService.detect_all()`): when a detector returns a dict value per node (as `ChainTopologySignalDetector` does), the service derives a namespace prefix from the detector's `signal_name` (`graph.node.chain_topology` → prefix `graph.node.`) and writes each sub-key as `{prefix}{sub_key}`. The parent key is also written. This is a general mechanism; any future detector returning a nested dict per node will auto-flatten the same way.

These signals require graph traversal (O(N×D) for N nodes and D depth) and are only non-trivial for chain methodologies (MEC). For non-chain methodologies (JTBD, CJM, Repertory Grid), the detector returns `{}` and all 8 signals are absent from scoring.

### Chain Lifecycle Signals

Two chain topology signals use transitive reachability to distinguish a node's position in the full chain lifecycle:

- **`graph.node.chain.has_attribute_foundation`** — BFS over **reverse** `leads_to` edges (following edges backward from target to source). Returns `True` if any reachable node has `level == min_level` (the attribute/origin level). This means the node's chain is rooted in a concrete product attribute, not floating.
- **`graph.node.chain.has_terminal_apex`** — BFS over **forward** `leads_to` edges (source to target). Returns `True` if any reachable node has a `node_type` in `terminal_types`. This means the chain has already reached a terminal value above this node.

Both traversals reuse `bfs_reachable()` from `src/signals/graph/graph_traversal.py`. The start node is included in the reachable set (distance 0), so an attribute node naturally has `has_attribute_foundation=True`, and a terminal node naturally has `has_terminal_apex=True`. Graph sizes in practice are 30–100 nodes; BFS cost is well under 1 ms.

Together these signals enable a 2×2 chain-lifecycle matrix for scoring:

| foundation | apex | Interpretation |
|---|---|---|
| False | False | Floating chain — no root and no goal |
| True | False | Grounded chain — extend upward toward terminal |
| False | True | Terminal reached but no attribute below |
| True | True | Complete chain — add breadth from new attributes |

The `current_focus_streak` on a node resets only when focus changes — in `update_focus()` during Stage 8. It is NOT reset in `record_yield()` (Stage 5). This ordering is fundamental: Stage 5 runs before Stage 8, so any reset in `record_yield()` would make the streak appear as 0 to all signal detectors.

---

## Graph Traversal Utilities

Shared synchronous helpers in `src/signals/graph/graph_traversal.py`. All functions operate on in-memory node/edge lists already loaded from the database by the calling signal detector. No LLM calls, no async, no DB access.

| Function | Input | Output | Purpose |
|----------|-------|--------|----------|
| `build_adjacency_list(nodes, edges)` | Node/edge lists | `Dict[node_id, List[node_id]]` | Forward adjacency: source -> targets |
| `build_reverse_adjacency_list(nodes, edges)` | Node/edge lists | `Dict[node_id, List[node_id]]` | Reverse adjacency: target -> sources |
| `get_node_type_map(nodes)` | Node list | `Dict[node_id, node_type]` | node_id -> node_type mapping |
| `bfs_to_target(start, adj_list, target_types, type_map)` | Start node, adjacency, target types | `bool` | Whether a path exists to any node of a given type |
| `bfs_reachable(start, adj_list)` | Start node, adjacency | `Dict[node_id, int]` | Shortest-path distance to all reachable nodes |

Used by `ChainCompletionSignal` (bfs_to_target), `ChainTopologySignalDetector` (bfs_reachable, adjacency builders, type map), and `GlobalChainTopologySignal` (adjacency builders). Any future graph-walking signal detector should reuse these rather than reimplementing BFS.

---

## Chain Completion Signal

`ChainCompletionSignal` (in `src/signals/graph/graph_signals.py`) computes chain completeness from level-1 nodes to terminal nodes using BFS:

- `graph.chain_completion.ratio` (float [0,1]): Fraction of level-1 nodes with a complete path to a terminal node.
- `graph.chain_completion.has_complete` (bool): True if at least one complete chain exists.

This is distinct from the chain topology signals above -- it measures end-to-end chain completeness, not per-node structural gaps. Used by chain-aware strategies as a progress indicator.

---

## Global Chain Topology Signal

`GlobalChainTopologySignal` (in `src/signals/graph/global_chain_signals.py`) produces aggregate counts used by chain-aware strategy `valid_when` gates for threshold checks:

| Signal | Type | Meaning |
|--------|------|----------|
| `graph.global.frontier_count` | int | Nodes with `gap_above=True` (chain frontiers waiting to be extended) |
| `graph.global.ungrounded_count` | int | Nodes with `gap_below=True` (high-level nodes without causal antecedents) |

Returns `{}` for non-chain methodologies (fewer than 2 distinct ontology levels), consistent with `ChainTopologySignalDetector` behavior. When the graph has no nodes, returns zero counts rather than `{}`.

---

## Strategy Integration

Chain topology signals (both node-level and global) are consumed by chain-aware strategies via `valid_when` gates in methodology YAML files:

- **ascend**: Targets nodes with `gap_above=True` to extend chains upward toward terminal values.
- **ground**: Targets nodes with `gap_below=True` to establish causal antecedents from origin level.
- **bridge**: Targets nodes with `level_skip=True` to fill skipped ontology levels.
- **branch**: Targets nodes with high `branching_deficit` to increase sibling coverage.
- **anchor**: Targets nodes with high `fan_in` to reinforce convergence from multiple origins.

Global signals (`frontier_count`, `ungrounded_count`) provide threshold guards -- e.g., `ascend` is only valid when `graph.global.frontier_count > 0`.

---

## Correctness Requirements

1. **All tracked nodes must be in the result.** Node signal detectors must return an entry for every node returned by `self._get_all_node_states()`. Missing nodes silently drop out of joint strategy-node scoring.

2. **`graph.node.exhaustion_score` is bounded [0.0, 1.0]** and is a weighted sum of three components:
   - `turns_since_last_yield` (40% weight, saturates at 10 turns)
   - `current_focus_streak` (30% weight, saturates at 5 consecutive turns)
   - `shallow_response_ratio` (30% weight, 0.0–1.0 from recent 3 responses)
   Nodes never focused (`focus_count == 0`) always return 0.0.

3. **`graph.node.focus_streak` resets only in `update_focus()`, never in `record_yield()`.** `record_yield()` is called in Stage 5 (GraphUpdateStage). `update_focus()` is called in Stage 8 (StrategySelectionStage). Stage 5 runs before Stage 8, so resetting streak in `record_yield()` causes the streak to read as 0 at signal detection time — even though it was correctly non-zero before the turn. Fix: remove any `current_focus_streak = 0` from `record_yield()`.

4. **`turns_since_last_yield` increments for ALL nodes every turn**, not just the focused node. This tick happens inside `update_focus()` — the loop that sets the new focus also increments `turns_since_last_yield` for nodes that were not yielded this turn. Without this global tick, the counter stalls and `exhaustion_score` never grows.

5. **`meta.node.opportunity` reads `llm.response_depth` from the current turn via `context.current_turn_global_signals`.** `MethodologyStrategyService.select_strategy_and_focus()` sets `context.current_turn_global_signals = global_signals` immediately after global signal detection and before calling `NodeSignalDetectionService`. `meta.node.opportunity._get_response_depth()` reads this attribute first, and falls back to `context.signals` (previous-turn output) only if the attribute is absent. Do NOT read `context.signals` directly for current-turn LLM data — it holds the prior turn's `StrategySelectionOutput.signals`.

6. **Boolean weight keys must use `.true` or `.false` suffix.** For signals that return `True`/`False` per node (e.g., `graph.node.exhausted`, `graph.node.is_orphan`), YAML weight keys must be `graph.node.exhausted.true` and `graph.node.exhausted.false`. Using `.yes` / `.no` or omitting the suffix causes the weight to never match.

7. **`NodeCanonicalNoveltySignal` returns `{}` when `enable_canonical_slots=False`.** This is a valid empty-result, not an error. Downstream scoring must handle empty node signal dicts without crashing.

8. **`graph.canonical_exhaustion_score` returns `{}` (absent) when `canonical_slot_repo is None`.** When `enable_canonical_slots=False`, the signal skips computation entirely rather than silently falling back to surface-node exhaustion — which would contradict its name/semantics. Consistent with `graph.canonical_edge_density`, which uses the same guard. Location: `src/signals/graph/graph_signals.py`, `CanonicalExhaustionScoreSignal.detect()`.

9. **Chain topology flat signals require sentinel registration.** The 8 flat keys (`graph.node.gap_above`, `graph.node.gap_below`, `graph.node.level_skip`, `graph.node.branching_deficit`, `graph.node.fan_in`, `graph.node.level_gap_size`, `graph.node.chain.has_attribute_foundation`, `graph.node.chain.has_terminal_apex`) are not backed by real detector logic — their values are injected by `NodeSignalDetectionService` flattening. Eight sentinel classes in `chain_topology_signals.py` (e.g. `_GapAboveSentinel`) register the names in `SignalDetector._registry` so the YAML validator and `ComposedSignalDetector.get_known_signal_names()` accept them. If a new chain topology sub-signal is added to `ChainTopologySignalDetector.detect()`, a matching sentinel class must also be added; otherwise the registry validator will reject any YAML referencing the new key.

10. **`graph.node.is_current_focus` reflects the PREVIOUS turn's focus node at signal-detection time.** `update_focus()` has not yet been called when node signals are detected (it runs later in Stage 6 strategy selection). The signal reads `node_tracker.previous_focus`, so the node that was focused last turn returns `True`. This is by design — strategies reference the incumbent focus — but the name is slightly misleading. Do not rename; add this timing context to any documentation or agent instructions referencing this signal.

---

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `graph.node.focus_streak` always reads as `none` or `low` despite persistent focus | `current_focus_streak` was reset inside `record_yield()` (Stage 5), before signal detection (Stage 8) | Remove `current_focus_streak = 0` from `record_yield()`; streak resets only on focus change in `update_focus()` |
| Node signals missing for some nodes; they score 0 by default | Detector iterated only a subset of nodes (e.g., only newly extracted ones) instead of all tracked nodes | Use `self._get_all_node_states()` to iterate the full NodeStateTracker |
| `graph.node.exhaustion_score` stays near 0.0 despite repeated focus | `turns_since_last_yield` never increments because the tick in `update_focus()` is missing for non-focused nodes | Ensure `update_focus()` ticks `turns_since_last_yield += 1` for ALL nodes in the loop, not only the new focus |
| Signal weight key never matches; strategy score ignores the signal | Wrong bin name in YAML — used `.medium` instead of `.mid`, or `.yes`/`.no` instead of `.true`/`.false` | Valid bins for floats: `.low`, `.mid`, `.high`; for booleans: `.true`, `.false`; for categories: match the exact string (e.g., `.none`, `.low`, `.medium`, `.high`) |
| `meta.node.opportunity` always returns `fresh` even for exhausted nodes | `meta.node.opportunity` evaluated before `llm.response_depth` is available | Check signal dependency ordering; LLM signals must resolve before meta signals that depend on them |
| `meta.node.opportunity.probe_deeper` fires based on prior-turn response depth | `_get_response_depth()` was reading `context.signals` (previous-turn output) instead of current-turn LLM signals | Read `context.current_turn_global_signals` (set by `MethodologyStrategyService` post-global-detection); see Requirement #5 |
| `graph.node.canonical_novelty` missing from signals dict | `enable_canonical_slots=False` — the signal returns `{}` by design | No fix needed; downstream code must handle empty node signal dicts gracefully |
| `graph.node.gap_above` / chain topology flat keys missing from node signals at runtime | ChainTopologySignalDetector returned `{}` (non-chain methodology or empty graph) | Expected; signals absent for non-MEC methodologies. If on MEC, check graph has nodes and edges. |
| `ValueError` at YAML load: `valid_when references unknown signal 'graph.node.gap_above'` | Sentinel classes not imported (module not loaded before validation) | Ensure `src/signals/__init__.py` imports `chain_topology_signals` before registry validation runs |
| New chain topology sub-signal added but not in scoring | Sub-key added to `ChainTopologySignalDetector.detect()` but no sentinel class created | Add a sentinel class in `chain_topology_signals.py` and update `__all__`; see Requirement #9 |
| `graph.canonical_exhaustion_score` not in signal output despite canonical slots being active | `node_tracker.canonical_slot_repo is None` — canonical slot repo was not injected into NodeStateTracker | Ensure `canonical_slot_service` is passed when constructing `NodeStateTracker`; see Requirement #8 |
| `graph.node.is_current_focus` returns `True` for last turn's focus, not this turn's chosen node | By design — `update_focus()` hasn't run yet at detection time | Expected behavior; see Requirement #9. Do not attempt to read post-update focus during signal detection. |

---

## Key Files

| File | Purpose |
|------|---------|
| `src/signals/graph/graph_signals.py` | Global graph signals: `graph.node_count`, `graph.max_depth`, `graph.chain_completion.*`, `graph.canonical_*` |
| `src/signals/graph/global_chain_signals.py` | Global chain topology aggregates: `graph.global.frontier_count`, `graph.global.ungrounded_count` |
| `src/signals/graph/graph_traversal.py` | Shared BFS and adjacency utilities used by chain topology, chain completion, and global chain signal detectors |
| `src/signals/graph/node_signals.py` | Node-level detectors: exhaustion, focus streak, recency, novelty, edge count, canonical novelty |
| `src/signals/graph/node_base.py` | `NodeSignalDetector` base class; provides `_get_all_node_states()` and `_calculate_shallow_ratio()` |
| `src/signals/graph/__init__.py` | `__all__` exports for both global and node signal classes |
 | `src/signals/graph/chain_topology_signals.py` | `ChainTopologySignalDetector` + 8 flat sentinel classes (`_GapAboveSentinel`, `_HasAttributeFoundationSentinel`, etc.) |
| `src/services/node_signal_detection_service.py` | Runs all node-level detectors; flattens nested dict signals into individual flat keys |
| `src/services/global_signal_detection_service.py` | Runs all global detectors and returns flat signal dict |
| `src/services/node_state_tracker.py` | `NodeStateTracker` — `update_focus()`, `record_yield()`, `get_all_states()` |
| `docs/NodeStateTracker_mutation.md` | Per-turn lifecycle map; Stage 5 vs Stage 8 ordering explained |
