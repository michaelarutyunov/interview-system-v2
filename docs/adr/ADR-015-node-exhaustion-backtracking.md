# ADR-015: Node Exhaustion and Backtracking System

**Status:** Accepted
**Date:** 2026-01-29
**Supersedes:** None
**Related:** ADR-014 (Signal Pools), ADR-013 (Methodology-Centric Architecture), ADR-007 (YAML-Based Methodology Schema)

## Context

### Problem Statement

The interview system exhibited a **"forgetful exploration"** problem where nodes could be repeatedly focused without yielding new information, while other potentially valuable nodes fell out of scope.

#### Specific Issues:

1. **Recent node bias**: `FocusSelectionService` prioritized `recent_nodes` (last ~5 nodes), causing older nodes to disappear from consideration even if they were not fully explored
2. **No backtracking**: Once the system moved away from a branch, it never returned to explore related or orphaned nodes
3. **Exhausted branches**: The system could get stuck on a branch even when it was exhausted (no new information yield + shallow responses)
4. **Strategy-node mismatch**: A strategy might score high based on global signals, but focus selection would then target a different node from the recent set, creating a decoupling between strategy selection and node targeting
5. **No per-node state**: The system lacked persistent state tracking for individual nodes across the interview session

#### User Requirements:

1. **Exhaustion detection**: When a node yields no new information for N turns + shallow responses, it should be marked as exhausted
2. **Signal-driven scoring**: Exhausted nodes should score lower, allowing other nodes to come into focus
3. **Salience hierarchy**: Recent nodes prioritized until exhausted, then focus "ripples out" to related nodes, then to unexplored branches
4. **Reversible exhaustion**: Exhausted nodes stay in the pool and keep getting scored (user may bring them up spontaneously)
5. **Distinguish exhaustion from extraction opportunity**: No graph change + shallow = exhausted; No graph change + deep = extraction opportunity (probe with different questions)

### Existing Architecture

```
Turn Pipeline:
  1. Detect signals (global context)
  2. Score strategies based on signals
  3. Select best strategy
  4. Select focus node from recent_nodes based on strategy preference
```

**The decoupling problem**: Strategy scoring considered global signals, but focus selection only saw `recent_nodes` (last ~5). This created a mismatch where a strategy was selected for one context, but then targeted a different node.

## Decision

Implement a **node exhaustion and backtracking system** with the following components:

### 1. NodeStateTracker Service

Introduce a persistent state tracking service for each knowledge graph node that maintains:

- **Engagement metrics**: focus_count, last_focus_turn, current_focus_streak, turns_since_last_focus
- **Yield metrics**: yield_count, yield_rate, turns_since_last_yield, last_yield_turn
- **Response quality aggregation**: all_response_depths, shallow_ratio, deep_ratio
- **Relationship tracking**: edge_count_incoming, edge_count_outgoing, connected_node_ids
- **Strategy usage patterns**: strategy_usage_count, last_strategy_used, consecutive_same_strategy

**Location**: `src/services/node_state_tracker.py`

### 2. Node-Level Signals

Create node-level signals derived from `NodeStateTracker`:

#### Exhaustion Signals:
- `graph.node.exhausted`: Categorical (true/false) - Primary exhaustion flag
- `graph.node.exhaustion_score`: Numeric (0.0-1.0) - Continuous score for fine-grained scoring
- `graph.node.yield_stagnation`: Categorical (true/false) - No yield for 3+ consecutive focuses

**Exhaustion logic**:
```python
is_exhausted = (
    turns_since_last_yield >= 3 and
    current_focus_streak >= 2 and
    shallow_ratio >= 0.66  # 2/3 of recent responses are shallow
)
```

#### Engagement Signals:
- `graph.node.focus_streak`: Categorical (none/low/medium/high) - Consecutive turns focused
- `graph.node.is_current_focus`: Categorical (true/false) - Is this the current focus?
- `graph.node.recency_score`: Numeric (0.0-1.0) - Higher for more recent nodes (1.0=current, 0.0=20+ turns ago)

#### Relationship Signals:
- `graph.node.is_orphan`: Categorical (true/false) - Node has no edges
- `graph.node.edge_count`: Numeric (int) - Total edges (incoming + outgoing)
- `graph.node.has_outgoing`: Categorical (true/false) - Node has outgoing edges

