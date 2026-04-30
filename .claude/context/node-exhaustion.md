# Node Exhaustion
## Current Version: 1.0

## Core Mechanics

`NodeStateTracker` maintains per-node state across turns to detect when a node has been sufficiently explored and should be rotated out of focus.

### Tracked Fields Per Node

| Field | Type | Updated by |
|-------|------|------------|
| `focus_count` | int | `update_focus()` Stage 6/8 |
| `current_focus_streak` | int | `update_focus()` Stage 6/8 |
| `last_focus_turn` | int | `update_focus()` Stage 6/8 |
| `turns_since_last_focus` | int | `update_focus()` Stage 6/8 (tick for all nodes) |
| `turns_since_last_yield` | int | `record_yield()` Stage 4 (reset); `update_focus()` Stage 6/8 (tick all) |
| `yield_count` | int | `record_yield()` Stage 4 |
| `yield_rate` | float | `record_yield()` Stage 4 |
| `all_response_depths` | list[str] | `append_response_signal()` Stage 6/8 |
| `previous_focus` | str | `update_focus()` Stage 6/8 |

### Exhaustion Score Formula

```python
exhaustion_score = (
    min(turns_since_last_yield, 10) / 10.0 * 0.4 +  # yield stagnation (0.0–0.4)
    min(current_focus_streak, 5) / 5.0 * 0.3 +      # persistent focus (0.0–0.3)
    shallow_response_ratio * 0.3                      # response quality (0.0–0.3)
)
```

Score ranges: **0.0–0.3** = fresh, **0.3–0.6** = moderate, **0.6–1.0** = exhausted.

`shallow_response_ratio` = fraction of recent `all_response_depths` values that are `"surface"`.

### State Timing Within a Turn

```
Turn N:
  Stage 4 (GraphUpdateStage):
    record_yield(previous_focus)
      → turns_since_last_yield = 0  (RESET)
      → yield_count += 1
      → current_focus_streak NOT touched here

  Stage 6/8 (StrategySelectionStage):
    [signal detection reads current state here]
      → current_focus_streak = accumulated value from prior turns  ✓

    update_focus(new_node_id)
      → current_focus_streak = 1 if focus changed, else streak + 1
      → turns_since_last_yield += 1 for ALL nodes  (tick)
      → previous_focus = new_node_id
```

Key: signals see the streak **accumulated from prior turns**, not reset. The reset only happens when focus changes (`update_focus()` on focus change), not when a yield is recorded.

### Persistence Across Turns

The tracker is loaded at turn start and saved at turn end:

1. **Load** (`SessionService._get_or_create_node_tracker()`): reads `sessions.node_tracker_state` JSON column; deserializes via `NodeStateTracker.from_dict()`; creates fresh tracker if column is NULL.
2. **Save** (`SessionService._save_node_tracker()`): serializes via `NodeStateTracker.to_dict()` and writes back to `sessions.node_tracker_state`.

Save happens inside `ScoringPersistenceStage` (Stage 10/12). If Stage 10/12 is skipped, the turn's NodeStateTracker mutations are lost.

## Correctness Requirements

1. **`current_focus_streak` must NOT reset in `record_yield()`** — `record_yield()` runs in Stage 4, before signal detection in Stage 6/8. Any reset there makes the streak appear as 0 to signals within the same turn. The streak resets only in `update_focus()` on focus change.

2. **`turns_since_last_yield` must tick for ALL nodes in `update_focus()`** — not just the focused node. All nodes accumulate stale time each turn they are not the focus and do not yield. If only the focused node ticks, unfocused nodes never appear stale.

3. **Stage 4 runs before Stage 6/8** — any state written in Stage 4 (`record_yield`, `register_node`) is visible to signal detectors in Stage 6/8. This ordering is critical; reversing it would mean signals read a state that does not yet reflect the current turn's extractions.

4. **`append_response_signal()` targets `previous_focus`, not the new focus** — response depth describes the answer to the question asked last turn (about `previous_focus`). Calling it after `update_focus()` would attribute the response to the newly selected node.

5. **ScoringPersistenceStage must always run** — it is the only place NodeStateTracker is serialized to the database. Changes made after Stage 10/12 are discarded.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `convgraph.node.focus.streak` always 0 for a focused node | `record_yield()` was resetting `current_focus_streak = 0` | Remove that reset from `record_yield()`; streak resets only in `update_focus()` on focus change |
| `exhaustion_score` not growing despite repeated focus on same node | `turns_since_last_yield` not ticking for unfocused nodes | Ensure `update_focus()` increments `turns_since_last_yield` for ALL nodes, not just the new focus |
| Node rotation not occurring (interview stays on one node) | Exhaustion signal weights missing or too low in strategy YAML | Add `convgraph.node.exhaustion.high: -0.8` and `focus_streak.high: -0.6` penalty weights to rotation-sensitive strategies |
| NodeStateTracker state lost between turns | `_save_node_tracker()` not called (ScoringPersistenceStage skipped) | Ensure Stage 10/12 always executes; check pipeline error handling |
| `all_response_depths` always empty | `append_response_signal()` not called, or called with wrong node_id | Verify StrategySelectionStage calls `append_response_signal()` before `update_focus()` |
| Fresh tracker loaded each turn despite completed turns existing | `node_tracker_state` column NULL or deserialization failing | Check `from_dict()` for schema version mismatch; verify `_save_node_tracker()` is writing |

## Known Failure Modes

_No entries yet. Add failure patterns as they are discovered in this subsystem — each entry should describe the incorrect behavior, its consequence, and the correct approach._


## Key Files

- `src/services/node_state_tracker.py` — `NodeState`, `NodeStateTracker`, `record_yield()`, `update_focus()`, `append_response_signal()`
- `src/services/turn_pipeline/stages/graph_update_stage.py` — calls `register_node()`, `record_yield()` (Stage 4)
- `src/services/turn_pipeline/stages/strategy_selection_stage.py` — calls `append_response_signal()`, `update_focus()` (Stage 6/8)
- `src/services/turn_pipeline/stages/scoring_persistence_stage.py` — saves NodeStateTracker to DB (Stage 10/12)
- `src/services/session_service.py` — `_get_or_create_node_tracker()`, `_save_node_tracker()`
- `src/signals/graph/node_signals.py` — `NodeExhaustionScoreSignal`, `NodeYieldStagnationSignal`, `NodeFocusStreakSignal`
- `.claude/context/node-state-tracker.md` — per-turn state transition tables and timing diagrams
