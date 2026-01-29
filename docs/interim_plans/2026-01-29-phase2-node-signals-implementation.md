# Phase 2: Node-Level Signals Implementation Plan

**Status:** Ready for Implementation
**Date:** 2026-01-29
**Parent Bead:** interview-system-v2-75a

## Overview

Implement node-level signals that are derived from NodeStateTracker. These signals enable joint strategy-node scoring in Phase 3.

## Tasks

### Task 1: Create Base Classes for Node Signals

**File:** `src/methodologies/signals/graph/__init__.py` (new directory structure)

**Requirements:**
- Create base class `NodeSignalDetector` extending `SignalDetector`
- Add helper methods for accessing NodeStateTracker
- Define namespace prefix `graph.node.*` for node-level signals

**Base class:**
```python
class NodeSignalDetector(SignalDetector):
    """Base class for signals derived from NodeStateTracker."""

    def __init__(self, node_tracker: NodeStateTracker):
        self.node_tracker = node_tracker

    def _get_node_state(self, node_id: str) -> Optional[NodeState]:
        """Get NodeState for a node, or None if not tracked."""
```

### Task 2: Implement Exhaustion Signals

**File:** `src/methodologies/signals/graph/node_exhaustion.py` (new)

**Signals:**

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `graph.node.exhausted` | categorical | `true` / `false` | Primary exhaustion flag |
| `graph.node.exhaustion_score` | numeric | 0.0 - 1.0 | Continuous score |
| `graph.node.yield_stagnation` | categorical | `true` / `false` | No yield for N focuses |

**Exhaustion Logic:**
```python
is_exhausted = (
    state.focus_count > 0 and
    state.turns_since_last_yield >= 3 and
    state.current_focus_streak >= 2 and
    shallow_ratio >= 0.66
)

where shallow_ratio = count of "surface"/"shallow" in last 3 responses / 3
```

**Class structure:**
```python
class NodeExhaustedSignal(NodeSignalDetector):
    signal_name = "graph.node.exhausted"
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text) -> Dict[str, str]:
        # Returns: {"node_id": "true"|"false", ...}

class NodeExhaustionScoreSignal(NodeSignalDetector):
    signal_name = "graph.node.exhaustion_score"
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text) -> Dict[str, float]:
        # Returns: {"node_id": 0.0-1.0, ...}

class NodeYieldStagnationSignal(NodeSignalDetector):
    signal_name = "graph.node.yield_stagnation"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text) -> Dict[str, str]:
        # Returns: {"node_id": "true"|"false", ...}
```

### Task 3: Implement Engagement Signals

**File:** `src/methodologies/signals/graph/node_engagement.py` (new)

**Signals:**

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `graph.node.focus_streak` | categorical | `none` / `low` / `medium` / `high` | Consecutive focuses |
| `graph.node.is_current_focus` | categorical | `true` / `false` | Currently focused |
| `graph.node.recency_score` | numeric | 0.0 - 1.0 | Higher for recent nodes |

**Focus streak mapping:**
```python
streak = state.current_focus_streak
if streak == 0: return "none"
elif streak == 1: return "low"
elif streak <= 3: return "medium"
else: return "high"
```

**Recency score calculation:**
```python
turns_since = state.turns_since_last_focus if state.last_focus_turn else 999
recency = max(0.0, 1.0 - (turns_since / 20.0))  # Decay over 20 turns
```

### Task 4: Implement Relationship Signals

**File:** `src/methodologies/signals/graph/node_relationships.py` (new)

**Signals:**

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `graph.node.is_orphan` | categorical | `true` / `false` | Computed from edge counts |
| `graph.node.edge_count` | numeric | int | Total edges |
| `graph.node.has_outgoing` | categorical | `true` / `false` | Has outgoing edges |

**Implementation:**
```python
class NodeIsOrphanSignal(NodeSignalDetector):
    signal_name = "graph.node.is_orphan"
    # Uses state.is_orphan @property

class NodeEdgeCountSignal(NodeSignalDetector):
    signal_name = "graph.node.edge_count"
    # Returns state.edge_count_incoming + state.edge_count_outgoing

class NodeHasOutgoingSignal(NodeSignalDetector):
    signal_name = "graph.node.has_outgoing"
    # Returns state.edge_count_outgoing > 0
```

### Task 5: Implement Strategy Repetition Signals

**File:** `src/methodologies/signals/technique/node_strategy_repetition.py` (new)

**Namespace:** `technique.node.*` (not `graph.node.*`)

**Signal:**

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `technique.node.strategy_repetition` | categorical | `none` / `low` / `medium` / `high` | Same strategy used repeatedly |

**Mapping:**
```python
consecutive = state.consecutive_same_strategy
if consecutive == 0: return "none"
elif consecutive <= 2: return "low"
elif consecutive <= 4: return "medium"
else: return "high"
```

### Task 6: Add Unit Tests

**File:** `tests/methodologies/signals/test_node_signals.py` (new)

**Test cases:**
- Test all exhaustion signals with various node states
- Test engagement signals (streak, recency)
- Test relationship signals (orphan, edge counts)
- Test strategy repetition signals
- Test signal detection with empty NodeStateTracker
- Test signal detection with multiple nodes

### Task 7: Register Signals in ComposedSignalDetector

**File:** `src/methodologies/signals/registry.py` (modify)

**Requirements:**
- Add node-level signal imports
- Make signals discoverable by ComposedSignalDetector
- Ensure proper namespacing (`graph.node.*`, `technique.node.*`)

## Signal Namespace Summary

| Namespace | Signals |
|-----------|---------|
| `graph.node.exhausted` | `true` / `false` |
| `graph.node.exhaustion_score` | 0.0 - 1.0 |
| `graph.node.yield_stagnation` | `true` / `false` |
| `graph.node.focus_streak` | `none` / `low` / `medium` / `high` |
| `graph.node.is_current_focus` | `true` / `false` |
| `graph.node.recency_score` | 0.0 - 1.0 |
| `graph.node.is_orphan` | `true` / `false` |
| `graph.node.edge_count` | int |
| `graph.node.has_outgoing` | `true` / `false` |
| `technique.node.strategy_repetition` | `none` / `low` / `medium` / `high` |

## Success Criteria

- [ ] Base class `NodeSignalDetector` created
- [ ] All 10 node-level signals implemented
- [ ] Signals registered in signal detector registry
- [ ] Unit tests pass (coverage > 80%)
- [ ] No ruff linting errors
- [ ] No pyright type errors
- [ ] Signals properly namespaced

## Dependencies

- Phase 1: NodeStateTracker must be complete ✅

## Next Phase

After Phase 2 completion, Phase 3 will implement joint strategy-node scoring using these signals.
