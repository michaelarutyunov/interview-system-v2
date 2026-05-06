# NodeStateTracker
## Current Version: 2.0

## Core Mechanics

`NodeStateTracker` maintains per-node state **in memory** across a single turn, persisted to DB as JSON in `sessions.node_tracker_state` at the end of each turn.

- **Loaded**: Stage 1 (`ContextLoadingStage`) via `from_dict()`
- **Updated**: Stages 4, 4.5, 4.6, 4.7, 6 (see method table below)
- **Saved**: Stage 10 (`ScoringPersistenceStage`) via `to_dict()`

Changes made after Stage 10 are lost; changes made before Stage 1 in the next turn are not visible.

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
| Stage 4 | `GraphUpdateStage` | `register_node(node, turn_number)` | Creates a new `NodeState` for newly extracted nodes; no-op if already registered. Keyed by surface `node.id` (UUID). |
| Stage 4 | `GraphUpdateStage` | `update_edge_counts(node_id, outgoing_delta, incoming_delta)` | Adjusts edge counts; floors at 0 |
| Stage 4.5 | `SlotDiscoveryStage` | `register_slot_memberships(mappings)` | Sets `NodeState.slot_id` on each surface entry that has a canonical slot mapping. **Does NOT change the keyspace** — tracker remains keyed by surface UUID. `mappings` is a `dict[SurfaceNodeId, SlotId]` built from the slot repo. Raises `NodeNotTrackedError` if any surface_id is missing from tracker. |
| Stage 4.6 | `EdgeExtractionBridgeStage` | `record_yield(tracking_key, turn_number, graph_changes)` | Credits `previous_focus` with yield unconditionally (D4/B7, moved from GraphUpdateStage). Resets `turns_since_last_yield` to 0; increments `yield_count`; recalculates `yield_rate`. Does **NOT** gate on `graph_changes.is_empty()` — yield is recorded regardless of edge count (fixed p4t3). |
| Stage 4.6 | `EdgeExtractionBridgeStage` | `update_edge_counts_batch(edge_deltas)` | Batch-updates edge counts for nodes affected by Stage 4.5B edges (mirrors GraphUpdateStage pattern). |
| Stage 6 | `StrategySelectionStage` | `update_focus(tracking_key, turn_number, strategy)` | Takes `tracking_key: SurfaceNodeId` (surface UUID, no `node_id` param). Increments `focus_count`; sets `last_focus_turn`; resets streak to 1 on focus change, increments streak on same focus; ticks `turns_since_last_yield += 1` for **ALL** nodes; updates `previous_focus` (always a surface UUID). Raises `NodeNotTrackedError` if key not registered. |
| Stage 4.7 | `LLMSignalBridgeStage` | `append_quality(node_id, elaboration, charge)` | Records per-concept LLM ratings: appends normalized `elaboration`/`charge` to `quality_history`, derives and appends a categorical `response_depth` to `all_response_depths`. Called once per concept via the per-concept→node bridge step. **Seals the tracker** — after this stage, `_evolving_node_tracker` is set to None and all downstream access goes through `context.node_tracker` (the sealed snapshot). |
| Stage 1 | `ContextLoadingStage` | `from_dict(data)` | Deserializes persisted tracker state; raises `ValueError` on schema version mismatch |
| Stage 10 | `ScoringPersistenceStage` | `to_dict()` | Serializes tracker state to JSON-compatible dict; converts `connected_node_ids` set to list |

### Pipeline Stage Ordering

```
Stage 1:  ContextLoadingStage          ← from_dict() loads tracker
Stage 2:  UtteranceSavingStage
Stage 2.5: SRLPreprocessingStage
Stage 3:  ExtractionStage
Stage 4:  GraphUpdateStage             ← register_node(), update_edge_counts(), record_yield()
Stage 4.5: SlotDiscoveryStage          ← register_slot_memberships() (after mappings created)
Stage 4.7: LLMSignalBridgeStage        ← append_quality() (per-concept → node bridge)
Stage 5:  StateComputationStage
Stage 6:  StrategySelectionStage       ← global signals → node signals → update_focus()
Stage 7:  ContinuationStage
Stage 8:  QuestionGenerationStage
Stage 9:  ResponseSavingStage
Stage 10: ScoringPersistenceStage      ← to_dict() saves tracker
```

