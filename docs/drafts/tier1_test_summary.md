# Tier 1 Smoke Test Results - 2026-04-15

**Test Date**: 2026-04-15
**Scope**: Baseline smoke tests for all 5 methodologies with `baseline_cooperative` persona
**Goal**: Confirm basic loop works — strategies fire, phases transition, interview completes properly

---

## Executive Summary

**Overall Status**: 3/5 PASS ✅, 2/5 HAVE ISSUES ⚠️

- **PASSING**: JTBD, CIT, CJM all terminate properly with `validate` closing strategy
- **ISSUES**: MEC and RG both fail to terminate properly, hitting max turns without closing

---

## Detailed Results

### T1.1: MEC Strict (means_end_chain_v2_strict) ⚠️

**Concept**: `glp1_food_mec_strict`
**Turns**: 13 (requested 12)
**Status**: Maximum turns reached (NO VALIDATE CLOSING)
**Graph**: 42 nodes, 47 edges, edge-to-node ratio 1.12

**Strategy Sequence**:
```
Turn 1-4:  ground (4× consecutive)
Turn 5:    revitalize
Turn 6-12: ascend (7× consecutive) ← RED FLAG
```

**Scoring Decomposition Findings**:
- `temporal.strategy_repetition_count` fires 96% of rows but contributes only -0.093 on average — **too weak to break dominance**
- `graph.node.branching_deficit` fires 100% (always-on +0.207 flat bonus for `branch`), yet `branch` was **never selected** despite 20 nodes passing its gate
- `graph.node.exhaustion_score` fires only 13% of rows with tiny -0.057 contribution — **node rotation penalty is invisible**
- `focus_count.high` is completely dead (never triggered)
- Top node (`acting responsibly and considering consequences`) was selected **5 turns out of 12**
- Phase multiplier widened the score gap in 3/12 turns, amplifying `ascend` dominance in late phase

**Root Cause Analysis**:
- `ascend` dominates because `gap_above.true` (+0.250) and `has_attribute_foundation` bonuses pile up faster than repetition penalties can offset them
- `validate` has heavy early/mid phase gates (-3.0) which work, but in late phase its base score cannot compete with `ascend`'s structural signal mass
- `branch` is structurally eligible (20 nodes pass gate) but its base score is uncompetitive due to weak signal weights and lack of phase bonus in late phase

**Concrete Recommendations**:
1. **`config/methodologies/means_end_chain_v2_strict.yaml`** — Increase `ascend` repetition brake:
   - Change `temporal.strategy_repetition_count` weight from -0.15 to **-0.5**
   - Add `temporal.strategy_repetition_count.high` weight = **-1.0** (currently absent)
2. **Boost `validate` late-phase competitiveness**:
   - Add `meta.conversation.saturation.high: 0.6` and `meta.canonical.saturation.high: 0.4` to `validate` signal_weights
   - Increase `phases.late.phase_bonuses.validate` from current value to **0.4**
3. **Fix node rotation**:
   - Increase `graph.node.focus_count.high` weight from -0.4 to **-1.2**
   - Increase `graph.node.exhaustion_score` weight magnitude (currently near-zero effective impact)
4. **Re-enable `branch` competition**:
   - Add `phases.late.phase_bonuses.branch: 0.3` so `branch` can compete with `ascend` when branching_deficit is high

---

### T1.2: JTBD (jobs_to_be_done_v2) ✅

**Concept**: `glp1_food_jtbd`
**Turns**: 10
**Status**: Closing strategy selected (PROPER TERMINATION)
**Graph**: 32 nodes, 45 edges, edge-to-node ratio 1.41

**Strategy Sequence**:
```
Turn 1-3:  ground (3× consecutive)
Turn 4-5:  revitalize (2× consecutive)
Turn 6-7:  ground (2× consecutive)
Turn 8:    ascend
Turn 9:    validate (closing) ← CORRECT
```

**Scoring Decomposition Findings**:
- `ground` dominates (55.6%) because `gap_below.true` fires on the few terminal nodes and `has_attribute_foundation.true` adds a near-constant +0.400 bonus
- `ascend` only fired once despite `gap_above.true` being 100% true for eligible nodes — `ascend` is gated to only 3 nodes while `ground` targets 1 node, and `ground` benefits from higher phase weights in mid-phase
- `elaborate` never selected — its signal profile is too weak to overcome `ground`'s structural bonuses
- No strategy streaks ≥ 4 turns; proper termination

