# Methodology Optimization Report

**Dataset**: 41 simulated interviews across 9 personas and 2 concepts (meal_planning_jtbd_v2, coffee_jtbd_v2)
**Methodology**: jobs_to_be_done_v2
**Extracted**: 502 turns, 150,725 scoring rows

---

## 1. Executive Summary

The JTBD v2 methodology produces rich knowledge graphs (mean 62.5 nodes, 88.5 edges) but suffers from **low strategy diversity** (mean 0.38), **14 dormant signals**, and a **dominant dig_motivation/revitalize duopoly** that accounts for 49% of all strategy selections. Phase multipliers are working as designed for phase transitions, but mid-phase scoring is too concentrated. Brief responder interviews expose a quality control weakness: `revitalize` is selected 109 times for this persona alone, suggesting the strategy fires as a generic fallback rather than a targeted intervention.

### Top 5 Actionable Findings

| # | Finding | Impact | Effort |
|---|---------|--------|--------|
| 1 | 5 signals have 0% activity rate — dead YAML config | Prune or fix thresholds | Low |
| 2 | `revitalize` dominates brief_responder (56% of turns) | Fix signal gating or add engagement floor | Medium |
| 3 | `dig_motivation` runs 4-6 turns consecutively in mid-phase | Increase repetition penalty weight | Low |
| 4 | Score margins are very tight for single_topic_fixator (median 0.104) | Selection is near-random; needs stronger differentiation | Medium |
| 5 | `response_depth` signal is always NaN in trajectory data | Extraction or normalization bug | Medium |

---

## 2. Signal Effectiveness Audit

### 2.1 Completely Dormant Signals (0% activity)

These signals have weights configured in the YAML but **never produce a nonzero contribution**:

| Signal | Likely Cause |
|--------|-------------|
| `graph.node.canonical_novelty.confirming` | Threshold too high or condition never met |
| `graph.node.focus_count.high` | No node reaches "high" focus count threshold |
| `graph.node.focus_count.medium` | Same — only `.none` fires (93.4% activity) |
| `graph.node.focus_streak.high` | Streak resets before reaching "high" |
| `meta.node.opportunity.probe_deeper` | Condition never triggered |

**Recommendation**: Either lower the thresholds that gate these signals or remove them from YAML to reduce scoring noise. The `focus_count` family only fires at `.none` level — the medium/high tiers are unreachable.

### 2.2 Near-Dormant Signals (<10% activity)

| Signal | Activity Rate | Notes |
|--------|--------------|-------|
| `graph.node.is_orphan.true` | 0.09% | Dedup prevents orphans effectively |
| `graph.node.focus_streak.medium` | 0.62% | Streak mechanics may need tuning |
| `graph.node.focus_streak.low` | 1.01% | Same issue |
| `llm.response_depth.surface` | 3.10% | Only brief_responder triggers this |
| `llm.engagement.mid` | 3.77% | LLM tends to score high or low, not mid |
| `temporal.strategy_repetition_count.high` | 5.49% | Repetition threshold too high |
| `technique.node.strategy_repetition.low` | 6.98% | Rarely reached |
| `meta.conversation.saturation.high` | 7.81% | Saturation takes many turns to hit |
| `llm.global_response_trend.shallowing` | 8.24% | Fires more often as `.fatigued` (22%) |

### 2.3 Highest-Impact Signals

These contribute most to scoring decisions (by mean absolute contribution when active):

| Signal | Mean Contribution | Count | Role |
|--------|------------------|-------|------|
| `meta.interview.phase.early` | -3.00 | 161 | Phase gate (blocks strategies) |
| `meta.interview.phase.mid` | -3.00 | 264 | Phase gate (blocks strategies) |
| `temporal.strategy_repetition_count.high` | -1.00 | 177 | Repetition penalty |
| `llm.certainty.low` | +1.00 | 143 | Strongest positive signal |
| `llm.valence.low` | +0.70 | 388 | Strong engagement indicator |
| `graph.node.is_orphan.true` | +0.66 | 5 | High weight but almost never fires |
| `llm.intellectual_engagement.high` | +0.60 | 216 | Core quality signal |

