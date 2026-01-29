# Node Exhaustion and Backtracking Design

**Status:** Draft
**Date:** 2026-01-29
**Author:** Design exploration with user
**Related ADRs:** ADR-014 (Signal Pools), ADR-007 (YAML Methodology Schema)

## Context

### Problem Statement

The current interview system has a **"forgetful exploration"** problem:

1. **Recent node bias**: FocusSelectionService prioritizes `recent_nodes`, causing older nodes to fall out of scope
2. **No backtracking**: Once the system moves away from a branch, it never returns
3. **Exhausted branches**: The system can get stuck on a branch even when it's exhausted
4. **Strategy-node mismatch**: A strategy may score high due to specific node properties, but focus selection then targets a different node

### Current Architecture

```
Turn Pipeline:
  1. Detect signals (global context)
  2. Score strategies based on signals
  3. Select best strategy
  4. Select focus node from recent_nodes based on strategy preference
```

**The decoupling problem**: Strategy scoring considers global signals, but focus selection only sees `recent_nodes` (last ~5). This creates a mismatch where the strategy was selected for one context, but then targets a different node.

### User Requirements

1. **Exhaustion detection**: When a node yields no new information for N turns + shallow responses, it should be marked as exhausted
2. **Signal-driven scoring**: Exhausted nodes should score lower, allowing other nodes to come into focus
3. **Salience hierarchy**: Recent nodes are prioritized until exhausted, then focus "ripples out" to related nodes, then to unexplored branches
4. **Reversible exhaustion**: Exhausted nodes stay in the pool and keep getting scored (user may bring them up spontaneously)
5. **Distinguish exhaustion from extraction opportunity**: No graph change + shallow = exhausted; No graph change + deep = extraction opportunity (probe with different questions)

## Decision

### D1: Joint (Strategy, Node) Scoring

Replace the two-step process (score strategies, then select node) with **joint optimization** that scores (strategy, node) pairs together.

**Architecture:**
```
For each strategy in methodology:
  For each node in tracked_nodes (not just recent):
    Compute score = strategy_signal_weights × node_signals
Select (strategy, node) pair with highest score
```

**Key changes:**
1. Score `(strategy, node)` pairs instead of just strategies
2. Expand scope from `recent_nodes` to all tracked nodes
3. Node-level signals determine which nodes are viable targets
4. Exhaustion signals naturally lower scores for exhausted nodes

## Architecture

### 1. NodeStateTracker Service

**Purpose**: Maintain persistent per-node state across the interview session.

**Location**: `src/services/node_state_tracker.py`

**Core Parameters:**

```python
@dataclass
class NodeState:
    """Persistent state tracked for each node across the session."""

    # Basic
    node_id: str
    label: str
    created_at_turn: int
    depth: int

    # Engagement
    focus_count: int = 0
    last_focus_turn: Optional[int] = None
    turns_since_last_focus: int = 0
    current_focus_streak: int = 0  # Resets on yield or focus change

    # Yield
    last_yield_turn: Optional[int] = None
    turns_since_last_yield: int = 0
    yield_count: int = 0
    yield_rate: float = 0.0  # yield_count / max(focus_count, 1)

    # Response Quality (aggregated from LLM signals)
    all_response_depths: List[str] = field(default_factory=list)  # All depths from creation

    # Relationships
    connected_node_ids: Set[str] = field(default_factory=set)
    edge_count_outgoing: int = 0
    edge_count_incoming: int = 0
    # is_orphan computed dynamically: (edge_count_outgoing + edge_count_incoming) == 0

    # Strategy usage per node
    strategy_usage_count: Dict[str, int] = field(default_factory=dict)
    last_strategy_used: Optional[str] = None
    consecutive_same_strategy: int = 0
```

**Key Methods:**

```python
class NodeStateTracker:
    def __init__(self):
        self.states: Dict[str, NodeState] = {}
        self.previous_focus: Optional[str] = None

    def register_node(self, node: KGNode, turn_number: int) -> None:
        """Register a new node when it's added to the graph."""

    def update_focus(self, node_id: str, turn_number: int, strategy: str) -> None:
        """Called when a node is selected as focus."""

    def record_yield(self, node_id: str, turn_number: int, graph_changes: GraphChangeSummary) -> None:
        """Called when a node produces new graph changes (nodes/edges added)."""

    def append_response_signal(self, focus_node_id: str, response_depth: str) -> None:
        """Append response depth to the node that was asked about (previous focus)."""

    def update_edge_counts(self, node_id: str, outgoing_delta: int, incoming_delta: int) -> None:
        """Update edge counts when edges are added/removed."""
```

