# Graph & Node Signal Detection

## Core Mechanics

Graph and node signals are computed from in-memory state — no LLM calls, no DB queries (except `ChainCompletionSignal` which loads nodes/edges once). They run after Stage 7 (StateComputation) so graph_state and NodeStateTracker are fresh when signal detection occurs in Stage 8.

**Global graph signals** (`graph.*`) return a single value keyed by the signal name and are derived from `GraphState` metrics: node count, edge count, max depth, chain completion, canonical concept count, etc. A float value like `graph.max_depth = 0.6` is matched against YAML weight keys via threshold binning (`.low`, `.mid`, `.high`). A boolean like `graph.chain_completion.has_complete` is matched via `.true` / `.false`.

**Chain topology global signals** (`graph.global.*`) return aggregate metrics about chain structure:
- `graph.global.frontier_count` (int): Count of nodes with `gap_above=True` (chain frontiers waiting to be extended)
- `graph.global.ungrounded_count` (int): Count of nodes with `gap_below=True` (high-level nodes without causal antecedents)

**Node-level signals** (`graph.node.*`, `graph.node.canonical_*`) return `dict[node_id, value]` — one entry per tracked node. They inherit from `NodeSignalDetector` (which wraps `NodeStateTracker`) and always call `self._get_all_node_states()` to iterate every tracked node. Categorical signals (e.g., `graph.node.focus_streak`) return string values (`none`, `low`, `medium`, `high`) matched directly. Float signals (`graph.node.exhaustion_score`, `graph.node.recency_score`) use threshold binning.

**Chain topology node signals** (`graph.node.chain_topology`) return a nested structure per node with 6 boolean/int/float values:
- `gap_above` (bool): Node is highest in its chain AND non-terminal (chain frontier)
- `gap_below` (bool): Node has no incoming edges from lower level AND above origin (ungrounded)
- `level_skip` (bool): Node has direct edge skipping >1 ontology level
- `branching_deficit` (float [0,1]): `1 - (actual_siblings / expected_siblings)` at this node's level
- `fan_in` (int): Distinct origin-level nodes with paths to this node
- `level_gap_size` (int): Ontology levels between this node and terminal/origin

These signals are auto-discovered via the `NodeSignalDetector` registry (not specified in YAML) and require graph traversal to compute chain structure.

The `current_focus_streak` on a node resets only when focus changes — in `update_focus()` during Stage 8. It is NOT reset in `record_yield()` (Stage 5). This ordering is fundamental: Stage 5 runs before Stage 8, so any reset in `record_yield()` would make the streak appear as 0 to all signal detectors.

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

9. **`graph.node.is_current_focus` reflects the PREVIOUS turn's focus node at signal-detection time.** `update_focus()` has not yet been called when node signals are detected (it runs later in Stage 6 strategy selection). The signal reads `node_tracker.previous_focus`, so the node that was focused last turn returns `True`. This is by design — strategies reference the incumbent focus — but the name is slightly misleading. Do not rename; add this timing context to any documentation or agent instructions referencing this signal.

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
| `graph.canonical_exhaustion_score` not in signal output despite canonical slots being active | `node_tracker.canonical_slot_repo is None` — canonical slot repo was not injected into NodeStateTracker | Ensure `canonical_slot_service` is passed when constructing `NodeStateTracker`; see Requirement #8 |
| `graph.node.is_current_focus` returns `True` for last turn's focus, not this turn's chosen node | By design — `update_focus()` hasn't run yet at detection time | Expected behavior; see Requirement #9. Do not attempt to read post-update focus during signal detection. |

---

## Key Files

| File | Purpose |
|------|---------|
| `src/signals/graph/graph_signals.py` | Global graph signals: `graph.node_count`, `graph.max_depth`, `graph.chain_completion.*`, `graph.canonical_*` |
| `src/signals/graph/node_signals.py` | Node-level detectors: exhaustion, focus streak, recency, novelty, edge count, canonical novelty |
| `src/signals/graph/node_base.py` | `NodeSignalDetector` base class; provides `_get_all_node_states()` and `_calculate_shallow_ratio()` |
| `src/signals/graph/__init__.py` | `__all__` exports for both global and node signal classes |
| `src/services/node_signal_detection_service.py` | Runs all node-level detectors and merges results per node |
| `src/services/global_signal_detection_service.py` | Runs all global detectors and returns flat signal dict |
| `src/services/node_state_tracker.py` | `NodeStateTracker` — `update_focus()`, `record_yield()`, `get_all_states()` |
| `docs/NodeStateTracker_mutation.md` | Per-turn lifecycle map; Stage 5 vs Stage 8 ordering explained |
