# Graph & Node Signal Detection
## Current Version: 1.0

## Core Mechanics

Graph and node signals are computed from in-memory state — no LLM calls, no DB queries (except `ChainCompletionSignal`, `ChainTopologySignalDetector`, and `GlobalChainTopologySignal` which each load nodes/edges once per detection pass). They run after Stage 7 (StateComputation) so graph_state and NodeStateTracker are fresh when signal detection occurs in Stage 8.

**Global graph signals** (`graph.*`) return a single value keyed by the signal name and are derived from `GraphState` metrics: node count, edge count, max depth, chain completion, canonical concept count, etc. A float value like `convgraph.state.max_depth = 0.6` is matched against YAML weight keys via threshold binning (`.low`, `.mid`, `.high`). A boolean like `convgraph.chain.completion.has_complete` is matched via `.true` / `.false`.

**Chain topology global signals** (`graph.global.*`) return aggregate metrics about chain structure:
- `convgraph.chain.structure.frontier_count` (int): Count of nodes with `gap_above=True` (chain frontiers waiting to be extended)
- `convgraph.chain.structure.ungrounded_count` (int): Count of nodes with `gap_below=True` (high-level nodes without causal antecedents)

**Node-level signals** (`convgraph.node.*`, `convgraph.node.canonical_*`) return `dict[node_id, value]` — one entry per tracked node. They inherit from `NodeSignalDetector` (which wraps `NodeStateTracker`) and always call `self._get_all_node_states()` to iterate every tracked node. Categorical signals (e.g., `convgraph.node.focus.streak`) return string values (`none`, `low`, `medium`, `high`) matched directly. Float signals (`convgraph.node.exhaustion`, `convgraph.node.recency`) use threshold binning.

**Chain topology node signals** are computed by `ChainTopologySignalDetector` and cover 8 structural properties per node. The detector internally produces a nested dict per node; `NodeSignalDetectionService` **flattens** this into individual signal keys so they are directly addressable in YAML `signal_weights` and `valid_when`:

| Flat key | Type | Meaning |
|---|---|---|
| `convgraph.node.chain.gap.above` | bool | Node is highest in its chain AND non-terminal (chain frontier) |
| `convgraph.node.chain.gap.below` | bool | No incoming edges from lower level AND above origin (ungrounded) |
| `convgraph.node.chain.level.skip` | bool | Direct edge to a node that skips >1 ontology level |
| `convgraph.node.chain.branching_deficit` | float [0,1] | `1 - (actual_siblings / expected_siblings)` at this node's level |
| `convgraph.node.chain.fan_in` | int | Distinct origin-level nodes with paths to this node |
| `convgraph.node.chain.level.gap_size` | int | Ontology levels between this node and terminal/origin |
| `convgraph.node.chain.has_attribute_foundation` | bool | Transitive downward path (reverse chain edges) reaches an attribute-level node |
| `convgraph.node.chain.has_terminal_apex` | bool | Transitive upward path (forward chain edges) reaches a terminal-value node |

The parent key `convgraph.node.chain.role` also remains available (holds the raw dict). The 8 flat keys are registered via sentinel classes in `chain_topology_signals.py` so the YAML registry validator accepts them in `valid_when` and `signal_weights`.

**Flattening mechanics** (`NodeSignalDetectionService.detect_all()`): when a detector returns a dict value per node (as `ChainTopologySignalDetector` does), the service derives a namespace prefix from the detector's `signal_name` (`convgraph.node.chain.role` → prefix `convgraph.node.`) and writes each sub-key as `{prefix}{sub_key}`. The parent key is also written. This is a general mechanism; any future detector returning a nested dict per node will auto-flatten the same way.

These signals require graph traversal (O(N×D) for N nodes and D depth) and are designed for chain methodologies (MEC).

### Signal Data Flow: Detector to Scoring

Signal detector results are merged into `node_signals` keyed by surface UUID. Any key not present in `tracker.states` raises immediately (see `node_signal_detection_service.py`).