**Observation**: Phase gates dominate scoring with -3.0 contributions. While effective at enforcing phase transitions, they make all other signals near-irrelevant in early/late phases. Consider whether a -3.0 gate is too blunt — a -1.5 would still block but allow some signal sensitivity.

---

## 3. Strategy Selection Analysis

### 3.1 Overall Strategy Distribution

| Strategy | Count | % | Primary Phase |
|----------|-------|---|---------------|
| `dig_motivation` | 114 | 24.7% | mid (98 of 114) |
| `revitalize` | 113 | 24.5% | mid (63) + early (49) |
| `uncover_obstacles` | 71 | 15.4% | mid (64 of 71) |
| `explore_situation` | 67 | 14.5% | early (52 of 67) |
| `probe_alternatives` | 45 | 9.8% | early (25) + mid (20) |
| `validate_outcome` | 35 | 7.6% | late (35 of 35) — closing only |
| `clarify_assumption` | 16 | 3.5% | early (12 of 16) |

**Key concern**: `dig_motivation` + `revitalize` = 49.2% of all selections. The methodology has 7 strategies but effectively uses 2-3 in any given interview.

### 3.2 Strategy Distribution by Persona

| Persona | Top Strategy | % of Turns | Unique Strategies | Diversity |
|---------|-------------|-----------|-------------------|-----------|
| baseline_cooperative | dig_motivation | 38.3% | 5.0 avg | 0.42 |
| brief_responder | revitalize | 55.9% | 4.1 avg | 0.30 |
| emotionally_reactive | dig_motivation | 52.6% | 4.0 avg | 0.42 |
| fatiguing_responder | dig_motivation | 42.1% | 4.5 avg | 0.45 |
| retrospective_rationalizer | dig_motivation | 53.1% | 3.7 avg | 0.35 |
| single_topic_fixator | dig_motivation | 48.9% | 3.7 avg | 0.33 |
| skeptical_analyst | dig_motivation | 38.1% | 5.0 avg | 0.53 |
| uncertain_hedger | dig_motivation | 42.1% | 4.5 avg | 0.50 |
| verbose_tangential | probe_alternatives | 36.8% | 4.0 avg | 0.42 |

**Problem**: `brief_responder` triggers `revitalize` 109 out of 195 turns. This persona gives short answers, which causes low engagement/depth signals, which triggers `revitalize` as a rescue strategy. But revitalize doesn't help because the persona *always* gives brief answers — it's a trait, not a state. The system enters a `revitalize` loop.

**Recommendation**: Add a `revitalize` cooldown or cap — if `revitalize` was selected in the last 2 turns and engagement hasn't improved, force a different strategy.

### 3.3 Phase Multiplier Effects

| Phase | Boosted Strategies | Suppressed Strategies |
|-------|-------------------|----------------------|
| Early | `explore_situation` (1.5x + 0.2 bonus), `probe_alternatives` (1.2x + 0.15) | `dig_motivation` (0.5x), `uncover_obstacles` (0.3x), `validate_outcome` (0.2x) |
| Mid | `clarify_assumption` (1.3x + 0.15), `dig_motivation` (1.2x + 0.15), `uncover_obstacles` (1.3x + 0.25) | `explore_situation` (0.6x), `validate_outcome` (0.5x) |
| Late | `validate_outcome` (1.5x + 0.2), `uncover_obstacles` (1.2x) | `dig_motivation` (0.5x), `explore_situation` (0.3x) |

Phase gates are working correctly: early pushes exploration, mid pushes depth, late pushes closure. The mean final scores confirm this alignment.

### 3.4 Score Margin Analysis (Decision Confidence)

