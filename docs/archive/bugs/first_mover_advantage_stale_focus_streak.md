# Bug: First-Mover Advantage Due to Stale focus_streak State

## Summary

Nodes that have been focused once retain their `current_focus_streak` value even after losing focus to other nodes. This creates a structural advantage where previously-focused nodes continue to receive `graph.node.focus_streak.low: +0.5` bonus while never-focused nodes get `focus_streak.none: +0.0`.

**Impact**: In the `meal_planning_jtbd_v2 × single_topic_fixator` simulation, all 6 focused nodes were created in turn 1. No nodes from turns 2-14 were ever selected as focus despite 73 nodes (69%) being created later.

## Root Cause

In `src/services/node_state_tracker.py`, the `update_focus()` method only resets `current_focus_streak` for the node GAINING focus, not for the node LOSING focus:

```python
# Line 192-205
# Update streak: reset if focus changed, increment if same
if self.previous_focus == tracking_key:
    state.current_focus_streak += 1
else:
    state.current_focus_streak = 1  # ← Only set for NEW focused node

# Update turns_since_last_focus and turns_since_last_yield for all nodes
for nid, s in self.states.items():
    if nid == tracking_key:
        s.turns_since_last_focus = 0
    else:
        s.turns_since_last_focus += 1  # ← Old focused nodes keep their streak
```

The `current_focus_streak` is never reset to 0 for nodes that lose focus.

## Evidence from Simulation

### Simulation File
`synthetic_interviews/20260306_194645_meal_planning_jtbd_v2_single_topic_fixator.json`

### All Selected Nodes Were from Turn 1
```
=== Nodes Selected During Interview ===
Node ID   | Created Turn | Label
54f7f8d7 | 1            | batch cooking on Sundays
0ad986b0 | 1            | batch cooking approach didn't stick
3b818218 | 1            | child's extreme food pickiness
a8585bf5 | 1            | food going to waste because child won't eat it
86d39cdc | 1            | excessive food waste triggering meal planning over
73e42dfb | 1            | plan meals around child's accepted foods
```

### Focus Frequency
```
54f7f8d7: 4 times focused (created turn 1)
0ad986b0: 2 times focused (created turn 1)
3b818218: 2 times focused (created turn 1)
a8585bf5: 2 times focused (created turn 1)
86d39cdc: 2 times focused (created turn 1)
73e42dfb: 1 times focused (created turn 1)
```

### Node State Comparison (Turn 8)

**Winner (3b818218) - was focused in turns 6-7:**
```
graph.node.exhausted: False
graph.node.exhaustion_score: 0.06
graph.node.yield_stagnation: False
graph.node.focus_streak: low          ← Should be "none" (not focused in turn 8)
graph.node.is_current_focus: False
graph.node.recency_score: 1.0
graph.node.is_orphan: False
```

**Runner-up (a8585bf5) - never focused:**
```
graph.node.exhausted: False
graph.node.exhaustion_score: 0.0
graph.node.yield_stagnation: False
graph.node.focus_streak: none         ← Correct for never-focused
graph.node.is_current_focus: False
graph.node.recency_score: 0.0
graph.node.is_orphan: False
```

### Score Difference (Turn 8, dig_motivation)

**Winner (3b818218):**
- Base Score: 0.800
- Final Score: 1.110
- `graph.node.focus_streak.low: True → +0.500` ← Unearned bonus

**Runner-up (a8585bf5):**
- Base Score: 0.300
- Final Score: 0.510
- `graph.node.exhaustion_score.low: True → +0.300`

The +0.500 bonus from `focus_streak.low` made the winner score higher despite having higher exhaustion_score (0.06 vs 0.0).

## Why This Happens

### Signal Categorization

From `src/signals/graph/node_signals.py` (NodeFocusStreakSignal):

```python
def _categorize_streak(self, streak: int) -> str:
    """Categorize numeric focus streak into ordinal levels."""
    if streak == 0:        return "none"
    elif streak == 1:      return "low"   # ← First focus
    elif streak <= 3:     return "medium"
    else:                  return "high"
```

### YAML Weight

From `config/methodologies/jobs_to_be_done_v2.yaml` (dig_motivation):

```yaml
graph.node.focus_streak.low: 0.5       # Prefer nodes in first focus
graph.node.focus_streak.medium: -0.4   # Penalize 2-3 turn over-focus
graph.node.focus_streak.high: -0.8     # Strongly penalize 4+ turn over-focus
```

The intent of `focus_streak.low: 0.5` is to prefer nodes in their FIRST focus. But due to the stale state bug, nodes that were focused 1-2 turns ago still get categorized as "low" even after losing focus.

## Expected Behavior

When node A loses focus to node B:
- Node A: `current_focus_streak = 0` (reset, no longer focused)
- Node B: `current_focus_streak = 1` (first time being focused)

This would result in:
- Node A: `focus_streak: none` → no bonus (correct, it's not currently focused)
- Node B: `focus_streak: low` → +0.5 bonus (correct, first-time focus)

## Actual Behavior

When node A loses focus to node B:
- Node A: `current_focus_streak = 2` (retains old value)
- Node B: `current_focus_streak = 1` (correct)

This results in:
- Node A: `focus_streak: low` → +0.5 bonus (WRONG - not currently focused)
- Node B: `focus_streak: low` → +0.5 bonus (correct)

## Affected Files

**Primary bug location:**
- `src/services/node_state_tracker.py` - `update_focus()` method (lines 192-205)

**Signal categorization:**
- `src/signals/graph/node_signals.py` - `NodeFocusStreakSignal._categorize_streak()`

**Strategy configuration:**
- `config/methodologies/jobs_to_be_done_v2.yaml` - `dig_motivation`, `uncover_obstacles`, `clarify_assumption`, etc.

## Proposed Fix

In `src/services/node_state_tracker.py`, modify the `update_focus()` method to reset `current_focus_streak = 0` for ALL nodes except the one being focused:

```python
# Update streak for the newly focused node
if self.previous_focus == tracking_key:
    state.current_focus_streak += 1
else:
    state.current_focus_streak = 1

# Reset streak for ALL other nodes that lost focus
for nid, s in self.states.items():
    if nid != tracking_key:
        s.current_focus_streak = 0  # ← NEW: Reset old focused nodes
```

## Verification Steps

1. Run simulation: `uv run python scripts/run_simulation.py meal_planning_jtbd_v2 single_topic_fixator 15`
2. Check which turn nodes were selected
3. Verify that nodes from turns 2+ are selected as focus
4. Verify that previously-focused nodes get `focus_streak: none` after losing focus

## Additional Context

- **Simulation used**: `20260306_194645_meal_planning_jtbd_v2_single_topic_fixator.json`
- **Review document**: `synthetic_interviews/review_20260306_194645_meal_planning_jtbd_v2_single_topic_fixator.md`
- **Graph visualization**: `synthetic_interviews/20260306_194645_meal_planning_jtbd_v2_single_topic_fixator.png` (focused nodes highlighted in gold)

## Related Documentation

- `docs/NodeStateTracker_mutation.md` - Timing of state mutations through pipeline stages
- `docs/signals_and_strategies.md` - Signal Pools configuration
- `docs/deepen_strategy_analysis.md` - Analysis of `dig_motivation` dominance patterns