**Timing Clarification:**

```
Turn N:
  1. Receive user response to question from Turn N-1
  2. Extract concepts, update graph
  3. Detect llm.response_depth for current response
  4. Append response depth to focus node from Turn N-1
  5. Select new focus for Turn N
  6. Generate question for Turn N
```

**Response depth belongs to the node that was focused when the question was asked (Turn N-1), not the node being selected for the next question (Turn N).**

### 2. Node-Level Signals

Signals derived from NodeStateTracker, computed per node.

#### Exhaustion Signals

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `node.exhausted` | categorical | `true` / `false` | Primary exhaustion flag |
| `node.exhaustion_score` | numeric | 0.0 - 1.0 | Continuous score for fine-grained scoring |
| `node.yield_stagnation` | categorical | `true` / `false` | No yield for N consecutive focuses |

**Exhaustion Logic:**
```python
is_exhausted = (
    turns_since_last_yield >= 3 and
    current_focus_streak >= 2 and
    shallow_ratio >= 0.66  # 2/3 of recent responses are shallow
)
```

**Location**: `src/methodologies/signals/graph/node_exhaustion.py`

#### Engagement Signals

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `node.focus_streak` | categorical | `none` / `low` / `medium` / `high` | Consecutive turns focused |
| `node.is_current_focus` | categorical | `true` / `false` | Is this the current focus? |
| `node.recency_score` | numeric | 0.0 - 1.0 | Higher for more recent nodes |

**Location**: `src/methodologies/signals/graph/node_engagement.py`

#### Relationship Signals

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `node.is_orphan` | categorical | `true` / `false` | Computed from edge counts |
| `node.edge_count` | numeric | int | Total edges (incoming + outgoing) |
| `node.has_outgoing` | categorical | `true` / `false` | Node has outgoing edges |

**Location**: `src/methodologies/signals/graph/node_relationships.py`

#### Strategy Repetition Signals

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `node.strategy_repetition` | categorical | `none` / `low` / `medium` / `high` | Same strategy used repeatedly on this node |

**Location**: `src/methodologies/signals/technique/node_strategy_repetition.py` (namespace: `technique.*`)

### 3. Meta Signals (Composite)

#### Node Opportunity Signal

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `node.opportunity` | categorical | `exhausted` / `probe_deeper` / `fresh` | What action should be taken? |

**Logic:**
```python
if is_exhausted:
    opportunity = "exhausted"
elif streak == "high" and response_depth == "deep":
    opportunity = "probe_deeper"  # Deep responses but no yield
else:
    opportunity = "fresh"
```

**Location**: `src/methodologies/signals/meta/node_opportunity.py`

### 4. Global Signals (Existing)

| Signal Name | Namespace | Values | Purpose |
|-------------|-----------|--------|---------|
| Response Depth | `llm.response_depth` | surface/shallow/deep | For global engagement tracking |
| Global Trend | `llm.global_response_trend` | deepening/stable/shallowing/fatigued | Track fatigue, trigger revitalization |
| Graph State | `graph.*` | Various | For phase detection (not strategy selection) |

**New**: `llm.global_response_trend` for engagement tracking and fatigue detection.

#### Hedging Language Signal (New)

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `llm.hedging_language` | categorical | `none` / `low` / `medium` / `high` | Detect uncertainty, trigger validation |

**Location**: `src/methodologies/signals/llm/hedging_language.py`

**Usage**: High hedging/uncertainty → validation strategy to clarify understanding.

### 5. Interview Phase Detection

**Purpose**: Graph signals (`graph.node_count`, `graph.max_depth`, `graph.orphan_count`) trigger interview phases, which configure signal weights for strategies.

**Location**: `src/methodologies/signals/meta/interview_phase.py`

| Phase | Trigger | Strategy Weights |
|-------|---------|------------------|
| `early` | node_count < 5 | Boost: explore, clarify |
| `mid` | node_count < 15 or orphan_count > 3 | Boost: deepen, probe |
| `late` | node_count >= 15 | Boost: validate, reflect |

**YAML Configuration:**
```yaml
methodology: means_end_chain

phases:
  early:
    signal_weights:
      explore: 1.5
      clarify: 1.2
      deepen: 0.5
      validate: 0.2

  mid:
    signal_weights:
      deepen: 1.3
      probe: 1.0
      explore: 0.8
      clarify: 0.7

  late:
    signal_weights:
      validate: 1.5
      reflect: 1.2
      deepen: 0.5
      explore: 0.3
```