The complete path from detector invocation to `valid_when` gate evaluation:

1. **Detectors produce per-node results**: `ChainTopologySignalDetector.detect()` loads nodes from `kg_nodes` → returns `{uuid: {gap.above: True, ...}}`. Tracker-based detectors call `_get_all_node_states()` → return `{uuid: {exhaustion: 0.4, ...}}`. All keys are surface UUIDs.
2. **`NodeSignalDetectionService.detect_all()`** initializes `node_signals = {node_id: {} for node_id in all_states.keys()}` (keys from tracker — always surface UUIDs).
3. **Merge loop**: `for node_id, signal_value in detected.items():` — if `node_id not in node_signals`, raises `ValueError` immediately. No silent drops.
4. **Flattening**: Nested dicts (e.g., `{gap.above: True}`) are flattened into individual flat keys (`convgraph.node.chain.gap.above.true`).
5. **`StrategySelectionStage`** places `node_signals` into `StrategySelectionOutput.node_signals`.
6. **`rank_strategy_node_pairs()`** iterates `node_signals.items()` — each entry is a candidate node.
7. **`valid_when` gate**: `node_signal_dict.get(gate_signal)` evaluates correctly for all surface-UUID-keyed nodes.

These signals require graph traversal (O(N×D) for N nodes and D depth) and are designed for chain methodologies (MEC). The detector filters edges using the `chain_relevant` flag from methodology YAML edge definitions — only edges with `chain_relevant: true` are included in adjacency lists. Each methodology declares which edge types represent chain progression:
- MEC: `leads_to` (chain_relevant), `revises` (not)
- JTBD: `triggers`, `addresses`, `enables`, `supports` (chain_relevant); `occurs_in`, `conflicts_with`, `revises` (not)
- CIT: `occurred_in`, `involved`, `resulted_in`, `elicited`, `led_to_learning`, `influenced` (chain_relevant); `attributed_to`, `similar_to`, `contrasts_with` (not)
- CJM: `transitions_to`, `evokes`, `disrupts`, `confirmed_by`, `violated_by`, `triggered`, `resolved_by`, `revises` (chain_relevant); `occurs_in`, `via_channel`, `expected_at` (not)
- RG: `implies` only (chain_relevant); all others (not)

Methodologies with no `chain_relevant: true` edges, or with fewer than 2 distinct ontology levels, get empty chain topology signals (`{}`). The flag is parsed by `EdgeTypeSpec.chain_relevant` and accessed via `MethodologySchema.get_chain_relevant_edge_types()`.

**Engine vs reporting distinction:** This filtering uses only the `chain_relevant: true` flag from methodology YAML — it does NOT apply `config/chain_rules/*.yaml` type-pair constraints. The chain_rules files are reporting-only (used by `scripts/reporting/generate_causal_chains.py`). The engine sees ALL edges whose type is marked `chain_relevant: true`, regardless of their source/target node types. See `.claude/context/chain-rules.md`.

### Per-Concept LLM Quality Node Signals (Phase C)

Surface per-concept LLM ratings (stored in `NodeState.quality_history` by the Stage 6 bridge — see `signal-detection-llm.md` and `node-state-tracker.md`) as YAML-weightable node signals:

| Flat key | Type | Meaning |
|---|---|---|
| `convgraph.node.llm.elaboration.low` / `.mid` / `.high` | bool | Mean normalized elaboration binned: low <0.34, mid [0.34, 0.67), high ≥0.67 |
| `convgraph.node.llm.charge.negative` / `.neutral` / `.positive` | bool | Mean normalized charge binned: negative <0.375, neutral [0.375, 0.625], positive >0.625 |
| `convgraph.node.llm.has_quality_data` | bool | `True` once the node has received at least one per-concept rating; gate for quality-dependent strategies |

