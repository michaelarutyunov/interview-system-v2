# NodeStateTracker

## Core Mechanics

`NodeStateTracker` maintains per-node state **in memory** across a single turn, persisted to DB as JSON in `sessions.node_tracker_state` at the end of each turn.

- **Loaded**: Stage 1 (`ContextLoadingStage`) via `from_dict()`
- **Updated**: Stages 5 and 8 (see method table below)
- **Saved**: Stage 12 (`ScoringPersistenceStage`) via `to_dict()`

Changes made after Stage 12 are lost; changes made before Stage 1 in the next turn are not visible.

### NodeState Fields

| Field | Type | Description |
|-------|------|-------------|
| `focus_count` | int | Total turns this node was selected as focus |
| `last_focus_turn` | int | Turn number of most recent focus |
| `current_focus_streak` | int | Consecutive turns of focus on this node |
| `turns_since_last_focus` | int | Turns elapsed since last focus (0 = currently focused) |
| `turns_since_last_yield` | int | Turns elapsed since last yield; resets to 0 on yield, ticks every turn in `update_focus` |
| `yield_count` | int | Total turns this node produced graph changes |
| `last_yield_turn` | int \| None | Turn number of most recent yield |
| `yield_rate` | float | `yield_count / max(focus_count, 1)` |
| `all_response_depths` | list[str] | Ordered list of "surface" / "shallow" / "moderate" / "deep" depth labels (derived from per-concept elaboration scores) |
| `quality_history` | `NodeQualityHistory` | Per-concept LLM ratings: `elaboration_scores: list[float]`, `charge_scores: list[float]`. Populated by `append_quality()`. |
| `connected_node_ids` | set[str] | IDs of nodes connected via edges |
| `edge_count_outgoing` | int | Number of outgoing edges |
| `edge_count_incoming` | int | Number of incoming edges |
| `strategy_usage_count` | dict[str, int] | Strategy name → times used on this node |
| `consecutive_same_strategy` | int | Consecutive turns using the same strategy on this node |
| `last_strategy_used` | str \| None | Name of most recently used strategy |

### Key Methods and When They Run

| Stage | Stage Name | Method | What It Does |
|-------|-----------|--------|--------------|
| Stage 5 | `GraphUpdateStage` | `register_node(node, turn_number)` | Creates a new `NodeState` for newly extracted nodes; no-op if already registered |
| Stage 5 | `GraphUpdateStage` | `update_edge_counts(node_id, outgoing_delta, incoming_delta)` | Adjusts edge counts; floors at 0 |
| Stage 5 | `GraphUpdateStage` | `record_yield(node_id, turn_number, graph_changes)` | Credits `previous_focus` with graph changes; resets `turns_since_last_yield` to 0; increments `yield_count`; recalculates `yield_rate`; does **NOT** touch `current_focus_streak` |
| Stage 8 | `StrategySelectionStage` | `update_focus(node_id, turn_number, strategy)` | Increments `focus_count`; sets `last_focus_turn`; resets streak to 1 on focus change, increments streak on same focus; ticks `turns_since_last_yield += 1` for **ALL** nodes; updates `previous_focus` |
| Stage 8 | `StrategySelectionStage` (bridge) | `append_quality(node_id, elaboration, charge)` | Records per-concept LLM ratings: appends normalized `elaboration`/`charge` to `quality_history`, derives and appends a categorical `response_depth` to `all_response_depths`. Called once per concept via the per-concept→node bridge step. Replaces the prior `append_response_signal`. |
| Stage 1 | `ContextLoadingStage` | `from_dict(data)` | Deserializes persisted tracker state; raises `ValueError` on schema version mismatch |
| Stage 12 | `ScoringPersistenceStage` | `to_dict()` | Serializes tracker state to JSON-compatible dict; converts `connected_node_ids` set to list |

### Pipeline Stage Ordering

```
Stage 1:  ContextLoadingStage          ← from_dict() loads tracker
Stage 2:  UtteranceSavingStage
Stage 3:  SRLPreprocessingStage
Stage 4:  ExtractionStage
Stage 5:  GraphUpdateStage             ← register_node(), update_edge_counts(), record_yield()
Stage 6:  SlotDiscoveryStage
Stage 7:  StateComputationStage
Stage 8:  StrategySelectionStage       ← global signals → per-concept→node bridge (append_quality) → node signals → update_focus()
Stage 9:  ContinuationStage
Stage 10: QuestionGenerationStage
Stage 11: ResponseSavingStage
Stage 12: ScoringPersistenceStage      ← to_dict() saves tracker
```

**Critical ordering fact**: Stage 5 (`record_yield`) runs BEFORE Stage 8 (signal detection + `update_focus`). Any mutation in Stage 5 is visible to signals in Stage 8 within the same turn.

### Per-Turn State Flow (Example: Same Focus node_A)

```
Turn N begins (state from Stage 12 of Turn N-1):
  current_focus_streak = 2
  turns_since_last_yield = 3
  previous_focus = "node_A"

  STAGE 5 — record_yield("node_A"):
    turns_since_last_yield = 0      ← reset by yield
    yield_count += 1
    yield_rate recalculated
    current_focus_streak = 2        ← UNCHANGED (not reset here)

  STAGE 8 — signal detection reads:
    current_focus_streak = 2        ← correct accumulated value
    turns_since_last_yield = 0      ← fresh yield this turn

  STAGE 8 — update_focus("node_A"):
    focus_count += 1
    current_focus_streak = 3        ← incremented (same focus)
    turns_since_last_yield += 1     ← ticked for ALL nodes → = 1

Turn N ends (saved to DB):
  current_focus_streak = 3
  turns_since_last_yield = 1
  previous_focus = "node_A"
```