**Assessment**: GOOD ✅
- Proper termination with `validate` closing strategy
- Good strategy diversity (4 unique)
- Natural rotation with `revitalize` breaking patterns
- Healthy phase progression

**Concrete Recommendations** (fine-tuning, not critical):
1. **`config/methodologies/jobs_to_be_done_v2.yaml`** — Reduce `has_attribute_foundation.true` weight from **0.4 to 0.2**; it currently acts as a near-flat bonus that disproportionately benefits `ground`
2. Give `elaborate` a small early-phase edge by adding `llm.specificity.low: 0.3` and increasing `phases.early.phase_bonuses.elaborate` to **0.2**

---

### T1.3: CIT (critical_incident_v2) ✅

**Concept**: `cold_brew_discovery_cit`
**Turns**: 10
**Status**: Closing strategy selected (PROPER TERMINATION)
**Graph**: 37 nodes, 46 edges, edge-to-node ratio 1.24

**Strategy Sequence**:
```
Turn 1:    elicit_narrative
Turn 2-3:  ascend (2× consecutive)
Turn 4-5:  elicit_narrative (2× consecutive)
Turn 6:    revitalize
Turn 7-8:  ascend (2× consecutive)
Turn 9:    validate (closing) ← CORRECT
```

**Scoring Decomposition Findings**:
- `gap_below.true` and `gap_above.true` both fire 100% for their eligible nodes — MEC-style laddering translates cleanly to CIT
- `recency_score` and `exhaustion_score` have very low fire rates (3%) and negligible contributions — node rotation signals are too weak to matter
- `bridge` was gated for all 37 nodes (0 scored) — no level skips occurred, which is methodologically healthy
- No strategy streaks ≥ 4; validate fired cleanly in late phase

**Assessment**: GOOD ✅
- Proper termination with `validate` closing strategy
- Narrative structure intact (`elicit_nissue_narrative` appears appropriately)
- Chain-aware laddering with `ascend`
- Natural rotation with `revitalize` breaking patterns

**Concrete Recommendations**:
1. **`config/methodologies/critical_incident_v2.yaml`** — Increase `graph.node.exhaustion_score` weight from its current near-zero effective value to **-0.6** to improve node rotation (currently only 3% fire rate with -0.057 avg contribution)
2. Consider adding `llm.response_depth.shallow: 0.1` to `ground` to make it more responsive to shallow narrative mentions (currently dead signal in this run)

---

### T1.4: RG (repertory_grid_v2) ⚠️

**Concept**: `plant_milk_comparison_rg`
**Turns**: 11 (requested 10)
**Status**: Maximum turns reached (NO VALIDATE CLOSING)
**Graph**: 71 nodes, 75 edges, edge-to-node ratio 1.06

**Strategy Sequence**:
```
Turn 1:    explore_construct
Turn 2:    triadic_elicit ← GOOD (core RG strategy)
Turn 3:    explore_construct
Turn 4:    rate_elements
Turn 5-7:  ladder_construct (3× consecutive) ← RED FLAG
Turn 8:    explore_construct
Turn 9-10: explore_ideal (2× consecutive)
```

**Scoring Decomposition Findings**:
- `temporal.strategy_repetition_count` penalty fires 97% but contributes only -0.185 on average — **insufficient to prevent `ladder_construct` 3× streak**
- `validate` has no hard early/mid phase gates (unlike MEC/JTBD/CIT). It relies entirely on `phase_weights` and soft saturation signals
- `meta.conversation.saturation.high` is dead (0% fire rate) despite being a weight on `explore_ideal`
- `graph.node.focus_streak.high` and `medium` are dead — node-level rotation penalties never trigger
- Phase multiplier widened the gap in 3/10 turns, favoring `explore_ideal` over `validate` in late phase

**Root Cause Analysis**:
- `validate` lacks the structural protection other methodologies use: heavy `-3.0` early/mid signal gates
- `ladder_construct` has the strongest repetition penalty (-0.8) in the YAML but the actual weighted contribution is still too small because `strategy_repetition_count` is normalized/dampened
- Rich graph extraction (71 nodes) proves RG's core construct-elicitation is working; the failure is purely strategic closure

**Concrete Recommendations**:
1. **`config/methodologies/repertory_grid_v2.yaml`** — Add hard phase gates to `validate`:
   - `meta.interview.phase.early: -3.0`
   - `meta.interview.phase.mid: -3.0`
   (This is the single most important fix for RG.)
2. **Strengthen `ladder_construct` repetition brake**:
   - Increase `temporal.strategy_repetition_count` weight from -0.8 to **-1.2**
   - Add `temporal.strategy_repetition_count.high: -0.8`
