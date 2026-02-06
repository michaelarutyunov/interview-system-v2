# ADR-016: Pure Node-Count Phase Detection

## Status

Accepted 2026-02-04

## Context

The interview system uses a three-phase progression (early, mid, late) to adjust strategy selection weights and bonuses. Phase transitions are critical for ensuring appropriate strategy variety throughout the interview.

## Problem

The original phase detection logic in `InterviewPhaseSignal._determine_phase()` included an `orphan_count > 3` condition that kept the interview in "mid" phase indefinitely:

```python
def _determine_phase(self, node_count, orphan_count, early_max_nodes, mid_max_nodes):
    if node_count < early_max_nodes:
        return "early"
    elif node_count < mid_max_nodes or orphan_count > 3:  # BUG
        return "mid"
    else:
        return "late"
```

**Impact:**
- Interviews with high orphan counts (common in exploratory research) never transitioned to "late" phase
- Late-phase strategies like `reflect` never received their intended weight boosts
- Strategy variety was severely limited in longer interviews

## Decision

Remove the `orphan_count > 3` condition and use pure node_count-based thresholds:

```python
def _determine_phase(self, node_count, orphan_count, early_max_nodes, mid_max_nodes):
    if node_count < early_max_nodes:
        return "early"
    elif node_count < mid_max_nodes:
        return "mid"
    else:
        return "late"
```

Add a comment documenting that orphan_count-based extensions are possible if needed for future use cases.

## Consequences

### Positive

1. **Predictable phase transitions** - Phases now transition purely based on node_count thresholds
2. **Late-phase strategies activated** - `reflect` and `revitalize` now receive appropriate weight boosts
3. **Improved strategy variety** - Interviews now progress through all three phases with appropriate strategy selection

### Negative

1. **Less tolerant of sparse graphs** - Interviews with high orphan counts will transition to late phase earlier
2. **May over-trigger late phase** - If graph building is slow, late phase may activate before adequate depth is achieved

### Mitigations

- Phase boundaries are configurable per methodology in YAML
- `MIN_TURN_FOR_SATURATION` (5 turns) in ContinuationStage prevents premature saturation checks
- If needed, the orphan_count condition can be re-added with a comment explaining its purpose

## Related

- [Interview Phase Signal Implementation](../../src/methodologies/signals/meta/interview_phase.py)
- [Phase-Based Strategy Selection](../../config/methodologies/means_end_chain.yaml)
- [ADR-014: Signal Pools Architecture](./ADR-014-signal-pools-architecture.md)

## History

- 2026-02-04: Initial decision to remove orphan_count clause
- 2026-02-04: Accepted