### Dual-Graph Support

When `canonical_slot_repo` is provided (i.e. `enable_canonical_slots=True`), surface node IDs are resolved to canonical slot IDs via `_resolve_canonical_slot_id()` before use as tracking keys. This aggregates metrics across paraphrase surface nodes into a single canonical slot entry. Falls back to surface node ID if no mapping exists (expected for unmapped nodes, not an error).

### Serialization Schema

```python
{
    "schema_version": 3,          # NODE_TRACKER_SCHEMA_VERSION (v3 adds quality_history; from_dict accepts v1/v2 with empty defaults)
    "previous_focus": str | None,
    "states": {
        "<node_id>": {             # canonical_slot_id if dual-graph, else surface node_id
            "node_id": str,
            "focus_count": int,
            "current_focus_streak": int,
            # ... all NodeState fields
            "connected_node_ids": list[str]   # serialized from set
        }
    }
}
```

---

## Correctness Requirements

1. **Stage ordering is invariant**: Stage 5 (`record_yield`) must run before Stage 8 (signal detection + `update_focus`). Signals in Stage 8 depend on yield state already being current.

2. **`current_focus_streak` resets ONLY on focus change**: The reset happens exclusively inside `update_focus()` when `previous_focus != tracking_key`. It must **never** be reset inside `record_yield()`. Resetting in `record_yield` would make streak always appear 0 to signals (because Stage 5 < Stage 8).

3. **`turns_since_last_yield` must tick for ALL nodes in `update_focus()`**: The tick `s.turns_since_last_yield += 1` runs in the loop over `self.states.items()`. It must not be restricted to the focused node — unfocused nodes also need their staleness counter to grow.

4. **Persistence window**: `to_dict()` must be called in Stage 12 and `from_dict()` in Stage 1. Mutations after Stage 12 within a turn are not persisted. Mutations before Stage 1 are not possible (tracker is not yet loaded).

5. **Dual-graph tracking key consistency**: All methods (`update_focus`, `record_yield`, `append_quality`, `update_edge_counts`, `get_state`) resolve surface node IDs to canonical slot IDs before accessing `self.states`. This ensures all metrics accumulate on the canonical key, not scattered across surface paraphrases.

6. **New nodes must be registered before focus or yield**: `register_node()` must run (Stage 5) before `update_focus()` or `record_yield()` attempt to access that node. If a node is not in `self.states`, both methods log a warning and return without error.

7. **`record_yield` is conditional**: No yield is recorded if `graph_changes.nodes_added == 0 and edges_added == 0 and nodes_modified == 0`. This prevents spurious yield credit on turns with no graph mutations.

8. **`NodeStateTracker` is strategy-agnostic**: The tracker records which strategy was used (`strategy_usage_count`, `last_strategy_used`, `consecutive_same_strategy`) but does not know about chain topology strategies (ascend/ground/bridge/branch/anchor) vs legacy strategies. No changes to this subsystem were needed for Phase 2 chain-aware strategy selection.

---

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `convgraph.node.focus.streak` signal always reads 0 at strategy selection | `record_yield()` was resetting `current_focus_streak = 0`; Stage 5 ran before signal detection in Stage 8 | Removed streak reset from `record_yield()`; streak now only resets on focus change inside `update_focus()` |
| `convgraph.node.exhaustion` not growing for repeatedly focused node | `turns_since_last_yield` only incremented for the focused node; unfocused nodes' counter never grew | Changed `update_focus()` loop to tick `turns_since_last_yield += 1` for **all** nodes, not just focus |
| Tracker state lost between turns (signals always see initial values) | `to_dict()` not called in `ScoringPersistenceStage`, or `from_dict()` not called in `ContextLoadingStage` | Verify Stage 12 calls `node_state_tracker.to_dict()` and saves result to `sessions.node_tracker_state`; verify Stage 1 loads it via `from_dict()` |
| Node signals missing / wrong for newly extracted nodes | New node not yet in tracker when `update_focus()` is called | Confirm `register_node()` is called in Stage 5 (before Stage 8); check `register_node()` call path in `graph_update_stage.py:_update_node_state_tracker()` |
| Canonical slot aggregation not working (metrics split across paraphrase nodes) | `canonical_slot_repo` not injected into `NodeStateTracker` constructor | Confirm `NodeStateTracker(canonical_slot_repo=repo)` is used when `enable_canonical_slots=True` in session config |
| `ValueError: Incompatible node_tracker_state schema version` | DB has state serialized at an older schema version | Migrate DB rows or reset `node_tracker_state` to `null` for affected sessions; schema is currently version 3 |

---

## Key Files

| File | Role |
|------|------|
| `src/services/node_state_tracker.py` | `NodeStateTracker` class and `GraphChangeSummary` dataclass |
| `src/domain/models/node_state.py` | `NodeState` dataclass (all tracked fields) |
| `src/services/turn_pipeline/stages/graph_update_stage.py` | Stage 5: calls `register_node()`, `update_edge_counts()`, `record_yield()` |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Stage 8: hosts the per-concept→node bridge (`append_quality()`) and calls `update_focus()` |
| `src/services/turn_pipeline/stages/context_loading_stage.py` | Stage 1: loads tracker via `from_dict()` |
| `src/services/turn_pipeline/stages/scoring_persistence_stage.py` | Stage 12: saves tracker via `to_dict()` |
| `src/persistence/repositories/canonical_slot_repo.py` | `CanonicalSlotRepository` for surface→canonical slot ID resolution |
| `src/services/session_service.py` | `_build_pipeline()` — pipeline wiring |
| `docs/data_flow_paths.md` | Path 8 (NodeStateTracker lifecycle), Path 19 (node signal detection) |
