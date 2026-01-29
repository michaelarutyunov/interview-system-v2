# Phase 1: NodeStateTracker Implementation Plan

**Status:** Ready for Implementation
**Date:** 2026-01-29
**Parent Bead:** interview-system-v2-416

## Overview

Implement the NodeStateTracker service that maintains persistent per-node state across the interview session. This is the foundation for node-level signals and joint strategy-node scoring.

## Tasks

### Task 1: Create NodeState Dataclass

**File:** `src/domain/models/node_state.py` (new)

**Requirements:**
- Create `NodeState` dataclass with all parameters from design doc
- Implement `is_orphan` as a @property (computed from edge counts)
- Add type hints for all fields
- Add docstrings

**Fields:**
```python
@dataclass
class NodeState:
    # Basic
    node_id: str
    label: str
    created_at_turn: int
    depth: int

    # Engagement
    focus_count: int = 0
    last_focus_turn: Optional[int] = None
    turns_since_last_focus: int = 0
    current_focus_streak: int = 0

    # Yield
    last_yield_turn: Optional[int] = None
    turns_since_last_yield: int = 0
    yield_count: int = 0
    yield_rate: float = 0.0

    # Response Quality
    all_response_depths: List[str] = field(default_factory=list)

    # Relationships
    connected_node_ids: Set[str] = field(default_factory=set)
    edge_count_outgoing: int = 0
    edge_count_incoming: int = 0

    # Strategy usage per node
    strategy_usage_count: Dict[str, int] = field(default_factory=dict)
    last_strategy_used: Optional[str] = None
    consecutive_same_strategy: int = 0

    @property
    def is_orphan(self) -> bool:
        return (self.edge_count_incoming + self.edge_count_outgoing) == 0
```

### Task 2: Implement NodeStateTracker Service

**File:** `src/services/node_state_tracker.py` (new)

**Requirements:**
- Create `NodeStateTracker` class
- Implement all core methods
- Use structlog for logging
- Handle edge cases (node not found, etc.)

**Methods:**

```python
class NodeStateTracker:
    def __init__(self):
        self.states: Dict[str, NodeState] = {}
        self.previous_focus: Optional[str] = None

    async def register_node(
        self,
        node: KGNode,
        turn_number: int
    ) -> NodeState:
        """Register a new node when it's added to the graph.
        Creates new NodeState or returns existing if already registered."""

    async def update_focus(
        self,
        node_id: str,
        turn_number: int,
        strategy: str
    ) -> None:
        """Called when a node is selected as focus.
        Updates focus_count, last_focus_turn, current_focus_streak.
        Resets current_focus_streak if focus changed from previous turn.
        Updates strategy_usage_count and consecutive_same_strategy."""

    async def record_yield(
        self,
        node_id: str,
        turn_number: int,
        graph_changes: GraphChangeSummary
    ) -> None:
        """Called when a node produces new graph changes.
        Updates last_yield_turn, turns_since_last_yield, yield_count.
        Resets current_focus_streak to 0 (yield breaks the streak).
        Recalculates yield_rate."""

    async def append_response_signal(
        self,
        focus_node_id: str,
        response_depth: str
    ) -> None:
        """Append response depth to the node that was asked about.
        This should be the focus from the PREVIOUS turn."""

    async def update_edge_counts(
        self,
        node_id: str,
        outgoing_delta: int,
        incoming_delta: int
    ) -> None:
        """Update edge counts when edges are added/removed.
        Updates edge_count_outgoing and edge_count_incoming."""

    def get_state(self, node_id: str) -> Optional[NodeState]:
        """Get NodeState for a node, or None if not tracked."""

    def get_all_states(self) -> Dict[str, NodeState]:
        """Get all tracked node states."""
```

**Supporting types needed:**
```python
@dataclass
class GraphChangeSummary:
    """Summary of graph changes for yield detection."""
    nodes_added: int
    edges_added: int
    nodes_modified: int
```

### Task 3: Wire into Turn Pipeline

**File:** `src/services/turn_pipeline/stages/graph_update_stage.py` (modify)

**Integration points:**

1. **After node creation:** Call `node_tracker.register_node()`
   - In `GraphUpdateStage.process()` after adding nodes to graph

2. **After edge creation:** Call `node_tracker.update_edge_counts()`
   - After edges are added to graph

3. **After graph update:** Call `node_tracker.record_yield()` if changes detected
   - Calculate `GraphChangeSummary` from added nodes/edges

**File:** `src/services/turn_pipeline/context.py` (modify)

4. **Add NodeStateTracker to PipelineContext**
   - Initialize in context creation
   - Pass to stages that need it

### Task 4: Add Basic Unit Tests

**File:** `tests/unit/test_node_state_tracker.py` (new)

**Test cases:**
- Test node registration
- Test focus updates (single, consecutive, changed)
- Test yield recording and streak reset
- Test response signal appending
- Test edge count updates
- Test `is_orphan` property computation
- Test `yield_rate` calculation
- Test strategy usage tracking

### Task 5: Add to Domain Models Export

**File:** `src/domain/models/__init__.py` (modify)

**Export NodeState:**
```python
from .node_state import NodeState
```

## Integration Points

### Pipeline Integration

```
Turn Pipeline Flow:
  1. ContextLoadingStage
  2. ExtractionStage
  3. GraphUpdateStage
     ├─ Add nodes → NodeStateTracker.register_node()
     ├─ Add edges → NodeStateTracker.update_edge_counts()
     └─ Record yield → NodeStateTracker.record_yield()
  4. StateComputationStage
  5. StrategySelectionStage
     └─ Will use NodeStateTracker in Phase 3
  6. QuestionGenerationStage
  7. ResponseSavingStage
```

### Context Access

PipelineContext will have:
```python
context.node_tracker: NodeStateTracker
```

Stages can access via:
```python
node_state = context.node_tracker.get_state(node_id)
```

## Success Criteria

- [ ] NodeState dataclass created with all fields
- [ ] NodeStateTracker service implemented with all methods
- [ ] Integrated into turn pipeline after graph updates
- [ ] NodeStateTracker accessible via PipelineContext
- [ ] Unit tests pass (coverage > 80%)
- [ ] No ruff linting errors
- [ ] No pyright type errors

## Dependencies

- None (this is the foundation phase)

## Next Phase

After Phase 1 completion, Phase 2 will implement node-level signals that read from NodeStateTracker.