**Dot-notation sub-key convention.** `NodeSignalDetector`s that return a dict per node must emit sub-keys with dot notation (e.g. `"elaboration.low"`, not `"elaboration_low"`). The flattener in `NodeSignalDetectionService` derives the namespace prefix by `rsplit('.', 1)` on the detector's `signal_name` and concatenates `{prefix}.{sub_key}`. YAML weight keys like `convgraph.node.llm.elaboration.low` will never match underscore-separated sub-keys.

### Chain Lifecycle Signals

Two chain topology signals use transitive reachability to distinguish a node's position in the full chain lifecycle:

- **`convgraph.node.chain.has_attribute_foundation`** — BFS over **reverse** chain edges (following edges backward from target to source). Returns `True` if any reachable node has `level == min_level` (the attribute/origin level). This means the node's chain is rooted in a concrete product attribute, not floating.
- **`convgraph.node.chain.has_terminal_apex`** — BFS over **forward** chain edges (source to target). Returns `True` if any reachable node has a `node_type` in `terminal_types`. This means the chain has already reached a terminal value above this node.

Both traversals reuse `bfs_reachable()` from `src/signals/graph/graph_traversal.py`. The start node is included in the reachable set (distance 0), so an attribute node naturally has `has_attribute_foundation=True`, and a terminal node naturally has `has_terminal_apex=True`. Graph sizes in practice are 30–100 nodes; BFS cost is well under 1 ms. Computed inside `ChainTopologySignalDetector.detect()` alongside the other chain topology signals, not as a separate detector.

Together these signals enable a 2×2 chain-lifecycle matrix for scoring:

| foundation | apex | Interpretation |
|---|---|---|
| False | False | Floating chain — no root and no goal |
| True | False | Grounded chain — extend upward toward terminal |
| False | True | Terminal reached but no attribute below |
| True | True | Complete chain — add breadth from new attributes |

The `current_focus_streak` on a node resets only when focus changes — in `update_focus()` during Stage 6. It is NOT reset in `record_yield()` (Stage 4.6). This ordering is fundamental: Stage 4.6 runs before Stage 6, so any reset in `record_yield()` would make the streak appear as 0 to all signal detectors.

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

- `convgraph.chain.completion.ratio` (float [0,1]): Fraction of level-1 nodes with a complete path to a terminal node.
- `convgraph.chain.completion.has_complete` (bool): True if at least one complete chain exists.

This is distinct from the chain topology signals above -- it measures end-to-end chain completeness, not per-node structural gaps. Used by chain-aware strategies as a progress indicator.

---

## Global Chain Topology Signal

`GlobalChainTopologySignal` (in `src/signals/graph/global_chain_signals.py`) produces aggregate counts used by chain-aware strategy `valid_when` gates for threshold checks:

| Signal | Type | Meaning |
|--------|------|----------|
| `convgraph.chain.structure.frontier_count` | int | Nodes with `gap_above=True` (chain frontiers waiting to be extended) |
| `convgraph.chain.structure.ungrounded_count` | int | Nodes with `gap_below=True` (high-level nodes without causal antecedents) |

Returns `{}` for non-chain methodologies (fewer than 2 distinct ontology levels), consistent with `ChainTopologySignalDetector` behavior. When the graph has no nodes, returns zero counts rather than `{}`.

---

## Strategy Integration

Chain topology signals (both node-level and global) are consumed by chain-aware strategies via `valid_when` gates in methodology YAML files:

- **ascend**: Targets nodes with `gap_above=True` to extend chains upward toward terminal values.
- **ground**: Targets nodes with `gap_below=True` to establish causal antecedents from origin level.
- **bridge**: Targets nodes with `level_skip=True` to fill skipped ontology levels.
- **branch**: Targets nodes with high `branching_deficit` to increase sibling coverage.
- **anchor**: Targets nodes with high `fan_in` to reinforce convergence from multiple origins.