### 6. Strategy-Node Joint Scoring

**Modified MethodologyStrategyService:**

```python
class MethodologyStrategyService:
    async def select_strategy_and_focus(
        self, context, graph_state, response_text
    ) -> Tuple[str, Optional[str], List[Tuple[str, float]], Optional[Dict]]:
        """
        Select best (strategy, node) pair using joint scoring.

        Returns:
            (strategy_name, focus_node, alternatives, signals)
        """

        # 1. Detect global signals
        global_signals = await self.detect_global_signals(context, graph_state, response_text)

        # 2. Detect node-level signals for all tracked nodes
        all_node_states = self.node_tracker.states
        node_signals = await self.detect_node_signals(all_node_states, context, graph_state, response_text)

        # 3. Score each (strategy, node) pair
        scored_pairs = []
        for strategy in self.strategies:
            for node_id, node_signal_dict in node_signals.items():
                # Combine global + node signals
                combined_signals = {**global_signals, **node_signal_dict}

                # Score strategy for this specific node
                score = self.score_strategy(strategy, combined_signals)
                scored_pairs.append((score, strategy.name, node_id))

        # 4. Select best pair
        best_score, best_strategy, best_node = max(scored_pairs, key=lambda x: x[0])

        return best_strategy, best_node, alternatives, global_signals
```

**Location**: `src/services/methodology_strategy_service.py` (modify existing)

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
    ├─ Detect global signals
    ├─ Detect node-level signals (from NodeStateTracker)
    ├─ Detect meta signals (node.opportunity, interview.phase)
    ├─ Score (strategy, node) pairs for all tracked nodes
    └─ Select best pair
    ↓
8. Update NodeStateTracker.update_focus(best_node, best_strategy)
    ↓
9. Question Generation with selected strategy/focus
    ↓
10. Return to user
```

## Implementation Phases

### Phase 1: NodeStateTracker Foundation
- Create NodeState dataclass
- Implement NodeStateTracker service
- Wire into pipeline after graph update stage
- Add basic tests

### Phase 2: Node-Level Signals
- Implement exhaustion signals
- Implement engagement signals
- Implement relationship signals
- Implement strategy repetition signals
- Add signal tests

### Phase 3: Joint Strategy-Node Scoring
- Modify MethodologyStrategyService for joint scoring
- Update YAML configs to reference node signals
- Add integration tests

### Phase 4: Meta Signals and Phasing
- Implement node.opportunity meta signal
- Implement interview.phase detection
- Add phase-based YAML configuration
- Update existing YAML configs

### Phase 5: Global Response Tracking
- Implement llm.global_response_trend
- Implement llm.hedging_language
- Add validation strategy trigger for uncertainty
- Test fatigue detection and revitalization

### Phase 6: Testing and Calibration
- Synthetic interviews with various scenarios
- Signal weight tuning
- Validation of exhaustion detection
- Validation of backtracking behavior

## Tradeoffs

**Pros:**
- Exhausted nodes naturally deprioritized without explicit filtering
- Signal-driven approach allows fine-tuned behavior via YAML
- Reversible exhaustion (nodes stay in pool)
- Distinguishes exhaustion from extraction opportunity
- Supports interview phasing for different conversation stages
- Validation triggered by uncertainty/hedging signals

**Cons:**
- More computation (O(strategies × nodes) vs O(strategies))
- Complex signal dependency graph
- Requires careful signal weight calibration
- NodeStateTracker adds state management complexity
- More signals to maintain and test

## Alternatives Considered

1. **Filter exhausted nodes from recent_nodes**: Rejected — filtering loses information, computation isn't a constraint
2. **Enhance FocusSelectionService with scoring**: Rejected — still has two-step decoupling problem
3. **Signal-based penalty (meta-signal)**: Rejected — user prefers node-level signals in graph pool
4. **Remove validation strategy**: Rejected — validation serves purpose for uncertainty/hedging detection

## Related Issues

- interview-system-v2-1xx: Set up LLM infrastructure for LLM signal extraction
- interview-system-v2-6c1: Make CoverageBreadthSignal method-agnostic
- interview-system-v2-4rz: Fix ruff and pyright linting issues
- **Bead needed**: Interview phasing system

## Future Considerations

1. **Signal cost optimization**: Use cost_tier to skip expensive signals when not needed
2. **Adaptive thresholds**: Make exhaustion threshold configurable or adaptive based on interview length
3. **Machine learning**: Learn optimal signal weights from interview outcomes
4. **Multi-morphology support**: Different signal weight profiles for different interview types
