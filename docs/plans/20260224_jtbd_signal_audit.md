# Cross-Persona Signal Pool Audit — JTBD Scoring Analysis

**Date**: 2026-02-24
**Methodology**: Jobs-to-be-Done (config/methodologies/jobs_to_be_done.yaml)
**Input Runs**:
- `synthetic_interviews/20260224_155914_coffee_jtbd_v2_skeptical_analyst.json` (15 turns)
- `synthetic_interviews/20260224_165801_coffee_jtbd_v2_social_conscious.json` (15 turns)

**Known Issues** (not addressed in this audit):
1. Phase detection broken — `meta.interview.phase` missing from all turns; all CSV rows show phase=unknown
2. `graph.node.slot_saturation` was dead in skeptical_analyst run (fixed between runs)
3. `llm.valence.mid` never fires — valence quantizes to 0.25 or 0.75 only

---

## Executive Summary

| Issue | Severity | Impact |
|-------|----------|--------|
| dig_motivation dominance (44-57% selection) | High | Interview monotony, reduced coverage |
| validate_outcome never selected in social_conscious run | High | Missing wrap-up strategy |
| Top nodes remain "fresh" until turns 10-12 | Medium | Weak rotation despite exhaustion signals |
| Multiple unused LLM signals | Low | Wasted computation |

---

## 1. Signal Pool Audit

### 1.1 Universal Dead Signals (Both Personas)

The following signals have **fired_pct = 0** for both personas. These are candidates for removal or zero-weighting:

| Signal | Registered | Current Usage | Recommendation |
|--------|-----------|---------------|----------------|
| `llm.engagement.low` | Yes | -0.5 (dig_motivation) | **Keep** — safety gate, may fire in other contexts |
| `llm.engagement.mid` | Yes | 0.3-0.5 across strategies | **Keep** — moderate engagement signal, calibration issue |
| `llm.global_response_trend.fatigued` | Yes | 1.0 (revitalize) | **Keep** — fatigue trigger, persona-specific |
| `graph.node.focus_streak.high` | Yes | -0.7 to -0.8 | **Investigate** — never fires despite 9+ turn focus |
| `llm.certainty.low` | Yes | 1.0 (validate_outcome) | **Investigate** — uncertainty gate not triggering |
| `llm.response_depth.shallow` | Yes | 0.2 (probe_alternatives) | **Remove or zero** — quantizes to surface/moderate/deep only |
| `llm.response_depth.surface` | Yes | 0.5 (dig_motivation) | **Remove or zero** — same as shallow |

**Key Finding**: `graph.node.focus_streak.high` never fires despite nodes being selected for 9+ consecutive turns. The signal threshold may be set too high or the discretization logic is broken.

### 1.2 Persona-Specific Signals

| Signal | Skeptical | Social | Diff | Notes |
|--------|-----------|--------|------|-------|
| `llm.specificity.high` | 87.2% | 19.4% | +67.8% | Skeptical persona makes specific claims |
| `graph.node.slot_saturation` | 0%* | 86.5% | -86.5% | Broken in skeptic run (fixed between runs) |
| `llm.valence.high` | 0% | 60.9% | -60.9% | Social persona more positive |
| `llm.valence.mid` | 36.6% | 0% | +36.6% | Never fires due to quantization |
| `graph.node.slot_saturation.low` | 73.2% | 17.0% | +56.1% | Placeholder format, no contribution |

\* Excluding skeptical_analyst run due to known bug

### 1.3 Signals to Remove or Zero-Weight

| Signal | Reason | Action |
|--------|--------|--------|
| `llm.response_depth.shallow` | Never fires (quantizes to surface/moderate/deep) | Remove from all strategies |
| `llm.response_depth.surface` | Same as shallow, redundant | Remove from all strategies |
| `llm.valence.mid` | Quantization makes 0.26-0.74 unreachable | Zero-weight or remove |
| `graph.node.slot_saturation.low` | Placeholder format, weighted_contribution always 0 | Remove (keep continuous `graph.node.slot_saturation`) |

---

## 2. Strategy Diversity Analysis

### 2.1 Current Selection Distribution

| Strategy | Skeptical | Social | Avg |
|----------|-----------|--------|-----|
| `dig_motivation` | 44.4% | 57.3% | **50.9%** |
| `explore_situation` | 18.7% | 24.4% | 21.6% |
| `uncover_obstacles` | 31.1% | 12.2% | 21.7% |
| `validate_outcome` | 5.8% | 0% | 2.9% |
| `clarify_assumption` | 0% | 6.1% | 3.1% |
| `revitalize` | 0% | 0% | 0% |

