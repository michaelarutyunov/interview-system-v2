# Phase 4: Meta Signals and Interview Phasing Implementation Plan

**Status:** Ready for Implementation
**Date:** 2026-01-29
**Parent Bead:** interview-system-v2-agm

## Overview

Implement meta signals (composite signals that combine other signals) and interview phase detection. Phase detection uses graph signals to determine interview stage (early/mid/late), which then configures signal weights for strategies.

## Tasks

### Task 1: Implement Node Opportunity Meta Signal

**File:** `src/methodologies/signals/meta/node_opportunity.py` (new)

**Signal:**

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `meta.node.opportunity` | categorical | `exhausted` / `probe_deeper` / `fresh` | What action should be taken? |

**Logic:**
```python
if is_exhausted:
    opportunity = "exhausted"
elif streak == "high" and response_depth == "deep":
    opportunity = "probe_deeper"  # Deep responses but no yield
else:
    opportunity = "fresh"
```

**Implementation:**
```python
class NodeOpportunitySignal(SignalDetector):
    """Meta signal: what's the best action for this node?"""

    signal_name = "meta.node.opportunity"
    cost_tier = SignalCostTier.MEDIUM  # Depends on node signals
    refresh_trigger = RefreshTrigger.PER_TURN

    def __init__(self, node_tracker: NodeStateTracker):
        self.node_tracker = node_tracker
        # Create signal detectors for dependency signals
        self.exhausted_signal = NodeExhaustedSignal(node_tracker)
        self.streak_signal = NodeFocusStreakSignal(node_tracker)

    async def detect(
        self, context, graph_state, response_text
    ) -> Dict[str, str]:
        # First detect dependency signals
        # Then compute opportunity
        pass
```

### Task 2: Implement Interview Phase Detection Signal

**File:** `src/methodologies/signals/meta/interview_phase.py` (new)

**Signal:**

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `meta.interview.phase` | categorical | `early` / `mid` / `late` | Current interview phase |

**Phase Logic:**
```python
node_count = graph_state.node_count
max_depth = graph_state.max_depth
orphan_count = graph_state.orphan_count

if node_count < 5:
    return "early"
elif node_count < 15 or orphan_count > 3:
    return "mid"
else:
    return "late"
```

**Implementation:**
```python
class InterviewPhaseSignal(SignalDetector):
    """Detect interview phase based on graph state."""

    signal_name = "meta.interview.phase"
    cost_tier = SignalCostTier.FREE  # Uses graph_state counts
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(
        self, context, graph_state, response_text
    ) -> str:
        # Returns "early" | "mid" | "late"
        pass
```

### Task 3: Add Phase-Based Configuration to YAML

**Files:**
- `src/methodologies/config/means_end_chain.yaml` (modify)
- `src/methodologies/config/jobs_to_be_done.yaml` (modify)

**Add phases section:**

```yaml
methodology: means_end_chain

phases:
  early:
    description: "Initial exploration, building graph structure"
    signal_weights:
      explore: 1.5
      clarify: 1.2
      deepen: 0.5
      reflect: 0.2

  mid:
    description: "Building depth and connections"
    signal_weights:
      deepen: 1.3
      probe: 1.0
      explore: 0.8
      clarify: 0.7

  late:
    description: "Validation and verification"
    signal_weights:
      validate: 1.5
      reflect: 1.2
      deepen: 0.5
      explore: 0.3
```

**Note:** Phase-based weights are multipliers applied on top of base signal weights.

### Task 4: Modify MethodologyConfig Schema

**File:** `src/methodologies/config.py` (modify)

**Requirements:**
- Add `PhaseConfig` class for phase definitions
- Add `phases` field to `MethodologyConfig`
- Update config loading to include phases

**Schema:**
```python
@dataclass
class PhaseConfig:
    """Configuration for an interview phase."""
    name: str
    description: str
    signal_weights: Dict[str, float]  # Multipliers for strategies

@dataclass
class MethodologyConfig:
    # ... existing fields ...
    phases: Optional[Dict[str, PhaseConfig]] = None  # phase_name -> config
```

