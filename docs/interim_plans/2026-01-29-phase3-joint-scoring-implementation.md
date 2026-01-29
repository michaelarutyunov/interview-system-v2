# Phase 3: Joint Strategy-Node Scoring Implementation Plan

**Status:** Ready for Implementation
**Date:** 2026-01-29
**Parent Bead:** interview-system-v2-xil

## Overview

Modify the scoring system to evaluate (strategy, node) pairs jointly instead of scoring strategies alone. This is the core of D1 architecture that enables automatic backtracking to non-exhausted nodes.

## Tasks

### Task 1: Create Node-Aware Strategy Scoring Module

**File:** `src/methodologies/scoring.py` (modify)

**Requirements:**
- Add new function `rank_strategy_node_pairs()` for joint scoring
- Keep existing `rank_strategies()` for backward compatibility
- Node-level signals should be merged with global signals when scoring

**New function signature:**
```python
def rank_strategy_node_pairs(
    strategies: List[StrategyConfig],
    global_signals: Dict[str, Any],
    node_signals: Dict[str, Dict[str, Any]],  # {node_id: {signal_name: value}}
    node_tracker: NodeStateTracker
) -> List[Tuple[StrategyConfig, str, float]]:  # [(strategy, node_id, score), ...]
```

**Scoring logic:**
```python
for strategy in strategies:
    for node_id, node_signal_dict in node_signals.items():
        # Merge global + node signals
        combined_signals = {**global_signals, **node_signal_dict}

        # Score strategy for this specific node
        score = score_strategy_with_weights(strategy, combined_signals)
        scored_pairs.append((strategy, node_id, score))

# Sort by score descending
return sorted(scored_pairs, key=lambda x: x[2], reverse=True)
```

### Task 2: Modify MethodologyStrategyService

**File:** `src/services/methodology_strategy_service.py` (modify)

**Requirements:**
- Add method `select_strategy_and_focus()` for joint scoring
- Keep existing `select_strategy()` for backward compatibility
- Pass NodeStateTracker to signal detector
- Detect both global and node-level signals

**New method:**
```python
async def select_strategy_and_focus(
    self,
    context: PipelineContext,
    graph_state: GraphState,
    response_text: str
) -> Tuple[str, Optional[str], List[Tuple[str, float]], Optional[Dict]]:
    """
    Select best (strategy, node) pair using joint scoring.

    Returns:
        (strategy_name, focus_node, alternatives, global_signals)
    """
```

**Implementation:**
1. Get NodeStateTracker from context (or initialize if needed)
2. Detect global signals using existing signal detector
3. Detect node-level signals for all tracked nodes
4. Score all (strategy, node) pairs using `rank_strategy_node_pairs()`
5. Select best pair
6. Return strategy name, node ID, alternatives, and global signals

### Task 3: Update StrategySelectionStage

**File:** `src/services/turn_pipeline/stages/strategy_selection_stage.py` (modify)

**Requirements:**
- Use `select_strategy_and_focus()` instead of `select_strategy()`
- Update focus handling to use node ID directly
- Update logging to include node information

**Changes:**
```python
# Old:
strategy, focus, alternatives, signals = await self._select_strategy_with_methodology(context)

# New:
strategy, focus_node_id, alternatives, signals = await self._select_strategy_and_node(context)

# Wrap node_id in dict format
focus_dict = {"focus_node_id": focus_node_id} if focus_node_id else None
```

### Task 4: Update FocusSelectionService or Deprecate

**Decision point:** With joint scoring, FocusSelectionService may no longer be needed.

**Options:**
- **A**: Deprecate FocusSelectionService (node is selected during scoring)
- **B**: Keep as fallback for backward compatibility

**Recommendation:** Option A - Deprecate FocusSelectionService since joint scoring handles focus selection.

**File:** `src/services/focus_selection_service.py` (modify)

- Add deprecation warning if called
- Document that joint scoring replaces this service

### Task 5: Update YAML Configs for Node Signals