| Persona | Median Margin | Min | Interpretation |
|---------|--------------|-----|----------------|
| single_topic_fixator | 0.104 | 0.036 | Near-coin-flip selections |
| skeptical_analyst | 0.162 | 0.018 | Often ambiguous |
| uncertain_hedger | 0.216 | 0.025 | Moderate confidence |
| baseline_cooperative | 0.282 | 0.008 | Moderate |
| emotionally_reactive | 0.334 | 0.038 | Reasonable |
| verbose_tangential | 0.156 | 0.000 | Contains a 0.000 tie |
| fatiguing_responder | 0.684 | 0.050 | Clear decisions |
| brief_responder | 0.510 | 0.004 | High but driven by `revitalize` dominance |
| retrospective_rationalizer | 0.407 | 0.018 | Moderate |

**Concern**: `single_topic_fixator` median margin of 0.104 means strategy selection is near-random. This persona should trigger strong exhaustion signals that clearly differentiate strategies — but the dormant `focus_count.high/medium` and `focus_streak.high` signals prevent this.

### 3.5 Strategy Repetition Patterns

Sample sequences show `dig_motivation` running 4-6 consecutive turns in mid-phase:

```
Interview 51d2d4c7: dig×4 → obstacles → dig → obstacles → dig → obstacles×3 → validate
Interview 9c4dc3a3: dig×3 → obstacles → clarify → dig → obstacles → dig×2 → obstacles → dig → validate
```

The repetition penalty (`temporal.strategy_repetition_count`, weight -0.7) reduces score but doesn't overcome `dig_motivation`'s base advantage in mid-phase (1.2x multiplier + 0.15 bonus). The penalty would need to be stronger (-1.2 to -1.5) or the `repetition_count.high` threshold lowered to actually break these runs.

---

## 4. Knowledge Graph Outcomes

### 4.1 Graph Richness by Persona

| Persona | Nodes/Turn | Edges/Turn | Edge/Node Ratio | Canonical Slots |
|---------|-----------|-----------|----------------|----------------|
| verbose_tangential | 9.0 | 11.0 | 1.23 | 8.0 |
| single_topic_fixator | 8.1 | 10.7 | 1.33 | 13.8 |
| skeptical_analyst | 8.2 | 11.3 | 1.38 | 10.0 |
| emotionally_reactive | 7.9 | 10.8 | 1.34 | 12.0 |
| retrospective_rationalizer | 7.5 | 10.9 | 1.48 | 9.7 |
| uncertain_hedger | 7.3 | 9.9 | 1.35 | 10.0 |
| baseline_cooperative | 6.8 | 9.8 | 1.44 | 12.1 |
| fatiguing_responder | 5.4 | 8.5 | 1.53 | 9.0 |
| brief_responder | 2.1 | 3.8 | 1.76 | 4.2 |

**Notable**: `brief_responder` yields only 2.1 nodes/turn (vs 6.8 for baseline) but has the highest edge/node ratio (1.76). The system extracts *fewer* nodes but connects them more densely. This is actually reasonable behavior — brief answers contain fewer concepts but the ones extracted are well-connected.

### 4.2 Node Type Distribution (Mean across all interviews)

| Type | Mean Count | % of Graph |
|------|-----------|-----------|
| pain_point | 21.7 | 34.7% |
| gain_point | 9.9 | 15.8% |
| solution_approach | 9.8 | 15.7% |
| emotional_job | 8.6 | 13.7% |
| job_context | 4.9 | 7.8% |
| job_statement | 4.6 | 7.4% |
| job_trigger | 3.7 | 5.9% |
| social_job | 1.7 | 2.8% |

**Observation**: `pain_point` dominates at 35% of nodes. This may reflect the methodology's bias toward `dig_motivation` and `uncover_obstacles` (which elicit pain points). If social jobs or job triggers are important for JTBD analysis, strategies that specifically probe for these types could be added or weighted.

### 4.3 Termination

| Reason | Count | % |
|--------|-------|---|
| Closing strategy selected | 35 | 85.4% |
| quality_degraded | 6 | 14.6% |

All 6 `quality_degraded` terminations are `brief_responder` interviews. The system correctly detects quality degradation but only after many turns of `revitalize` cycling. Earlier detection (e.g., after 3 consecutive low-engagement turns) would save LLM costs.

