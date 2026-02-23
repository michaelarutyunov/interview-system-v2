# NodeStateTracker Mutation Lifecycle

## Overview

`NodeStateTracker` maintains per-node state across interview turns, tracking engagement patterns, yield history, response quality, and strategy usage. This document maps how pipeline stages mutate NodeState state and explains the critical timing relationship between `record_yield()` (Stage 5) and signal detection (Stage 8).

---

## Pipeline Stage Ordering (Critical for State Mutations)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TURN PROCESSING PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Stage 1: ContextLoadingStage                                                │
│  Stage 2: UtteranceSavingStage                                              │
│  Stage 3: SRLPreprocessingStage                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Stage 4: ExtractionStage                                                    │
│  Stage 5: GraphUpdateStage  ◄── calls record_yield()                        │
│                          └──> previous_focus node gets yield credit         │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Stage 6: SlotDiscoveryStage                                                 │
│  Stage 7: StateComputationStage                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Stage 8: StrategySelectionStage  ◄── calls update_focus() + signal detect  │
│                          └──> NEW focus selected, streak computed           │
│                          └──> node_signals read current_focus_streak        │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Stage 9:  ContinuationStage                                                │
│  Stage 10: QuestionGenerationStage                                          │
│  Stage 11: ResponseSavingStage                                              │
│  Stage 12: ScoringPersistenceStage                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Insight**: Stage 5 (record_yield) runs BEFORE Stage 8 (update_focus + signal detection). Any state reset in record_yield is invisible to signals in the same turn.

---

## Per-Turn Lifecycle Map

### NodeStateTracker Methods Called by Pipeline Stages

| Stage | Stage Name | NodeStateTracker Method(s) Called | Purpose |
|-------|------------|-----------------------------------|---------|
| 5 | GraphUpdateStage | `register_node()` | Register newly extracted nodes |
| 5 | GraphUpdateStage | `update_edge_counts()` | Update edge counts for affected nodes |
| 5 | GraphUpdateStage | `record_yield()` | Credit previous_focus with graph changes |
| 8 | StrategySelectionStage | `update_focus()` | Set new focus, compute streak, tick counters |
| 8 | StrategySelectionStage | `append_response_signal()` | Append response_depth to previous_focus |

### State Mutation Timing Within a Turn