**Files:**
- `src/methodologies/config/means_end_chain.yaml` (modify)
- `src/methodologies/config/jobs_to_be_done.yaml` (modify)

**Add node-level signal weights:**

```yaml
strategies:
  - name: deepen
    technique: laddering
    signal_weights:
      # Global signals
      llm.response_depth.surface: 0.8
      # Node-level signals
      graph.node.exhausted.false: 1.0  # Boost non-exhausted nodes
      graph.node.focus_streak.low: 0.5  # Prefer fresh nodes
      graph.node.exhaustion_score.low: 0.7  # Avoid exhausted nodes

  - name: clarify
    technique: probing
    signal_weights:
      graph.node.is_orphan.true: 1.0  # Boost orphan nodes
      graph.node.exhausted.false: 0.5
      graph.node.focus_streak.none: 0.3

  - name: explore
    technique: elaboration
    signal_weights:
      graph.node.focus_streak.none: 1.0  # Fresh nodes
      graph.node.yield_stagnation.false: 0.8  # Nodes that yield
      graph.node.exhausted.false: 0.7

  - name: reflect
    technique: validation
    signal_weights:
      graph.node.edge_count.high: 0.8  # Well-connected nodes
      graph.node.focus_streak.high: 0.5  # Often-focused nodes
      graph.node.strategy_repetition.low: 0.3  # Avoid overusing same strategy
```

### Task 6: Add Integration Tests

**File:** `tests/integration/test_joint_strategy_node_scoring.py` (new)

**Test cases:**
- Test joint scoring with multiple nodes and strategies
- Test exhausted node gets lower score
- Test orphan node gets boosted for clarify strategy
- Test fresh node gets boosted for explore strategy
- Test full pipeline integration with joint scoring
- Test backward compatibility (if keeping old methods)

### Task 7: Update Documentation

**Files to update:**
- `docs/adr/ADR-014-signal-pools-architecture.md` - Add section on joint scoring
- `docs/SYSTEM_DESIGN.md` - Update architecture diagram
- Any relevant README files

## Success Criteria

- [ ] `rank_strategy_node_pairs()` function implemented in scoring.py
- [ ] `MethodologyStrategyService.select_strategy_and_focus()` implemented
- [ ] StrategySelectionStage updated to use joint scoring
- [ ] YAML configs updated with node-level signal weights
- [ ] Integration tests pass
- [ ] Backward compatibility maintained (if applicable)
- [ ] No ruff linting errors
- [ ] No pyright type errors

## Dependencies

- Phase 1: NodeStateTracker ✅
- Phase 2: Node-Level Signals ✅

## Data Flow (Updated)

```
User Response (Turn N)
    ↓
1. Extraction → Add nodes/edges to graph
    ↓
2. NodeStateTracker updates (register nodes, update edges, record yield)
    ↓
3. Detect global signals (llm.response_depth, etc.)
    ↓
4. Detect node-level signals (for all tracked nodes)
    ↓
5. MethodologyStrategyService.select_strategy_and_focus()
    ├─ Get all strategies from YAML
    ├─ Get all tracked nodes from NodeStateTracker
    ├─ Score each (strategy, node) pair
    │   └─ Merge global + node signals
    │   └─ Apply strategy weights from YAML
    └─ Select best (strategy, node) pair
    ↓
6. Update NodeStateTracker with new focus
    ↓
7. Question Generation with selected strategy/focus node
    ↓
8. Return to user
```

## Key Implementation Notes

1. **Node signals take precedence**: When scoring, node-level signals can override global signal weights via YAML configuration

2. **Exhaustion naturally deprioritizes**: No explicit filtering needed — exhausted nodes score lower due to `graph.node.exhausted.true: -1.0` or similar weights

3. **Salience hierarchy emerges**: Recent nodes have better engagement metrics, orphans have explicit boost, etc. — all via signal weights

4. **Backtracking is automatic**: When current node exhausts, other nodes with better signal profiles naturally score higher

## Next Phase

After Phase 3 completion, Phase 4 will implement meta signals (node.opportunity) and interview phasing.