3. **Boost `validate` late-phase score**:
   - Add `graph.node.has_outgoing.true: 0.5` to `validate` signal_weights
   - Increase `phases.late.phase_bonuses.validate` from 0.15 to **0.3**
4. **Fix dead node-rotation signals**:
   - Lower the threshold for `focus_streak.high` in the signal detector, or increase its weight from -0.5 to **-1.0** so it actually breaks streaks

---

### T1.5: CJM (customer_journey_mapping_v2) ✅

**Concept**: `coffee_subscription_cjm`
**Turns**: 10
**Status**: Closing strategy selected (PROPER TERMINATION)
**Graph**: 36 nodes, 56 edges, edge-to-node ratio 1.56

**Strategy Sequence**:
```
Turn 1:    deepen_stage
Turn 2:    track_emotions
Turn 3:    deepen_stage
Turn 4:    track_emotions
Turn 5:    deepen_stage
Turn 6:    track_emotions
Turn 7:    deepen_stage
Turn 8:    probe_friction
Turn 9:    validate (closing) ← CORRECT
```

**Scoring Decomposition Findings**:
- `deepen_stage` dominates (44.4%) driven by `graph.node.exhaustion_score.low` (100% fire, +0.400) and `graph.node.focus_streak.none` (97% fire, +0.400) — **fresh-node targeting, not depth deficits**
- `llm.response_depth.surface` and `shallow` are dead for CJM — `deepen_stage`'s depth-based weights never trigger
- `graph.node.is_orphan.true` is dead (0% fire rate) — no orphans exist, which is healthy, but `anchor`'s gate and weights are effectively vacuous
- `llm.engagement.low` and `llm.global_response_trend.fatigued` are dead — respondent stayed highly engaged
- `meta.conversation.saturation` and `meta.canonical.saturation` fire 89-100% as global flat offsets

**Assessment**: GOOD ✅
- Proper termination with `validate` closing strategy
- Healthy alternation pattern (deepen_stage ↔ track_emotions)
- Late-phase shift to `probe_friction` before closing (methodologically sound)
- Rich journey structure (highest edge-to-node ratio 1.56)

**Concrete Recommendations**:
1. **`config/methodologies/customer_journey_mapping_v2.yaml`** — `deepen_stage` should respond to actual depth deficits, not just node freshness:
   - Add `llm.response_depth.surface: 0.3` and `llm.response_depth.shallow: 0.4` (currently dead signals in this run because weights exist but respondent depth was always moderate/deep)
   - Reduce `graph.node.exhaustion_score.low` from **0.5 to 0.3** to reduce over-dependence on freshness
2. `advance_stage` was never selected in this run. It should fire when a stage is saturated:
   - Increase `meta.conversation.saturation.high` weight from 0.6 to **0.9** on `advance_stage`
   - Increase `graph.node.focus_streak.high` weight from 0.6 to **0.9**

---

## Cross-Methodology Comparison

**Termination Behavior**:
- **Properly terminating**: JTBD, CIT, CJM (all use `validate` for closing)
- **Not terminating**: MEC, RG (both hit max turns)

**Why `validate` Fails in MEC vs RG**:
- **MEC**: `validate` has hard early/mid gates (-3.0) but `ascend` base scores are so high in late phase that `validate` cannot overcome them even when ungated
- **RG**: `validate` has NO hard early/mid gates at all — it relies purely on phase_weights, and `explore_ideal` out-competes it in late phase

**Strategy Diversity** (unique strategies per interview):
- JTBD: 4 ✅
- CIT: 4 ✅
- CJM: 4 ✅
- RG: 5 ✅
- MEC: 3 ⚠️ (lowest)

**Graph Richness** (edge-to-node ratio):
- CJM: 1.56 (richest journey structure)
- JTBD: 1.41
- CIT: 1.24
- MEC: 1.12
- RG: 1.06 (but 71 nodes - most elements/constructs)

**Common Signal Pathologies**:
- `temporal.strategy_repetition_count` penalty is **universally too weak** across all methodologies (avg contribution -0.06 to -0.25). It fires almost every turn but cannot break dominance.
- `llm.global_response_trend.fatigued` is dead in 4/5 runs — the `baseline_cooperative` persona simply doesn't fatigue, but this signal is weighted heavily (-0.6 to -1.0) in every YAML, wasting weight budget.
- `meta.conversation.saturation` and `meta.canonical.saturation` fire 89-100% of the time as **global flat offsets** — they don't differentiate strategies, they just inflate all scores.