Global signals (`frontier_count`, `ungrounded_count`) provide threshold guards -- e.g., `ascend` is only valid when `convgraph.chain.structure.frontier_count > 0`.

---

## Correctness Requirements

1. **All tracked nodes must be in the result.** Node signal detectors must return an entry for every node returned by `self._get_all_node_states()`. Missing nodes silently drop out of joint strategy-node scoring.

2. **`convgraph.node.exhaustion` is bounded [0.0, 1.0]** and is a weighted sum of three components:
   - `turns_since_last_yield` (40% weight, saturates at 10 turns)
   - `current_focus_streak` (30% weight, saturates at 5 consecutive turns)
   - `shallow_response_ratio` (30% weight, 0.0–1.0 from recent 3 responses)
   Nodes never focused (`focus_count == 0`) always return 0.0.

3. **`convgraph.node.focus.streak` resets only in `update_focus()`, never in `record_yield()`.** `record_yield()` is called in Stage 4.6 (EdgeExtractionBridgeStage). `update_focus()` is called in Stage 6 (StrategySelectionStage). Stage 4.6 runs before Stage 6, so resetting streak in `record_yield()` causes the streak to read as 0 at signal detection time — even though it was correctly non-zero before the turn. Fix: remove any `current_focus_streak = 0` from `record_yield()`.

4. **`turns_since_last_yield` increments for ALL nodes every turn**, not just the focused node. This tick happens inside `update_focus()` — the loop that sets the new focus also increments `turns_since_last_yield` for nodes that were not yielded this turn. Without this global tick, the counter stalls and `exhaustion_score` never grows.

5. **Boolean weight keys must use `.true` or `.false` suffix.** For signals that return `True`/`False` per node (e.g., `convgraph.node.is_orphan`, `convgraph.node.has_outgoing`), YAML weight keys must use the `.true` / `.false` suffix. Using `.yes` / `.no` or omitting the suffix causes the weight to never match.

7. **`NodeCanonicalNoveltySignal` returns `{}` when `enable_canonical_slots=False`.** This is a valid empty-result, not an error. Downstream scoring must handle empty node signal dicts without crashing.

8. **`canongraph.state.exhaustion` returns `{}` (absent) when canonical slots are disabled.** When `enable_canonical_slots=False`, the signal skips computation entirely rather than silently falling back to surface-node exhaustion — which would contradict its name/semantics. The check is `context.canonical_graph_state is None` (not `node_tracker.canonical_slot_repo` — `NodeStateTracker` has no such field). Location: `src/signals/graph/graph_signals.py`, `CanonicalExhaustionScoreSignal.detect()`.

9. **Chain topology flat signals require sentinel registration.** The 8 flat keys (`convgraph.node.chain.gap.above`, `convgraph.node.chain.gap.below`, `convgraph.node.chain.level.skip`, `convgraph.node.chain.branching_deficit`, `convgraph.node.chain.fan_in`, `convgraph.node.chain.level.gap_size`, `convgraph.node.chain.has_attribute_foundation`, `convgraph.node.chain.has_terminal_apex`) are not backed by real detector logic — their values are injected by `NodeSignalDetectionService` flattening. Eight sentinel classes in `chain_topology_signals.py` (e.g. `_GapAboveSentinel`) register the names in `SignalDetector._registry` so the YAML validator and `ComposedSignalDetector.get_known_signal_names()` accept them. If a new chain topology sub-signal is added to `ChainTopologySignalDetector.detect()`, a matching sentinel class must also be added; otherwise the registry validator will reject any YAML referencing the new key.

10. **`convgraph.node.is_current_focus` reflects the PREVIOUS turn's focus node at signal-detection time.** `update_focus()` has not yet been called when node signals are detected (it runs later in Stage 6 strategy selection). The signal reads `node_tracker.previous_focus`, so the node that was focused last turn returns `True`. This is by design — strategies reference the incumbent focus — but the name is slightly misleading. Do not rename; add this timing context to any documentation or agent instructions referencing this signal.