---

## 5. Signal Trajectory Analysis

### 5.1 Engagement by Persona Over Time

| Persona | Turn 1 | Turn 7 | Turn 14 | Trend |
|---------|--------|--------|---------|-------|
| baseline_cooperative | 0.69 | 0.75 | 0.50 | Stable then dips |
| brief_responder | 0.28 | 0.12 | 0.11 | Low throughout |
| emotionally_reactive | 0.75 | 0.75 | 0.75 | Flat high |
| fatiguing_responder | 0.75 | 0.50 | 0.75 | V-shaped |
| single_topic_fixator | 0.75 | 0.75 | 1.00 | Rising |
| skeptical_analyst | 0.75 | 1.00 | 1.00 | Rising |

**`response_depth` is NaN across all personas and all turns.** This is a data extraction or normalization bug — the signal exists in scoring decomposition rows but doesn't appear in the `signals` dict at turn level. This should be investigated as `response_depth` has weights in 4 strategies.

### 5.2 Conversation Saturation

Saturation hovers between 0.2-0.6 for most personas, rarely triggering `meta.conversation.saturation.high` (7.8% activity). The system terminates via closing strategy before saturation takes effect. This means saturation-based signals are not contributing to the decision to close — the phase boundary + `validate_outcome` multiplier drives closure independently.

---

## 6. Recommended YAML Changes

### 6.1 Immediate (Low Effort)

```yaml
# 1. Remove or lower thresholds for dormant focus signals
# Currently these never fire — remove from signal_weights to reduce scoring noise
# REMOVE from all strategies:
#   graph.node.focus_count.high
#   graph.node.focus_count.medium
#   graph.node.focus_streak.high
#   meta.node.opportunity.probe_deeper
#   graph.node.canonical_novelty.confirming

# 2. Increase repetition penalty
# Current: temporal.strategy_repetition_count: -0.7
# Proposed: -1.2 (enough to overcome dig_motivation's mid-phase advantage)
strategies:
  dig_motivation:
    signal_weights:
      temporal.strategy_repetition_count: -1.2  # was -0.7
  uncover_obstacles:
    signal_weights:
      temporal.strategy_repetition_count: -1.2  # was -0.7

# 3. Lower repetition_count.high threshold
# Current fires at 5.5% — lower threshold so it kicks in after 2 consecutive uses
```

### 6.2 Medium Effort

1. **Revitalize gating for brief_responder pattern**: Add a signal that detects "persistent low engagement without improvement" and suppresses `revitalize` after 2+ consecutive uses without engagement recovery.

2. **Fix response_depth signal**: It's present in scoring rows but absent from turn-level signals. Trace the extraction path to find where it's dropped.

3. **Tune single_topic_fixator differentiation**: Enable the dormant exhaustion signals (`focus_count.medium/high`, `focus_streak.high`) by lowering thresholds, so this persona type actually triggers the rotation mechanics it was designed to test.

### 6.3 Longer Term

1. **Node-type-aware strategies**: Add strategies that specifically target underrepresented node types (`social_job` at 2.8%, `job_trigger` at 5.9%) to produce more balanced JTBD graphs.

2. **Phase gate softening**: Replace -3.0 hard gates with -1.5 soft gates, allowing some signal sensitivity within phase transitions.

3. **Earlier quality termination**: Detect 3 consecutive low-engagement turns and trigger early closure rather than cycling through `revitalize`.

---

## 7. Data Files

All source data is available in `analysis/simulation_extract/`:

| File | Rows | Description |
|------|------|-------------|
| `turns.parquet` | 502 | Per-turn signals, strategies, graph growth |
| `scoring.parquet` | 150,725 | Per-signal scoring decomposition |
| `interviews.parquet` | 41 | Terminal graph stats, strategy diversity |

Load with:
```python
import pandas as pd
df = pd.read_parquet("analysis/simulation_extract/turns.parquet")
```

---

*Generated from 41 simulation outputs in `synthetic_interviews/v2/`*