#### Strategy Repetition Signals:
- `technique.node.strategy_repetition`: Categorical (none/low/medium/high) - Same strategy used repeatedly on this node

### 3. Joint Strategy-Node Scoring (Phase 3)

Replace the two-step process (score strategies, then select node) with **joint optimization** that scores (strategy, node) pairs together:

```python
for strategy in methodology.strategies:
    for node_id in tracked_nodes:  # All nodes, not just recent
        combined_signals = {**global_signals, **node_signals[node_id]}
        score = score_strategy(strategy, combined_signals)
        scored_pairs.append((score, strategy.name, node_id))

best_score, best_strategy, best_node = max(scored_pairs)
```

**Key changes**:
1. Score `(strategy, node)` pairs instead of just strategies
2. Expand scope from `recent_nodes` to all tracked nodes
3. Node-level signals determine which nodes are viable targets
4. Exhaustion signals naturally lower scores for exhausted nodes

### 4. Phase-Based Weight Multipliers (Phase 4)

Add interview phase detection that configures signal weights for different conversation stages:

| Phase | Trigger | Strategy Weights |
|-------|---------|------------------|
| `early` | node_count < 5 | Boost: explore, clarify |
| `mid` | node_count < 15 or orphan_count > 3 | Boost: deepen, probe |
| `late` | node_count >= 15 | Boost: validate, reflect |

**Location**: `src/methodologies/signals/meta/interview_phase.py`

### 5. Global Response Tracking (Phase 5)

Add global signals for engagement tracking and fatigue detection:

- `llm.global_response_trend`: Categorical (deepening/stable/shallowing/fatigued) - Track response quality trends across interview
- `llm.hedging_language`: Categorical (none/low/medium/high) - Detect uncertainty, trigger validation

### 6. Meta Signals

Composite signals derived from other signals:

- `meta.node.opportunity`: Categorical (exhausted/probe_deeper/fresh) - What action should be taken for this node?
- `meta.interview.phase`: Categorical (early/mid/late) - Current interview phase

## Implementation

### Phase 1: NodeStateTracker Foundation
- Created `NodeState` dataclass with comprehensive per-node state
- Implemented `NodeStateTracker` service with registration and update methods
- Wired into pipeline after graph update stage
- Added basic tests

### Phase 2: Node-Level Signals
- Implemented exhaustion signals (`node_exhaustion.py`)
- Implemented engagement signals (`node_engagement.py`)
- Implemented relationship signals (`node_relationships.py`)
- Implemented strategy repetition signals (`node_strategy_repetition.py`)
- Added signal tests

### Phase 3: Joint Strategy-Node Scoring
- Modified `MethodologyStrategyService` for joint scoring
- Updated scoring to expand scope from `recent_nodes` to all tracked nodes
- Updated pipeline contracts to handle `(strategy, node, score)` tuples
- Added integration tests

### Phase 4: Meta Signals and Phasing
- Implemented `node.opportunity` meta signal
- Implemented `interview.phase` detection
- Added phase-based YAML configuration
- Updated existing YAML configs for phase-aware weights

### Phase 5: Global Response Tracking
- Implemented `llm.global_response_trend` signal
- Implemented `llm.hedging_language` signal
- Added validation strategy trigger for uncertainty
- Tested fatigue detection and revitalization

### Phase 6: Testing and Calibration
- Created synthetic interviews with various scenarios
- Tuned signal weights for optimal behavior
- Validated exhaustion detection accuracy
- Validated backtracking behavior

## Consequences

### Positive

- **Better interview quality**: Automatic backtracking ensures no valuable nodes are left unexplored
- **Improved signal detection**: Node-level signals provide granular context for strategy selection
- **Natural deprioritization**: Exhausted nodes naturally score lower without explicit filtering
- **Reversible exhaustion**: Nodes stay in the pool and can be revisited if user brings them up
- **Salience hierarchy**: Recent nodes prioritized until exhausted, then focus expands outward
- **Distinguishes exhaustion from extraction**: Deep responses without yield trigger probing, not abandonment
- **Interview phasing**: Different conversation stages get appropriate strategy weights
- **Validation triggered by uncertainty**: Hedging/uncertainty signals trigger validation strategy

### Negative

