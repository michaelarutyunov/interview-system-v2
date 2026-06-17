# Design: Replace Saturation Signals with Meaningful Metrics

**Date:** 2026-02-27
**Status:** Approved

## Problem

Both `meta.conversation.saturation` and `meta.canonical.saturation` use the same formula that produces an "interview progress indicator" rather than actual saturation detection. The formula combines velocity decay (relative to peak), edge density (graph maturity), and a turn floor (monotonic clock) — all three increase monotonically over time regardless of whether information exhaustion has occurred.

Run 15 (CJM × single_topic_fixator) demonstrated the failure: canonical saturation only reached 0.20 by turn 10 despite 64 surface nodes collapsing into 10 canonical slots (6.4:1 compression). The signal was too slow and too smooth to trigger any strategy suppression.

## Design

### Signal 1: `meta.canonical.saturation` — Canonical Novelty Ratio

Measures what fraction of this turn's extraction was thematically redundant at the canonical level.

```python
new_canonical = canonical_concept_count - prev_canonical_node_count
new_surface = surface_node_count - prev_surface_node_count

if new_surface > 0:
    novelty_ratio = new_canonical / new_surface
else:
    novelty_ratio = 1.0  # no extraction = not saturated

saturation = 1.0 - novelty_ratio  # high = saturated
```

- Output: 0.0 (all new themes) to 1.0 (pure deduplication)
- Instantaneous per-turn, no smoothing

### Signal 2: `meta.conversation.saturation` — Extraction Yield Ratio

Measures how much extractable content the respondent is producing compared to their best turn.

```python
new_surface = surface_node_count - prev_surface_node_count
peak = surface_velocity_peak  # already tracked in SessionState

if peak > 0:
    yield_ratio = new_surface / peak
else:
    yield_ratio = 1.0

saturation = 1.0 - min(yield_ratio, 1.0)  # high = saturated
```

- Reuses existing `surface_velocity_peak` field
- Output: 0.0 (matching peak extraction) to 1.0 (zero extraction)

### YAML Weight Changes

Add negative suppression on mid-phase deepening strategies:

| Methodology | Strategy | `meta.canonical.saturation` | `meta.conversation.saturation` |
|---|---|---|---|
| CJM | `compare_expectations` | `.high: -0.6` | `.high: -0.4` |
| MEC | `deepen` | `.high: -0.5` | `.high: -0.4` |
| CIT | `probe_attributions` | `.high: -0.5` | `.high: -0.4` |
| RG | `ladder_constructs` | `.high: -0.5` | `.high: -0.4` |
| JTBD | `dig_motivation` | `.high: -0.5` | `.high: -0.4` |

Reduce existing late-phase positive weights from 0.3-0.5 to 0.2-0.3 (new formulas produce stronger values).

### Fields to Remove

- `canonical_velocity_ewma` / `surface_velocity_ewma` — no longer consumed
- EWMA computation in `scoring_persistence_stage.py`

### Unchanged

- Signal names, registration, pipeline wiring
- SessionState fields: `prev_*_node_count`, `surface_velocity_peak`, `canonical_velocity_peak`