**Issue**: `dig_motivation` exceeds the 50% monotony threshold in both runs.

### 2.2 Repetition Penalty Growth

The `temporal.strategy_repetition_count` penalty is **-0.7 × value**. The value grows by 0.2 per consecutive same-strategy turn:

| Consecutive Turns | Signal Value | Penalty at -0.7 |
|-------------------|--------------|-----------------|
| 1 | 0.0 | 0.00 |
| 2 | 0.2 | -0.14 |
| 3 | 0.4 | -0.28 |
| 4 | 0.6 | -0.42 |
| 5 | 0.8 | -0.56 |

### 2.3 dig_motivation Streak Analysis

**Skeptical Analyst**: Longest streak = 4 turns (turns 4-7)
**Social Conscious**: Longest streak = 4 turns (turns 6-9), then 3 turns (turns 13-15)

At a 4-turn streak, the penalty is only **-0.42**. The average win margin for dig_motivation is **0.23-0.26**, so the penalty isn't enough to displace it.

### 2.4 Recommended Penalty Weight

To break a 4-turn streak, we need the penalty to exceed the win margin:
- Current at 4 turns: -0.42
- Required: ~ -0.5 to -0.6

**Recommendation**: Increase `temporal.strategy_repetition_count` weight from **-0.7 to -1.0 or -1.2**

| Weight | 4-turn penalty | 5-turn penalty |
|--------|----------------|----------------|
| -0.7 | -0.42 | -0.56 |
| -1.0 | -0.60 | -0.80 |
| -1.2 | -0.72 | -0.96 |

**Note**: The `dig_motivation` strategy also has `temporal.strategy_repetition_count.high: -1.0` as a severe penalty at 4-5 reps. However, this discretized key is not being applied.

---

## 3. validate_outcome Coverage

### 3.1 Selection Frequency

| Run | Times Selected | Turns |
|-----|----------------|-------|
| Skeptical | 1 | Turn 15 only |
| Social | 0 | Never |

### 3.2 Score Gap Analysis

**Skeptical Analyst** — validate_outcome gap behind winner:
- Turns 1-11: Gap = 2.0-4.3 points (massive)
- Turn 12: Gap = 0.011 (competitive!)
- Turn 13: Gap = 0.718 (narrowing)
- Turn 14: Gap = 0.568 (narrowing)
- Turn 15: Gap = 0.000 (wins!)

**Social Conscious** — validate_outcome gap behind winner:
- All turns: Gap = 2.4-4.6 points (never competitive)

### 3.3 Root Cause

The `validate_outcome` strategy has:
- Late-phase multiplier: **1.5** with bonus **0.2**
- But phase detection is broken, so it relies on base scores only

With phase detection broken, `validate_outcome` never gets its late-phase boost. In the skeptical run, it only wins at turn 15 when the base score is finally competitive.

### 3.4 Recommendation

**Wait for phase detection fix first.** The issue is primarily the missing `meta.interview.phase` signal, not the YAML weights.

Secondary option: Add a turn-based trigger as a fallback:
```yaml
validate_outcome:
  signal_weights:
    temporal.turn_number.high: 0.5  # Trigger in late turns regardless of phase
```

---

## 4. Node Rotation Assessment

### 4.1 Top Node Selection Dominance

**Skeptical Analyst**:
- Top node (ff1924de...): 85/257 selections (33.1%)
- Second node: 54/257 (21.0%)

**Social Conscious**:
- Top node (5b4d7298...): 57/279 selections (20.4%)
- Second node: 57/279 (20.4%)
- Third node: 54/279 (19.4%)

### 4.2 Exhaustion Timeline

The `graph.node.exhaustion_score.low` signal (True = fresh, False = exhausted):

**Skeptical Top Node**:
- Turns 1-9: FRESH (True)
- Turns 10-15: EXHAUSTED (False)
- **Result**: Node stayed "fresh" for 9 turns despite being selected every turn

**Social Conscious Top Node**:
- Turns 1-11: FRESH (True)
- Turns 12-15: EXHAUSTED (False)
- **Result**: Node stayed "fresh" for 11 turns

### 4.3 Focus Streak Behavior