---

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `convgraph.node.focus.streak` always reads as `none` or `low` despite persistent focus | `current_focus_streak` was reset inside `record_yield()` (Stage 4.6), before signal detection (Stage 6) | Remove `current_focus_streak = 0` from `record_yield()`; streak resets only on focus change in `update_focus()` |
| Node signals missing for some nodes; they score 0 by default | Detector iterated only a subset of nodes (e.g., only newly extracted ones) instead of all tracked nodes | Use `self._get_all_node_states()` to iterate the full NodeStateTracker |
| `convgraph.node.exhaustion` stays near 0.0 despite repeated focus | `turns_since_last_yield` never increments because the tick in `update_focus()` is missing for non-focused nodes | Ensure `update_focus()` ticks `turns_since_last_yield += 1` for ALL nodes in the loop, not only the new focus |
| Signal weight key never matches; strategy score ignores the signal | Wrong bin name in YAML — used `.medium` instead of `.mid`, or `.yes`/`.no` instead of `.true`/`.false` | Valid bins for floats: `.low`, `.mid`, `.high`; for booleans: `.true`, `.false`; for categories: match the exact string (e.g., `.none`, `.low`, `.medium`, `.high`) |
| `canongraph.node.novelty` missing from signals dict | `enable_canonical_slots=False` — the signal returns `{}` by design | No fix needed; downstream code must handle empty node signal dicts gracefully |
| `convgraph.node.chain.gap.above` / chain topology flat keys missing from node signals at runtime | ChainTopologySignalDetector returned `{}` — fewer than 2 distinct ontology levels, or no edges have `chain_relevant: true` in the methodology YAML | Methodologies with <2 levels or no `chain_relevant` edges get `{}`. Check that the methodology YAML edge definitions include `chain_relevant: true` on the appropriate edge types. |
| Chain topology signals produce vacuously-true `gap.above` for all nodes despite having chain-relevant edges | `get_chain_relevant_edge_types()` returns empty list — edge definitions in YAML missing `chain_relevant: true` flag | Add `chain_relevant: true` to the chain-progression edge types in the methodology YAML. The detector filters edges using this flag, not hardcoded edge type names. |
| `ValueError` at YAML load: `valid_when references unknown signal 'convgraph.node.chain.gap.above'` | Sentinel classes not imported (module not loaded before validation) | Ensure `src/signals/__init__.py` imports `chain_topology_signals` before registry validation runs |
| New chain topology sub-signal added but not in scoring | Sub-key added to `ChainTopologySignalDetector.detect()` but no sentinel class created | Add a sentinel class in `chain_topology_signals.py` and update `__all__`; see Requirement #9 |
| `canongraph.state.exhaustion` not in signal output despite canonical slots being active | `context.canonical_graph_state is None` — canonical graph state not yet computed (e.g. StateComputationStage hasn't run or canonical slots are disabled) | Verify `enable_canonical_slots=True` and that StateComputationStage produced a `canonical_graph_state`; see Requirement #8 |
| `convgraph.node.is_current_focus` returns `True` for last turn's focus, not this turn's chosen node | By design — `update_focus()` hasn't run yet at detection time | Expected behavior; see Requirement #9. Do not attempt to read post-update focus during signal detection. |
| `valid_when` chain topology checks fail for all nodes | Detector emitted a key not in the tracker keyspace (e.g. slot ID instead of surface UUID). After surface-primary inversion, the merge guard raises `ValueError` immediately rather than silently dropping. | Ensure all signal detectors emit surface UUID keys matching `tracker.states`. The merge loop in `NodeSignalDetectionService.detect_all()` will raise with a diagnostic message listing the offending key and the first 5 tracker keys. |
| Anchor strategy never selected despite many orphan nodes (e.g., 10+ orphans visible in graph) | `convgraph.state.node.orphan_count` is an unbounded int blocked from `signal_weights` by registry validation. No normalized variant existed, so systemic orphan accumulation was invisible to strategy scoring. The anchor strategy could only target individual orphans via `convgraph.node.is_orphan.true` (+0.50) with no awareness of scale. | Add `convgraph.state.node.orphan_ratio` weight to anchor (e.g., `.high: 0.40` when ≥75% orphans, `.mid: 0.25` when 25–75%). The signal already exists in `graph_signals.py` — just declare it in the methodology YAML `signals.graph` and add weight keys. |

---

## Known Failure Modes

- **Orphan accumulation is invisible to strategy scoring.** `convgraph.state.node.orphan_count` returns a raw integer that the registry blocks from `signal_weights` (unbounded int safety check at `registry.py:341-344`). Without a normalized variant, anchor/ground strategies cannot detect systemic orphan accumulation — they can only see individual orphan nodes via `convgraph.node.is_orphan`. The normalized variant `convgraph.state.node.orphan_ratio` (float [0,1]) fills this gap and can be threshold-binned via `.high`/`.mid`/`.low` for use in strategy weights. See Symptom → Cause → Fix table entry "Anchor never selected despite high orphan count."


## Key Files

| File | Purpose |
|------|---------|
| `src/signals/graph/graph_signals.py` | Global graph signals: `convgraph.state.node.count`, `convgraph.state.node.orphan_count`, `convgraph.state.node.orphan_ratio`, `convgraph.state.max_depth`, `convgraph.chain.completion.*`, `graph.canonical_*` |
| `src/signals/graph/global_chain_signals.py` | Global chain topology aggregates: `convgraph.chain.structure.frontier_count`, `convgraph.chain.structure.ungrounded_count` |
| `src/signals/graph/graph_traversal.py` | Shared BFS and adjacency utilities used by chain topology, chain completion, and global chain signal detectors |
| `src/signals/graph/node_signals.py` | Node-level detectors: exhaustion, focus streak, recency, novelty, edge count, canonical novelty |
| `src/signals/graph/node_base.py` | `NodeSignalDetector` base class; provides `_get_all_node_states()` and `_calculate_shallow_ratio()` |
| `src/signals/graph/__init__.py` | `__all__` exports for both global and node signal classes |
 | `src/signals/graph/chain_topology_signals.py` | `ChainTopologySignalDetector` + 8 flat sentinel classes (`_GapAboveSentinel`, `_HasAttributeFoundationSentinel`, etc.) |
| `src/services/node_signal_detection_service.py` | Runs all node-level detectors; flattens nested dict signals into individual flat keys |
| `src/services/global_signal_detection_service.py` | Runs all global detectors and returns flat signal dict |
| `src/services/node_state_tracker.py` | `NodeStateTracker` — `update_focus()`, `record_yield()`, `get_all_states()` |
| `.claude/context/node-state-tracker.md` | Per-turn lifecycle map; Stage 5 vs Stage 8 ordering explained |

## Signal Contracts

Per-signal intent vs computation mapping. Extracted from the 2026-04-17 signal semantics audit. Each row is a contract: when code changes, verify the computation still satisfies the stated intent. Severity: `plausible-impact` = could affect scoring, `likely-trivial` = wording mismatch with no behavioral effect, `none` = code/doc agree.

### Global Graph Signals

| Signal | Intent | Computation | Severity |
|--------|--------|-------------|----------|
| `convgraph.state.node.count` | Count of active surface nodes | `graph_state.node_count` (unbounded int) | plausible-impact — raw int multiplied by weight; normalize before weighting |
| `convgraph.state.edge.count` | Count of directed edges | `graph_state.edge_count` (unbounded int) | plausible-impact — same unbounded-int issue |
| `convgraph.state.node.orphan_count` | Nodes with zero incoming AND zero outgoing edges | `graph_state.orphan_count` (unbounded int) | plausible-impact — unbounded int blocked from signal_weights; use `orphan_ratio` instead |
| `convgraph.state.node.orphan_ratio` | Fraction of nodes that are orphans | `orphan_count / max(node_count, 1)` (float [0,1]) | none — normalized, safe for weight multiplication; threshold-binnable via `.high` (≥0.75), `.mid` (0.25–0.75), `.low` (≤0.25) |
| `convgraph.state.max_depth` | Length of longest chain, normalized by ontology level count | BFS from root nodes / ontology level count; clamped [0,1]; fallback=5.0 | likely-trivial — fallback constant MEC-calibrated |
| `convgraph.chain.completion.ratio` | Fraction of level-1 nodes with complete BFS path to terminal | `complete_chain_count / max(level_1_count, 1)` | likely-trivial — brittle with N=1 |
| `convgraph.chain.completion.has_complete` | Boolean: at least one complete chain exists | `complete_chain_count > 0` | none |
| `canongraph.state.node.count` | Count of active canonical slots | `cg_state.concept_count`; absent when `cg_state is None` | likely-trivial — guide claims "0.0", code returns absent |
| `canongraph.state.edge.density` | Edge-to-concept ratio in canonical graph | `edge_count / concept_count`; 0.0 when concept_count==0; absent when `cg_state is None` | plausible-impact — unbounded above 1.0; absent vs 0.0 confusion |
| `canongraph.state.exhaustion` | Average exhaustion across canonical slots | Iterates `node_tracker.states.values()`; "canonical" guarantee depends on `enable_canonical_slots=True` | plausible-impact — silent fallback to surface-keyed states when canonical disabled |

### Node-Level Graph Signals

| Signal | Intent | Computation | Severity |
|--------|--------|-------------|----------|
| `convgraph.node.exhaustion` | 0–1 weighted sum: 40% turns_since_yield + 30% focus_streak + 30% shallow_ratio | Formula matches. `shallow_ratio` counts both `surface` and `shallow` | none — all docs aligned |
| `convgraph.node.yield_stagnation` | Boolean: no yield for 3+ turns on previously-focused node | `focus_count > 0 AND turns_since_last_yield >= 3` | none |
| `convgraph.node.focus.streak` | Categorical: none=0, low=1, medium=2-3, high=4+ | Bins exactly as documented | none |
| `convgraph.node.is_current_focus` | Boolean: true for currently active focus node | Compares to `node_tracker.previous_focus` — name says "current," reads "previous" (correct given stage timing) | plausible-impact — rename to `is_prior_focus` or clarify |
| `convgraph.node.recency` | Float 1.0→0.0 decaying over 20 turns | `max(0.0, 1.0 - turns_since_last_focus / 20.0)`; 0.0 if never focused | none |
| `convgraph.node.is_orphan` | Boolean: zero incoming AND zero outgoing edges | `state.is_orphan` property | none |
| `convgraph.node.edge_count` | Sum of incoming + outgoing edges | `state.edge_count_incoming + state.edge_count_outgoing` | none |
| `convgraph.node.has_outgoing` | Boolean: at least one outgoing edge | `state.edge_count_outgoing > 0` | none |
| `convgraph.node.novelty` | Age-based freshness; high≥0.6 (last 2 turns) | `max(0.0, 1.0 - age/5)`; boundary-inclusive: age=2→0.6→high (effectively "last 3 turns") | likely-trivial — fix guide wording |
| `convgraph.node.focus.count` | Cumulative focus turns; none=0, low=1-2, medium=3-4, high=5+ | Bins exactly as documented | none |
| `canongraph.node.novelty` | Classifies node as new/confirming/orphan based on slot history | Reads `state.slot_id` for each tracked surface, then looks up `canonical_slot_first_seen[slot_id]`. Returns `"orphan"` for surfaces with `slot_id is None`. | plausible-impact — `_slot_first_seen` was instance attribute re-instantiated every turn; now uses `tracker.canonical_slot_first_seen` (survives across turns) |