**Critical ordering fact**: Stage 4.6 (`record_yield`) runs BEFORE Stage 6 (signal detection + `update_focus`). Any mutation in Stage 4.6 is visible to signals in Stage 6 within the same turn.

### Per-Turn State Flow (Example: Same Focus node_A)

```
Turn N begins (state from Stage 10 of Turn N-1):
  current_focus_streak = 2
  turns_since_last_yield = 3
  previous_focus = "node_A"

  STAGE 4.6 — record_yield("node_A"):
    turns_since_last_yield = 0      ← reset by yield
    yield_count += 1
    yield_rate recalculated
    current_focus_streak = 2        ← UNCHANGED (not reset here)

  STAGE 6 — signal detection reads:
    current_focus_streak = 2        ← correct accumulated value
    turns_since_last_yield = 0      ← fresh yield this turn

  STAGE 6 — update_focus("node_A"):
    focus_count += 1
    current_focus_streak = 3        ← incremented (same focus)
    turns_since_last_yield += 1     ← ticked for ALL nodes → = 1

Turn N ends (saved to DB):
  current_focus_streak = 3
  turns_since_last_yield = 1
  previous_focus = "node_A"
```

### Model Invariants

`NodeStateTracker` is a **frozen Pydantic `BaseModel`** (`model_config = ConfigDict(frozen=True)`). It has no mutable attributes and no `canonical_slot_repo` field. Canonical slot availability is checked via `context.canonical_graph_state is None` in signal detectors — never via a tracker attribute.

### Keyspace: Surface UUID

`states: dict[str, NodeState]` is keyed exclusively by **surface UUID** (`SurfaceNodeId`). There is no slot-keyed entry at any point in the lifecycle. Slot membership is a **property** on each `NodeState`, not a keyspace dimension:

- **`NodeState.slot_id: Optional[SlotId]`** — set by `register_slot_memberships()` (Stage 4.5) when a surface node maps to a canonical slot. `None` for unmapped nodes.
- **`register_slot_memberships(mappings: Mapping[SurfaceNodeId, SlotId])`** — the only mutation that touches slot identity. Iterates over the provided mappings and sets `state.slot_id` on each matching surface entry. Does NOT add, remove, or re-key entries. Raises `NodeNotTrackedError` if any surface_id is absent.
- **`surfaces_in_slot(slot_id: SlotId) -> list[SurfaceNodeId]`** — returns all surface UUIDs whose `state.slot_id` matches. Used by slot-aggregating signals (e.g. `canongraph.node.novelty`).
- **`slot_id_for_surface(surface_id: SurfaceNodeId) -> Optional[SlotId]`** — returns the slot_id property for a surface entry, or `None` if untracked/unmapped.

### Dual-Graph Support

When `enable_canonical_slots=True`, surface nodes may be mapped to canonical slots via `register_slot_memberships()`. The tracker remains keyed by surface UUID; slot membership is stored as `NodeState.slot_id`. Signal detectors that need slot-level aggregation use `surfaces_in_slot()` to collect all surface states belonging to a slot.

### Identity Types

`SurfaceNodeId` and `SlotId` are `NewType(str, ...)` aliases defined in `src/domain/models/identity.py`. They distinguish surface graph UUIDs from canonical slot keys at static-analysis time (pyright) while being runtime no-ops. All `tracking_key` parameters on NodeStateTracker methods use `SurfaceNodeId`; `previous_focus` is also a `SurfaceNodeId`. `SlotId` appears only as `NodeState.slot_id` and in the `register_slot_memberships` mapping.

### Serialization Schema