- **Increased computation**: O(strategies × nodes) vs O(strategies) - more scoring operations
- **Complex signal dependency graph**: Node-level signals depend on NodeStateTracker, which depends on graph updates
- **State management complexity**: NodeStateTracker adds persistent state that must be maintained correctly
- **Signal weight calibration**: More signals require careful tuning to avoid unexpected behavior
- **Pipeline contract changes**: Joint scoring required updating pipeline contracts and UI components

### Neutral

- **YAML configuration**: Phase-based weights add configuration complexity but enable flexible interview progression
- **Signal namespace expansion**: Added `graph.node.*` and `technique.node.*` namespaces for node-level signals
- **Response timing**: Response depth is recorded for the node that was focused when question was asked (previous turn), not the node being selected for next question

## Alternatives Considered

1. **Filter exhausted nodes from recent_nodes**: Rejected - filtering loses information, and computation isn't a constraint
2. **Enhance FocusSelectionService with scoring**: Rejected - still has two-step decoupling problem between strategy and node
3. **Signal-based penalty (meta-signal)**: Rejected - user prefers node-level signals in graph pool for better observability
4. **Remove validation strategy**: Rejected - validation serves important purpose for uncertainty/hedging detection
5. **Keep only recent_nodes**: Rejected - doesn't solve the backtracking problem or orphaned nodes

## Migration Path

### For Existing Code

1. **Pipeline contracts**: Updated `StrategySelectionOutput.strategy_alternatives` to handle both `(strategy, score)` and `(strategy, node, score)` formats
2. **UI components**: Updated scoring panel to handle tuple-based alternatives instead of dicts
3. **API responses**: Added `phase` field to session status response
4. **Signal consumers**: Updated to consume namespaced node-level signals

### For New Methodologies

1. Define node-level signals in YAML config under `signals.graph.node`
2. Configure phase-based weights in `phases.{early,mid,late}.signal_weights`
3. Ensure strategies can handle node-specific context

## Data Flow

```
User Response (Turn N)
    ↓
1. Extraction → Add nodes/edges to graph
    ↓
2. NodeStateTracker.register_node() for new nodes
    ↓
3. NodeStateTracker.update_edge_counts() for new edges
    ↓
4. NodeStateTracker.record_yield() if graph changed
    ↓
5. Detect LLM signals (response_depth, hedging_language)
    ↓
6. NodeStateTracker.append_response_signal(previous_focus, response_depth)
    ↓
7. MethodologyStrategyService.select_strategy_and_focus()
    ├─ Detect global signals (llm.*, graph.*)
    ├─ Detect node-level signals (graph.node.*, technique.node.*)
    ├─ Detect meta signals (node.opportunity, interview.phase)
    ├─ Apply phase-based weight multipliers
    ├─ Score (strategy, node) pairs for all tracked nodes
    └─ Select best pair
    ↓
8. Update NodeStateTracker.update_focus(best_node, best_strategy)
    ↓
9. Question Generation with selected strategy/focus
    ↓
10. Return to user
```

## References

- Design document: `docs/plans/2026-01-29-node-exhaustion-backtracking-design.md`
- Code quality report: `docs/reports/2026-01-29-code-quality-and-ui-audit.md`
- ADR-014: Signal Pools Architecture
- ADR-013: Methodology-Centric Architecture
- ADR-007: YAML-Based Methodology Schema

## Implementation Status

- [x] NodeStateTracker service implementation
- [x] Node-level signals (exhaustion, engagement, relationships, strategy repetition)
- [x] Joint strategy-node scoring in MethodologyStrategyService
- [x] Interview phase detection
- [x] Phase-based YAML configuration
- [x] Global response tracking signals
- [x] Meta signals (node.opportunity, interview.phase)
- [x] Pipeline contract updates
- [x] UI component updates for tuple-based alternatives
- [x] Integration tests
- [x] Synthetic interview tests

## Future Considerations

1. **Signal cost optimization**: Use cost_tier to skip expensive signals when not needed
2. **Adaptive thresholds**: Make exhaustion threshold configurable or adaptive based on interview length
3. **Machine learning**: Learn optimal signal weights from interview outcomes
4. **Multi-morphology support**: Different signal weight profiles for different interview types
5. **Node clustering**: Group related nodes for more intelligent backtracking
6. **Exhaustion decay**: Allow exhausted nodes to gradually recover over time