```
Turn N begins:
┌─────────────────────────────────────────────────────────────────────┐
│ BEFORE STAGE 5 (GraphUpdateStage):                                  │
│   current_focus_streak = 2 (from Turn N-1 focus)                    │
│   turns_since_last_yield = 3 (from Turn N-3 yield)                  │
│   previous_focus = "node_A" (set in Turn N-1)                       │
├─────────────────────────────────────────────────────────────────────┤
│ STAGE 5: GraphUpdateStage.process()                                 │
│   └──> _update_node_state_tracker()                                 │
│       ├──> register_node(new_nodes)  -- adds fresh nodes            │
│       ├──> update_edge_counts(edges)   -- updates edge counts        │
│       └──> record_yield(                                            │
│              node_id=previous_focus,  # "node_A"                    │
│              graph_changes=...                                       │
│           )                                                         │
│           Sets:                                                      │
│           - last_yield_turn = N                                      │
│           - turns_since_last_yield = 0  ◄── RESET by yield          │
│           - yield_count += 1                                         │
│           - yield_rate = yield_count / focus_count                   │
│           - current_focus_streak NOT reset (see note below)         │
├─────────────────────────────────────────────────────────────────────┤
│ AFTER STAGE 5 (BEFORE STAGE 8):                                     │
│   current_focus_streak = 2 (unchanged)                              │
│   turns_since_last_yield = 0 (RESET by yield)                       │
│   previous_focus = "node_A" (unchanged)                             │
├─────────────────────────────────────────────────────────────────────┤
│ STAGE 8: StrategySelectionStage.process()                           │
│   └──> _select_strategy_and_node()                                  │
│       └──> select_strategy_and_focus()                              │
│           └──> signal detection reads node.state:                   │
│               - current_focus_streak = 2 ◄── CORRECT VALUE          │
│               - turns_since_last_yield = 0                          │
│               - focus_count, yield_count, etc.                      │
│   └──> update_focus(                                                │
│          node_id="node_B",  # NEW focus                             │
│          strategy="broaden",                                        │
│          turn_number=N                                              │
│       )                                                            │
│       Sets:                                                         │
│       - focus_count += 1                                            │
│       - last_focus_turn = N                                         │
│       - current_focus_streak = 1 (reset: focus changed)             │
│       - turns_since_last_yield += 1 for ALL nodes (tick)            │
│       - previous_focus = "node_B" (updated)                         │
├─────────────────────────────────────────────────────────────────────┤
│ AFTER STAGE 8 (END OF TURN N):                                      │
│   current_focus_streak = 1 (reset: new focus)                       │
│   turns_since_last_yield = 1 (ticked in update_focus)               │
│   previous_focus = "node_B" (new focus)                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Why `record_yield()` Runs Before Signal Detection

The pipeline ordering is intentional and correct:

1. **Extraction (Stage 4)** produces graph changes (nodes/edges added)
2. **Yield Recording (Stage 5)** credits the `previous_focus` node with those changes
3. **State Computation (Stage 7)** refreshes graph metrics (node counts, saturation)
4. **Signal Detection (Stage 8)** reads the updated state to select the next strategy

The yield must be recorded before signal detection because:
- Signals need to know if the previous focus produced value (yield)
- Signals need current yield_count and yield_rate for scoring
- Graph state must be fresh before strategy selection

**The bug (bead 119q)**: If `record_yield()` reset `current_focus_streak = 0`, the streak would always appear as 0 to signal detection because:
- `record_yield()` runs in Stage 5
- Signal detection runs in Stage 8 (same turn)
- The reset would happen before signals could read the accumulated streak

**The fix**: `current_focus_streak` is NOT reset in `record_yield()`. It only resets when focus changes (in `update_focus()`). This ensures signals see the accumulated streak from consecutive turns.

---

## Per-Turn State Transition Table

### Example: 3-Turn Sequence with Same Focus (node_A)

| Field | Turn 1 Start | After Stage 5 (Turn 1) | After Stage 8 (Turn 1) | Turn 2 Start | After Stage 5 (Turn 2) | After Stage 8 (Turn 2) | Turn 3 Start | After Stage 5 (Turn 3) | After Stage 8 (Turn 3) |
|-------|--------------|------------------------|------------------------|--------------|------------------------|------------------------|--------------|------------------------|------------------------|
| `previous_focus` | null | "node_A" | "node_A" | "node_A" | "node_A" | "node_A" | "node_A" | "node_A" | "node_A" |
| `current_focus_streak` | 0 | 0 (unchanged) | 1 (set by update_focus) | 1 | 1 (unchanged) | 2 (incremented) | 2 | 2 (unchanged) | 3 (incremented) |
| `turns_since_last_yield` | 0 | 0 (reset by yield) | 1 (ticked in update_focus) | 1 | 0 (reset by yield) | 1 (ticked) | 1 | 0 (reset by yield) | 1 (ticked) |
| `focus_count` | 0 | 0 | 1 | 1 | 1 | 2 | 2 | 2 | 3 |
| `yield_count` | 0 | 1 (incremented) | 1 | 1 | 2 (incremented) | 2 | 2 | 3 (incremented) | 3 |
| `yield_rate` | 0.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

### Example: Focus Change (node_A → node_B)

| Field | Turn N Start | After Stage 5 (node_A yield) | After Stage 8 (switch to node_B) |
|-------|--------------|------------------------------|-----------------------------------|
| `previous_focus` | "node_A" | "node_A" | "node_B" (changed) |
| `current_focus_streak` | 2 | 2 (unchanged) | 1 (reset: focus changed) |
| `turns_since_last_yield` | 3 | 0 (reset by yield) | 1 (ticked for all nodes) |
| `focus_count` | 1 (node_A) | 1 | 2 (node_B: +1) |
| `yield_count` | 1 | 2 (node_A: +1) | 2 |
| `yield_rate` | 1.0 | 2.0 | 2.0 |

---

## State Snapshots at Stage Boundaries

### Before Stage 5 (GraphUpdateStage)
```python
# NodeState for previous_focus node (e.g., "node_A")
{
    "node_id": "node_A",
    "focus_count": 2,
    "current_focus_streak": 2,  # Accumulated from Turn N-2, Turn N-1
    "last_focus_turn": N-1,
    "yield_count": 2,
    "last_yield_turn": N-2,
    "turns_since_last_yield": 2,  # No yield in Turn N-1
    "yield_rate": 1.0,
    # ... other fields
}
```

### After Stage 5 (record_yield called)
```python
# Same node after record_yield()
{
    "node_id": "node_A",
    "focus_count": 2,
    "current_focus_streak": 2,  # NOT reset here (critical!)
    "last_focus_turn": N-1,
    "yield_count": 3,  # +1 increment
    "last_yield_turn": N,  # Updated
    "turns_since_last_yield": 0,  # Reset by yield
    "yield_rate": 1.5,  # Recalculated: 3 / 2
    # ... other fields
}
```

### After Stage 8 (update_focus called, new focus selected)
```python
# Previous focus node ("node_A") after update_focus tick
{
    "node_id": "node_A",
    "focus_count": 2,
    "current_focus_streak": 2,
    "last_focus_turn": N-1,
    "yield_count": 3,
    "last_yield_turn": N,
    "turns_since_last_yield": 1,  # Ticked in update_focus loop
    "yield_rate": 1.5,
}