```python
{
    "schema_version": 6,          # NODE_TRACKER_SCHEMA_VERSION (v6: surface-primary keyspace, slot_id on NodeState)
    "previous_focus": str | None, # SurfaceNodeId (surface UUID)
    "states": {
        "<surface_uuid>": {       # SurfaceNodeId — always surface UUID, never slot ID
            "node_id": str,
            "slot_id": str | None, # canonical slot membership, set by register_slot_memberships
            "focus_count": int,
            "current_focus_streak": int,
            # ... all NodeState fields
            "connected_node_ids": list[str]   # serialized from frozenset
        }
    },
    "canonical_slot_first_seen": dict[str, int]  # slot_id → first-seen turn number
}
```

---

## Correctness Requirements

1. **Stage ordering is invariant**: Stage 4 (`record_yield`) must run before Stage 6 (signal detection + `update_focus`). Signals in Stage 6 depend on yield state already being current.

2. **`current_focus_streak` resets ONLY on focus change**: The reset happens exclusively inside `update_focus()` when `previous_focus != tracking_key`. It must **never** be reset inside `record_yield()`. Resetting in `record_yield` would make streak always appear 0 to signals (because Stage 4 < Stage 6).

3. **`turns_since_last_yield` must tick for ALL nodes in `update_focus()`**: The tick `s.turns_since_last_yield += 1` runs in the loop over `self.states.items()`. It must not be restricted to the focused node — unfocused nodes also need their staleness counter to grow.

4. **Persistence window**: `to_dict()` must be called in Stage 10 and `from_dict()` in Stage 1. Mutations after Stage 10 within a turn are not persisted. Mutations before Stage 1 are not possible (tracker is not yet loaded).

5. **Surface-primary keyspace**: `tracker.states` is keyed exclusively by surface UUID. All methods (`update_focus`, `record_yield`, `append_quality`, `update_edge_counts`, `get_state`) use surface UUID as tracking key. Slot identity is a property on `NodeState.slot_id`, set by `register_slot_memberships()` at Stage 4.5. There is no slot-keyed entry in `states`.

6. **New nodes must be registered before focus or yield**: `register_node()` must run (Stage 4) before `update_focus()` or `record_yield()` attempt to access that node. If a node is not in `self.states`, both methods log a warning and return without error.

7. **`NodeStateTracker` is strategy-agnostic**: The tracker records which strategy was used (`strategy_usage_count`, `last_strategy_used`, `consecutive_same_strategy`) but does not know about chain topology strategies (ascend/ground/bridge/branch/anchor) vs legacy strategies. No changes to this subsystem were needed for Phase 2 chain-aware strategy selection.

9. **Slot membership registration at Stage 4.5**: `register_node()` stores entries under surface `node.id` (UUID) because canonical slot mappings don't exist yet at Stage 4. After Stage 4.5 (`SlotDiscoveryStage`) creates the mappings, `register_slot_memberships()` must run to set `NodeState.slot_id` on each mapped surface entry. The tracker keyspace is not altered — no entries are added, removed, or re-keyed. Signal detectors that need slot-level aggregation use `surfaces_in_slot()` to collect surface states by slot.

   **Cross-reference**: DB-based signal detectors and the tracker both use surface UUID keys. `NodeSignalDetectionService` merges detector results into `node_signals` keyed by surface UUID — no namespace translation needed. See `signal-detection-graph.md` for the full data flow.