**Skeptical Top Node**:
- Turns 1-5: `focus_streak.none` → `focus_streak.low` (first focus)
- Turns 6-15: `focus_streak.medium` (2-3 turn over-focus)
- **Issue**: `focus_streak.high` never fires despite 9+ consecutive turns

**Social Conscious Top Node**:
- Turns 1-7: `focus_streak.low` (continuous first focus)
- Turns 8-15: `focus_streak.medium`
- **Issue**: Same — `focus_streak.high` never fires

### 4.4 Issues Found

1. **`focus_streak.high` never fires** — The discretization threshold is likely set too high (probably > 4, but nodes are yielding before reaching it)
2. **Exhaustion threshold is too lenient** — Nodes remain "fresh" until 9-11 turns, allowing excessive focus
3. **Focus streak penalties are insufficient** — At -0.4 for medium streak, the penalty doesn't overcome other boosts

### 4.5 Recommended Changes

| Signal | Current | Proposed | Rationale |
|--------|---------|----------|-----------|
| `graph.node.exhaustion_score.low` | 1.0 (dig_motivation) | **0.5** | Reduce fresh node boost to allow rotation |
| `dig_motivation.graph.node.focus_streak.high` | -0.8 | **Fix threshold** | Currently never fires |
| `dig_motivation.graph.node.focus_streak.medium` | -0.4 | **-0.6** | Increase penalty for 2-3 turn focus |

---

## 5. Proposed YAML Changes

### Priority 1: Fix dig_motivation Dominance

| YAML Path | Current | Proposed | Evidence |
|-----------|---------|----------|----------|
| `strategies[dig_motivation].signal_weights.temporal.strategy_repetition_count` | -0.7 | **-1.0** | 4-turn streak penalty of -0.42 is too weak; avg win margin 0.23-0.26 |
| `strategies[dig_motivation].signal_weights.temporal.strategy_repetition_count.high` | -1.0 | **Fix discretization** | Key not firing at 4-5 reps |

### Priority 2: Fix Node Rotation

| YAML Path | Current | Proposed | Evidence |
|-----------|---------|----------|----------|
| `strategies[dig_motivation].signal_weights.graph.node.exhaustion_score.low` | 1.0 | **0.5** | Top nodes stay "fresh" for 9-11 turns |
| `strategies[dig_motivation].signal_weights.graph.node.focus_streak.medium` | -0.4 | **-0.6** | Medium streak (2-3 turns) needs stronger penalty |
| `strategies[dig_motivation].signal_weights.graph.node.focus_streak.high` | -0.8 | **Fix threshold** | Never fires despite 9+ consecutive selections |

### Priority 3: Remove Dead Weight

| YAML Path | Current | Proposed | Evidence |
|-----------|---------|----------|----------|
| All strategies `llm.response_depth.shallow` | 0.2 | **0.0 (remove)** | Never fires (quantization) |
| All strategies `llm.response_depth.surface` | 0.3-0.5 | **0.0 (remove)** | Same as shallow |
| `explore_situation` `llm.valence.mid` | 0.5 | **0.0** | Valence quantizes to 0.25/0.75 only |
| All strategies `graph.node.slot_saturation.low` | 0.0 (placeholder) | **Remove key** | No contribution, use continuous form |

### Priority 4: Diversity Penalty (Apply to All Strategies)

| YAML Path | Current | Proposed | Evidence |
|-----------|---------|----------|----------|
| `_profiles.diversity_penalty.temporal.strategy_repetition_count` | -0.7 | **-1.0** | Universal fix for strategy monotony |

---

## 6. Implementation Order

1. **First**: Fix `graph.node.focus_streak.high` discretization threshold (code change in detector)
2. **Second**: Apply Priority 1 YAML changes (diversity penalty)
3. **Third**: Apply Priority 2 YAML changes (node rotation)
4. **Fourth**: Apply Priority 3 YAML changes (remove dead weight)
5. **Later**: Fix phase detection to enable `validate_outcome`

---

## 7. Metrics to Track After Changes

| Metric | Current | Target |
|--------|---------|--------|
| dig_motivation selection rate | 45-57% | < 35% |
| Longest consecutive dig_motivation streak | 4 | ≤ 3 |
| validate_outcome selections (social) | 0 | ≥ 1 (turns 12-15) |
| Top node exhaustion turn | 10-12 | ≤ 8 |
| focus_streak.high firings | 0 | ≥ 2 per run |