# New focus node ("node_B") after update_focus
{
    "node_id": "node_B",
    "focus_count": 1,  # +1 increment
    "current_focus_streak": 1,  # Reset (new focus)
    "last_focus_turn": N,
    "yield_count": 0,  # No yield yet
    "last_yield_turn": None,
    "turns_since_last_yield": 1,  # Ticked for all nodes
    "yield_rate": 0.0,
}
```

---

## Signal Detection Visibility

### What Signals See (Stage 8)

Signal detectors in Stage 8 read `NodeState` via `NodeStateTracker.get_state()` or `get_all_states()`. At signal detection time:

1. **Yield signals** (`graph.node.yield_rate`, `graph.node.stagnation`) see:
   - Fresh `yield_count`, `yield_rate`, `last_yield_turn` from Stage 5
   - Accurate yield history because `record_yield()` runs before signals

2. **Focus signals** (`graph.node.focus_streak`, `graph.node.exhaustion`) see:
   - `current_focus_streak` accumulated from previous turns (NOT reset by Stage 5)
   - Accurate streak because reset only happens in Stage 8 `update_focus()`
   - After `update_focus()` runs, streak is reset for the NEXT turn

3. **Recency signals** (`graph.node.recency`) see:
   - `turns_since_last_yield` reset to 0 if yield occurred in Stage 5
   - `turns_since_last_focus` reset to 0 for new focus, incremented for others

### Critical Timing Constraints

```
Turn N Signal Detection reads state mutated by:
├──> record_yield() in Turn N, Stage 5 (same turn, earlier stage)
├──> update_focus() in Turn N-1, Stage 8 (previous turn)
└──> register_node() in Turn N, Stage 5 (new nodes visible)

Turn N Signal Detection does NOT see:
├──> update_focus() in Turn N, Stage 8 (same turn, later stage)  ◄── Runs AFTER signals
└──> record_yield() in Turn N+1, Stage 5 (future turn)
```

---

## Implementation Notes

### `record_yield()` (Stage 5)
- **When called**: After graph changes detected in `GraphUpdateStage`
- **What it sets**:
  - `last_yield_turn = turn_number`
  - `turns_since_last_yield = 0`
  - `yield_count += 1`
  - `yield_rate = yield_count / max(focus_count, 1)`
- **What it does NOT set**:
  - `current_focus_streak` (intentionally NOT reset)
- **Why**: Signals need to see accumulated streak from previous turns

### `update_focus()` (Stage 8)
- **When called**: After strategy selection in `StrategySelectionStage`
- **What it sets**:
  - `focus_count += 1`
  - `last_focus_turn = turn_number`
  - `current_focus_streak = 1 if focus changed else streak + 1`
  - `turns_since_last_focus = 0 for focus node, += 1 for others`
  - `turns_since_last_yield += 1 for ALL nodes` (tick)
  - `previous_focus = new_focus`
- **Why**: Streak resets only when focus changes, not when yield occurs

### `append_response_signal()` (Stage 8)
- **When called**: After signal detection in `StrategySelectionStage`
- **What it appends**: `response_depth` ("surface", "shallow", "deep") to `all_response_depths`
- **Target**: `previous_focus` node (from Turn N-1, NOT new focus)
- **Why**: Response depth belongs to the node that was asked about in previous question

---

## References

- **Source file**: `/home/mikhailarutyunov/projects/interview-system-v2/src/services/node_state_tracker.py`
- **Pipeline wiring**: `/home/mikhailarutyunov/projects/interview-system-v2/src/services/session_service.py:_build_pipeline()` (lines 177-296)
- **Stage 5 (GraphUpdateStage)**: `/home/mikhailarutyunov/projects/interview-system-v2/src/services/turn_pipeline/stages/graph_update_stage.py` (lines 126-213)
- **Stage 8 (StrategySelectionStage)**: `/home/mikhailarutyunov/projects/interview-system-v2/src/services/turn_pipeline/stages/strategy_selection_stage.py` (lines 114-122)
- **Bug fix context**: Bead 119q (node exhaustion/rotation bug fix)