---

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `convgraph.node.focus.streak` signal always reads 0 at strategy selection | `record_yield()` was resetting `current_focus_streak = 0`; Stage 4 ran before signal detection in Stage 6 | Removed streak reset from `record_yield()`; streak now only resets on focus change inside `update_focus()` |
| `convgraph.node.exhaustion` not growing for repeatedly focused node | `turns_since_last_yield` only incremented for the focused node; unfocused nodes' counter never grew | Changed `update_focus()` loop to tick `turns_since_last_yield += 1` for **all** nodes, not just focus |
| Tracker state lost between turns (signals always see initial values) | `to_dict()` not called in `ScoringPersistenceStage`, or `from_dict()` not called in `ContextLoadingStage` | Verify Stage 10 calls `node_state_tracker.to_dict()` and saves result to `sessions.node_tracker_state`; verify Stage 1 loads it via `from_dict()` |
| Node signals missing / wrong for newly extracted nodes | New node not yet in tracker when `update_focus()` is called | Confirm `register_node()` is called in Stage 4 (before Stage 6); check `register_node()` call path in `graph_update_stage.py:_update_node_state_tracker()` |
| Canonical slot aggregation not working (slot_id always None) | `register_slot_memberships()` not called after Stage 4.5 | Verify `register_slot_memberships()` is called at end of `SlotDiscoveryStage.process()` after mappings are created. |
| `ValueError: Incompatible node_tracker_state schema version` | DB has state serialized at an older schema version | Migrate DB rows or reset `node_tracker_state` to `null` for affected sessions; schema is currently version 6 |
| `focus_update_failed_node_not_found` / `append_quality_failed_node_not_found` warnings on every turn | A node was selected as focus (Stage 6) or mapped from a concept (Stage 4.7) that was not registered in the tracker at Stage 4. This should not happen in normal flow — every extracted concept is registered before it can be focused. | Confirm `register_node()` is called in `GraphUpdateStage` for all extracted nodes before downstream stages. Check extraction → graph_update → focus call ordering. |

---

## Known Failure Modes

### record_yield is_empty() guard silently kills yield credit (p4t3, May 2026)

**Symptom:** Interview stops at turn 6 with `all_nodes_exhausted` despite configured 10-turn window. All nodes show `yield_count=0`, `last_yield_turn=None`, `turns_since_last_yield` climbing unchecked.

**Root cause:** `record_yield()` had a guard `if graph_changes.is_empty(): return self` that skipped yield recording when `nodes_added==0 AND edges_added==0`. After B7 moved `record_yield` from GraphUpdateStage to EdgeExtractionBridgeStage, the bridge hardcodes `nodes_added=0` and `edges_added` is `0` whenever the feature flag is OFF (task is None). The guard returned `self` unchanged every turn.

**Fix:** Removed the `is_empty()` guard (commit `a8af00d`). The focus node was actively used this turn — it deserves yield credit regardless of graph change counts. The guard was appropriate for GraphUpdateStage's original call site (where `(nodes_added or edges_added)` was a meaningful signal) but became a silent killer after the B7 move.

**Detection:** Check for `yc=0` and `lyt=None` on all explored nodes in the exhaustion log. If present, `record_yield` is not being called or is being gated.


## Key Files

| File | Role |
|------|------|
| `src/services/node_state_tracker.py` | `NodeStateTracker` class and `GraphChangeSummary` dataclass |
| `src/domain/models/node_state.py` | `NodeState` dataclass (all tracked fields) |
| `src/services/turn_pipeline/stages/graph_update_stage.py` | Stage 4: calls `register_node()`, `update_edge_counts()` |
| `src/services/turn_pipeline/stages/slot_discovery_stage.py` | Stage 4.5: calls `register_slot_memberships()` after creating surface-to-slot mappings |
| `src/services/turn_pipeline/stages/edge_extraction_bridge_stage.py` | Stage 4.6: calls `record_yield()` (D4/B7), `update_edge_counts_batch()` for Stage 4.5B edges |
| `src/services/turn_pipeline/stages/llm_signal_bridge_stage.py` | Stage 4.7: per-concept→node bridge (`append_quality()`), seals tracker |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Stage 6: calls `update_focus()` |
| `src/services/turn_pipeline/stages/context_loading_stage.py` | Stage 1: loads tracker via `from_dict()` |
| `src/services/turn_pipeline/stages/scoring_persistence_stage.py` | Stage 10: saves tracker via `to_dict()` |
| `src/persistence/repositories/canonical_slot_repo.py` | `CanonicalSlotRepository` for surface-to-slot ID resolution (used by SlotDiscoveryStage to build mappings) |
| `src/services/session_service.py` | `_build_pipeline()` — pipeline wiring |
| `.claude/context/signal-detection-graph.md` | Node signal detection flow, key namespace divergence, chain topology signals |
| `.claude/context/strategy-selection.md` | Joint scoring architecture and strategy selection flow |
