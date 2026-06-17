# Interview Saturation Signals — Design Document

**Date:** 2026-02-18
**Epic:** h0vk
**Status:** Approved

## Overview

Replace the broken `meta.interview_progress` signal with two methodology-agnostic saturation signals based on **information velocity** — a quantitative measure of theoretical saturation from qualitative research methodology.

## Problem Statement

The current `meta.interview_progress` signal has critical flaws:

1. **Plateaus at 0.10** due to double-normalization bug (orbj)
2. **MEC-specific** — chain_completion is meaningless for JTBD methodology
3. **Structural not semantic** — graph depth doesn't reflect information flow
4. **Unaligned with practice** — interviewers use pace, not structural completeness

## Solution: Information Velocity

**Core concept:** When new turns stop producing new concepts, the interview has reached saturation. This is "theoretical saturation" from qualitative research, operationalized as EWMA of new-node-per-turn rate.

### Formula

```
velocity_decay = 1 - (ewma / max(peak, 1.0))
edge_density_norm = min(edge_count / node_count / 2.0, 1.0)
turn_floor = min(turn_number / 15.0, 1.0)
saturation = 0.60 × velocity_decay + 0.25 × edge_density_norm + 0.15 × turn_floor
```

**Component weights:**
- 60% velocity decay (primary indicator)
- 25% edge density (graph richness)
- 15% turn floor (minimum duration)

### Two Parallel Signals

| Signal | Graph Type | Purpose |
|--------|-----------|---------|
| `meta.conversation.saturation` | Surface (conversational) | Primary saturation metric |
| `meta.canonical.saturation` | Canonical (deduplicated) | Experimental comparison |

Hypothesis: Conversational graph may produce better results, but this needs empirical validation.

## Architecture

```
SessionState (DB)                          Pipeline Context
┌─────────────────────────────────────┐    ┌─────────────────────────────┐
│ surface_velocity_ewma: float         │    │ ContextLoadingOutput        │
│ surface_velocity_peak: float         │────┤ • surface_velocity_ewma     │
│ prev_surface_node_count: int         │    │ • surface_velocity_peak     │
│ canonical_velocity_ewma: float       │    │ • prev_surface_node_count   │
│ canonical_velocity_peak: float       │    │ • canonical_velocity_ewma   │
│ prev_canonical_node_count: int       │    │ • canonical_velocity_peak   │
└─────────────────────────────────────┘    │ • prev_canonical_node_count │
       ▲                                    └─────────────────────────────┘
       │                                                 │
       │ ScoringPersistenceStage                        │
       │ (compute & persist)                            │
       │                                                 │
       │                                           ┌────▼────┐
       │                                           │ Signals │
       │                                           │         │
       │                                    ┌──────┴─────┬──────┐
       │                                    │            │      │
       └─────────────────────────────────────┤            │      │
            Velocity decay → EWMA formula   │            │      │
                                             ▼            ▼      ▼
                                    meta.conversation.  meta.    validate_
                                    saturation           canonical outcome
                                                         saturation  weights
```

## Implementation Steps

### Step 1: Data Model (8b5n)

**Files:**
- `src/domain/models/session.py` — SessionState class
- `src/domain/models/pipeline_contracts.py` — ContextLoadingOutput class
- `src/services/turn_pipeline/stages/context_loading_stage.py` — ContextLoadingStage

**Changes:**
1. Add 6 velocity fields to SessionState (DB persistence)
2. Add matching fields to ContextLoadingOutput (pipeline access)
3. Update ContextLoadingStage to map SessionState → ContextLoadingOutput

**Fields:**
```python
# Surface graph
surface_velocity_ewma: float = Field(default=0.0)
surface_velocity_peak: float = Field(default=0.0)
prev_surface_node_count: int = Field(default=0)

# Canonical graph
canonical_velocity_ewma: float = Field(default=0.0)
canonical_velocity_peak: float = Field(default=0.0)
prev_canonical_node_count: int = Field(default=0)
```

### Step 2: Velocity Computation (nig9)

**File:** `src/services/turn_pipeline/stages/scoring_persistence_stage.py`

**Method:** `_update_turn_count()`

**Logic:**
```python
alpha = 0.4  # EWMA smoothing factor (hardcoded)

# Surface graph velocity
current_surface = context.graph_state.node_count
prev_surface = context.context_loading_output.prev_surface_node_count
surface_delta = max(current_surface - prev_surface, 0)
new_surface_ewma = alpha * surface_delta + (1 - alpha) * old_ewma
new_surface_peak = max(old_peak, float(surface_delta))

# Canonical graph velocity (may be None)
cg_state = context.canonical_graph_state
current_canonical = cg_state.concept_count if cg_state else 0
# ... similar EWMA computation
```

**Bug fix:** Also preserve `last_strategy` and `mode` fields that are currently lost.

### Step 3: Signal Detection (f1ej, agax)

**Files:**
- `src/signals/meta/conversation_saturation.py`
- `src/signals/meta/canonical_saturation.py`

**Pattern:** Both follow same structure, read from `context.context_loading_output`

**Edge case:** `CanonicalSaturationSignal` returns empty dict if `canonical_graph_state` is None (feature disabled).

### Step 4: Registration (3p9w)

**Auto-registration:** Signals auto-register via `__init_subclass__` — no manual registry changes needed.

**YAML updates:**
- `config/methodologies/jobs_to_be_done.yaml` — Add to `signals.meta`
- `config/methodologies/means_end_chain.yaml` — Add to `signals.meta`
- `config/methodologies/critical_incident.yaml` — Add if exists

### Step 5: Integration (ewxf)

**Files:**
- `config/methodologies/*.yaml` — Add weights to `validate_outcome`
- `src/signals/meta/progress.py` — Add deprecation notice

**Weights:**
```yaml
validate_outcome:
  signal_weights:
    meta.conversation.saturation: 0.5
    meta.canonical.saturation: 0.3
```

**Deprecation:**
- Keep `progress.py` for MEC (chain_completion is valid there)
- Add docstring: "DEPRECATED for JTBD: replaced by saturation signals"

## Edge Cases

| Case | Handling |
|------|----------|
| peak = 0 | Use `max(peak, 1.0)` to avoid division by zero |
| canonical_slots disabled | `CanonicalSaturationSignal` returns empty dict |
| First turn | Defaults (0.0) yield saturation=0.15 (turn floor only) |
| Negative delta | `max(delta, 0)` — velocity never decreases |

## Testing Strategy

**Unit tests:**
- EWMA computation with edge cases (peak=0, negative delta)
- Saturation formula components (velocity_decay, edge_density_norm, turn_floor)
- Signal detection with mock context

**No integration tests specified** — relying on simulation-based validation later.

## Configuration

**EWMA alpha:** Hardcoded to 0.4 (not configurable)

**Rationale:** Matches theoretical saturation research design; simpler than adding configuration surface.

## Backward Compatibility

**Database:** New fields have default values (0.0/0). Existing sessions will initialize to defaults on first load, then compute correctly.

**API:** No breaking changes. Signals are additions, not replacements.

## Success Criteria

1. Signals compute correctly for new sessions
2. Existing sessions work with default initialization
3. `validate_outcome` strategy uses saturation scores
4. `meta.interview_progress` fully deprecated for JTBD

## References

- Bead 8b5n: Data model changes
- Bead nig9: Velocity computation
- Bead f1ej: Conversation saturation signal
- Bead agax: Canonical saturation signal
- Bead 3p9w: Signal registration
- Bead ewxf: Integration and deprecation
- Bead orbj: Original progress signal bug (to be closed)
