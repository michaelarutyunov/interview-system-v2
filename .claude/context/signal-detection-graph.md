# Graph & Node Signal Detection

## Core Mechanics

Graph and node signals are computed from in-memory state — no LLM calls, no DB queries (except `ChainCompletionSignal` which loads nodes/edges once). They run after Stage 7 (StateComputation) so graph_state and NodeStateTracker are fresh when signal detection occurs in Stage 8.

**Global graph signals** (`graph.*`) return a single value keyed by the signal name and are derived from `GraphState` metrics: node count, edge count, max depth, chain completion, canonical concept count, etc. A float value like `graph.max_depth = 0.6` is matched against YAML weight keys via threshold binning (`.low`, `.mid`, `.high`). A boolean like `graph.chain_completion.has_complete` is matched via `.true` / `.false`.

**Node-level signals** (`graph.node.*`, `graph.node.canonical_*`) return `dict[node_id, value]` — one entry per tracked node. They inherit from `NodeSignalDetector` (which wraps `NodeStateTracker`) and always call `self._get_all_node_states()` to iterate every tracked node. Categorical signals (e.g., `graph.node.focus_streak`) return string values (`none`, `low`, `medium`, `high`) matched directly. Float signals (`graph.node.exhaustion_score`, `graph.node.recency_score`) use threshold binning.

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

5. **`meta.node.opportunity` depends on LLM signals being detected first.** It combines `graph.node.exhaustion_score` with `llm.response_depth` to classify nodes as `exhausted`, `probe_deeper`, or `fresh`. It must run after the LLM signal pool is evaluated.

6. **Boolean weight keys must use `.true` or `.false` suffix.** For signals that return `True`/`False` per node (e.g., `graph.node.exhausted`, `graph.node.is_orphan`), YAML weight keys must be `graph.node.exhausted.true` and `graph.node.exhausted.false`. Using `.yes` / `.no` or omitting the suffix causes the weight to never match.

7. **`NodeCanonicalNoveltySignal` returns `{}` when `enable_canonical_slots=False`.** This is a valid empty-result, not an error. Downstream scoring must handle empty node signal dicts without crashing.

---

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `graph.node.focus_streak` always reads as `none` or `low` despite persistent focus | `current_focus_streak` was reset inside `record_yield()` (Stage 5), before signal detection (Stage 8) | Remove `current_focus_streak = 0` from `record_yield()`; streak resets only on focus change in `update_focus()` |
| Node signals missing for some nodes; they score 0 by default | Detector iterated only a subset of nodes (e.g., only newly extracted ones) instead of all tracked nodes | Use `self._get_all_node_states()` to iterate the full NodeStateTracker |
| `graph.node.exhaustion_score` stays near 0.0 despite repeated focus | `turns_since_last_yield` never increments because the tick in `update_focus()` is missing for non-focused nodes | Ensure `update_focus()` ticks `turns_since_last_yield += 1` for ALL nodes in the loop, not only the new focus |
| Signal weight key never matches; strategy score ignores the signal | Wrong bin name in YAML — used `.medium` instead of `.mid`, or `.yes`/`.no` instead of `.true`/`.false` | Valid bins for floats: `.low`, `.mid`, `.high`; for booleans: `.true`, `.false`; for categories: match the exact string (e.g., `.none`, `.low`, `.medium`, `.high`) |
| `meta.node.opportunity` always returns `fresh` even for exhausted nodes | `meta.node.opportunity` evaluated before `llm.response_depth` is available | Check signal dependency ordering; LLM signals must resolve before meta signals that depend on them |
| `graph.node.canonical_novelty` missing from signals dict | `enable_canonical_slots=False` — the signal returns `{}` by design | No fix needed; downstream code must handle empty node signal dicts gracefully |

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
