# MEC and CIT Methodology Redesign

Date: 2026-02-22

## Context

The interview system had functional but underdeveloped MEC and CIT methodology configs. Both used generic strategies with minimal signal weights and lacked methodology-specific interviewing techniques. JTBD (7 strategies, 3 phases, 20+ signal weights per strategy) served as the reference for what a well-tuned methodology looks like.

## Decision

Rewrote both MEC and CIT YAML configs with methodology-specific strategies, comprehensive signal weights, and proper phase configurations. No code changes required — the system's separation of mechanism (code) and domain (YAML) means new strategies are pure configuration.

## MEC Redesign (v3.0 → v4.0)

### Strategies: 5 → 7

| Old | New | Change |
|-----|-----|--------|
| deepen | ladder_up | Renamed, refocused on chain completion as primary signal |
| clarify | clarify | Retained, same purpose |
| explore | elicit_attribute | Renamed, focused on concrete product features |
| reflect | validate_chain | Renamed, now reflects back complete chains specifically |
| revitalize | revitalize | Retained |
| — | anchor_down | **NEW**: Pulls back to concrete when respondent is too abstract |
| — | bridge_chains | **NEW**: Connects separate ladders |

### Key Signal Changes
- Added `llm.intellectual_engagement` to signal pool
- `graph.chain_completion.has_complete.false` is strongest signal on `ladder_up` (1.0)
- `llm.specificity.low` triggers `anchor_down` (0.9) — inverted from JTBD
- Dropped `meta.interview_progress` from signal pool (redundant with chain_completion)
- Phase boundaries: early=4, mid=14 (adaptive termination via saturation)

## CIT Redesign (v2.0 → v3.0)

### Strategies: 6 → 9

| Old | New | Change |
|-----|-----|--------|
| explore_incident | elicit_incident | Refined description, proper signal weights |
| explore_outcomes | probe_outcomes | Refined |
| explore_emotions | explore_emotion | Dual polarity valence triggering (high AND low) |
| explore_attributions | seek_attribution | intellectual_engagement as primary driver |
| explore_learnings | extract_learning | Depth + IE as triggers |
| explore_behavior_change | (merged into extract_learning/validate_pattern) | — |
| — | situate_incident | **NEW**: Grounds story in concrete context |
| — | trace_actions | **NEW**: Walks through behavioral sequence |
| — | elicit_contrast | **NEW**: Multi-incident pivot for contrasting experiences |
| — | validate_pattern | **NEW**: Cross-incident pattern synthesis |

### Key Signal Changes
- Added `llm.intellectual_engagement` to signal pool
- Dual polarity on `llm.valence` for `explore_emotion` (both high: 0.7 and low: 0.7)
- Inverted exhaustion on `elicit_contrast` (exhausted nodes = positive trigger)
- `yield_stagnation.true` triggers incident pivot
- Phase boundaries: early=4, mid=14
- No `graph.chain_completion` (CIT uses forest structure, not chains)

## Consequences

- Both configs pass validation (all signal weight keys valid, all phase refs valid)
- MEC interviews will be more structured (ladder_up → anchor_down oscillation)
- CIT interviews will produce multi-incident data with cross-incident patterns
- Both use adaptive termination (saturation-based, not fixed turn count)
- Simulation testing needed to verify strategy firing patterns

## Alternatives Considered

- **Repertory Grid**: Rejected — requires matrix data structure the graph doesn't support
- **Customer Journey Mapping**: Deferred — needs temporal ordering between nodes