---

## Issues Requiring Attention

### Priority 1: Missing `validate` Closing Strategy

**Affected Methodologies**: MEC, RG

**MEC Fix** (reference methodology — highest priority):
- Boost `validate` late-phase base score with saturation bonuses
- Increase `phases.late.phase_bonuses.validate` to 0.4
- Increase `ascend` repetition penalty so it doesn't monopolize late phase

**RG Fix**:
- Add hard `-3.0` early/mid phase gates to `validate` (copy pattern from JTBD/CIT)
- Increase `phases.late.phase_bonuses.validate` to 0.3
- Boost `validate` base score with `graph.node.has_outgoing.true: 0.5`

### Priority 2: Strategy Repetition Penalties Are Too Weak

**Affected Methodologies**: MEC (7× ascend), RG (3× ladder_construct)

**Evidence from CSV**:
| Methodology | Avg Repetition Contribution | Max Streak |
|-------------|---------------------------|------------|
| MEC         | -0.093                    | 7          |
| JTBD        | -0.075                    | 3          |
| CIT         | -0.061                    | 2          |
| CJM         | -0.249                    | 2          |
| RG          | -0.185                    | 3          |

CJM's stronger -0.249 contribution correlates with its cleanest alternation pattern. MEC's -0.093 is the weakest and has the worst streak.

**Recommended Actions**:
1. Increase `temporal.strategy_repetition_count` weights across all methodologies to **at least -0.4** for dominant strategies
2. Add `temporal.strategy_repetition_count.high` (≥3 consecutive) with weight **-0.8 to -1.2**
3. Consider removing `llm.global_response_trend.fatigued` weights (dead signal for baseline_cooperative) or reducing them from -1.0 to -0.3 to free up signal budget for repetition penalties

### Priority 3: Always-Firing Signals Waste Weight Budget

**Signals that fired >80% in most runs**:
- `meta.conversation.saturation` (89-100%)
- `meta.canonical.saturation` (89-100%)
- `graph.node.exhaustion_score.low` (100% in CJM)
- `graph.node.focus_streak.none` (97-98% in CJM/RG)

These are **global or near-global flat offsets**. They do not help differentiate strategies — they just raise the baseline score for everyone.

**Recommended Actions**:
1. Audit methodology YAMLs and reduce weights on signals that fire >90% of rows
2. Replace broad `exhaustion_score.low` bonuses with more differentiated thresholds (`medium` / `high` penalties)
3. Use `meta.canonical.saturation.high` (a thresholded, less frequent variant) instead of the raw `meta.canonical.saturation` signal

---

## Next Steps

**Tier 2 Testing**: Persona stress tests may reveal whether these issues are specific to `baseline_cooperative` or systemic across all personas.

**Calibration Priority**:
1. Fix MEC `validate` closing issue and `ascend` streak (highest impact - MEC is reference methodology)
2. Add hard phase gates to RG `validate`
3. Increase repetition penalties across all methodologies (especially MEC, RG)
4. Re-run Tier 1 after calibration to verify fixes

**Specific YAML Edits Checklist**:
- [ ] `means_end_chain_v2_strict.yaml`: ascend repetition -0.5, validate saturation bonuses +0.6/+0.4, branch late bonus +0.3
- [ ] `repertory_grid_v2.yaml`: validate early/mid gates -3.0, ladder_construct repetition -1.2, validate late bonus +0.3
- [ ] `jobs_to_be_done_v2.yaml`: reduce has_attribute_foundation 0.4→0.2, boost elaborate early bonus +0.2
- [ ] `critical_incident_v2.yaml`: increase exhaustion_score penalty magnitude
- [ ] `customer_journey_mapping_v2.yaml`: deepen_stage depth signals +0.3/+0.4, advance_stage saturation +0.9

---

## Test Environment

**Config**: `config/interview_config.yaml`
- Extraction: `claude-sonnet-4-6` with `effort: low`
- Signal scoring: `claude-haiku-4-5`
- Question generation: `claude-haiku-4-5`

**Personas**: All tests used `baseline_cooperative` (8 personas available for stress testing)

**Methodologies**: All 5 v2 methodologies tested
- `means_end_chain_v2_strict` (reference MEC)
- `jobs_to_be_done_v2` (chain-aware JTBD)
- `critical_incident_v2` (chain-aware CIT)
- `repertory_grid_v2` (flat-ontology RG)
- `customer_journey_mapping_v2` (sequential CJM)