### Task 5: Apply Phase Weights in Scoring

**File:** `src/methodologies/scoring.py` (modify)

**Requirements:**
- Modify `rank_strategies()` and `rank_strategy_node_pairs()` to accept optional phase weights
- Apply phase multipliers to final scores

**Changes:**
```python
def rank_strategy_node_pairs(
    strategies: List[StrategyConfig],
    global_signals: Dict[str, Any],
    node_signals: Dict[str, Dict[str, Any]],
    node_tracker: NodeStateTracker,
    phase_weights: Optional[Dict[str, float]] = None,  # NEW
) -> List[Tuple[StrategyConfig, str, float]]:

    # After computing base score:
    if phase_weights and strategy.name in phase_weights:
        multiplier = phase_weights[strategy.name]
        score *= multiplier
```

### Task 6: Integrate Phase Detection into Pipeline

**File:** `src/services/methodology_strategy_service.py` (modify)

**Requirements:**
- Detect interview phase in `select_strategy_and_focus()`
- Pass phase weights to scoring function
- Log phase for observability

**Implementation:**
```python
async def select_strategy_and_focus(...):
    # ... existing code ...

    # Detect interview phase
    phase_signal = InterviewPhaseSignal()
    current_phase = await phase_signal.detect(context, graph_state, response_text)

    log.info("interview_phase_detected", phase=current_phase)

    # Get phase weights from config
    phase_weights = None
    if config.phases and current_phase in config.phases:
        phase_weights = config.phases[current_phase].signal_weights

    # Pass phase weights to scoring
    ranked = rank_strategy_node_pairs(
        strategies,
        global_signals,
        node_signals,
        node_tracker,
        phase_weights=phase_weights,  # NEW
    )
```

### Task 7: Add Unit Tests

**File:** `tests/methodologies/signals/test_meta_signals.py` (new)

**Test cases:**
- Test node opportunity signal with various node states
- Test interview phase detection with different graph states
- Test phase weight application in scoring
- Test empty/small/large graphs for phase detection

### Task 8: Add Integration Tests

**File:** `tests/integration/test_phase_based_scoring.py` (new)

**Test cases:**
- Test phase transitions (early → mid → late)
- Test phase weights modify strategy selection
- Test end-to-end with phase-based config
- Test phase detection with real graph states

## Success Criteria

- [ ] Node opportunity meta signal implemented
- [ ] Interview phase detection signal implemented
- [ ] YAML configs updated with phase sections
- [ ] MethodologyConfig schema updated
- [ ] Phase weights applied in scoring
- [ ] Pipeline integration complete
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] No ruff linting errors
- [ ] No pyright type errors

## Dependencies

- Phase 1: NodeStateTracker ✅
- Phase 2: Node-Level Signals ✅
- Phase 3: Joint Strategy-Node Scoring ✅

## Signal Dependency Graph

```
meta.node.opportunity
├── depends on: graph.node.exhausted
│   └── reads: NodeStateTracker
├── depends on: graph.node.focus_streak
│   └── reads: NodeStateTracker
└── depends on: llm.response_depth
    └── reads: current response

meta.interview.phase
├── reads: graph_state.node_count
├── reads: graph_state.max_depth
└── reads: graph_state.orphan_count
```

## Data Flow (Updated for Phases)

```
User Response (Turn N)
    ↓
1. Extraction → Graph update
    ↓
2. NodeStateTracker updates
    ↓
3. Detect global signals
    ↓
4. Detect node-level signals
    ↓
5. Detect meta signals
    ├─ meta.node.opportunity (for each node)
    └─ meta.interview.phase (global)
    ↓
6. Get phase weights from YAML config
    ↓
7. Score (strategy, node) pairs with phase weights
    ↓
8. Select best pair
    ↓
9. Generate question
```

## Next Phase

After Phase 4 completion, Phase 5 will implement global response tracking signals (llm.global_response_trend, llm.hedging_language) and validation strategy triggers.
