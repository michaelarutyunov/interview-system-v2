# Tier 2 Persona Stress Test Summary

**Date**: 2026-04-15
**Tests Completed**: 9/10 (T2.8 pending - CJM + uncertain_hedger still running)

## Executive Summary

The Tier 2 calibration fixes from Tier 1 successfully addressed the validate closure issue - **8/9 completed tests properly terminated with "Closing strategy selected"**. However, significant **strategy dominance issues persist** across multiple persona-methodology combinations, indicating that repetition penalties alone are insufficient to prevent monotony.

## Calibration Fixes Applied (Pre-Test)

From Tier 1 findings, the following fixes were applied:

| Methodology | Fix | Expected Impact |
|-------------|-----|-----------------|
| MEC strict | Added missing `validate` strategy | Should enable proper closure |
| MEC strict | Ascend repetition penalty: -0.15 → -0.5 | Should reduce ascend dominance |
| MEC strict | Added `strategy_repetition_count.high: -1.0` | Should prevent long streaks |
| MEC strict | Validate saturation bonuses boosted | Should help validate fire in late phase |
| RG | Validate early/mid phase gates: -3.0 | Should prevent premature closure |
| RG | Ladder_construct repetition: -0.8 → -1.2 | Should reduce construct dominance |
| JTBD | `has_attribute_foundation.true`: 0.4 → 0.2 | Should reduce ground dominance |
| CIT | Exhaustion penalties strengthened | Should improve node rotation |

## Test Results

### ✅ Tests with Proper Closure (8/9)

All of these properly terminated with validate:

| Test | Methodology + Persona | Strategy Distribution | Dominant Strategy | Key Finding |
|------|----------------------|----------------------|-------------------|-------------|
| T2.1 | MEC strict + brief_responder | ground 56%, revitalize 22%, ascend 11%, validate 11% | ground (5/9 turns) | Ground dominance expected for brief responses |
| T2.2 | MEC strict + verbose_tangential | ground 78%, branch 11%, validate 11% | ground (7/9 turns) | ⚠️ SEVERE dominance |
| T2.3 | MEC strict + single_topic_fixator | ascend 44%, ground 33%, branch 11%, validate 11% | ascend (4/9 turns) | Moderate ascend dominance |
| T2.4 | MEC strict + skeptical_analyst | ascend 56%, ground 33%, validate 11% | ascend (5/9 turns) | ⚠️ Ascend dominance despite low engagement |
| T2.5 | CIT + emotionally_reactive | ascend 78%, elicit_narrative 11%, validate 11% | ascend (7/9 turns) | ⚠️ SEVERE ascend dominance |
| T2.6 | CIT + retrospective_rationalizer | ascend 78%, elicit_narrative 11%, validate 11% | ascend (7/9 turns) | ⚠️ SEVERE ascend dominance |
| T2.7 | CJM + fatiguing_responder | advance_stage 33%, track_emotions 22%, deepen_stage 22%, probe_friction 11%, validate 11% | Balanced (no >50%) | ✅ HEALTHY diversity |
| T2.10 | RG + uncertain_hedger | explore_construct 33%, ladder_construct 33%, triadic_elicit 22%, validate 11% | Balanced (no >50%) | ✅ HEALTHY diversity |

### ❌ Test Failure (1/9)

| Test | Issue | Details |
|------|-------|---------|
| T2.9 | JTBD + brief_responder | **Maximum turns reached** - NO validate closure. Strategy: revitalize 70%, ground 20%, validate 10%. Revitalize fired 7/10 turns but interview hit max turns before validate could close. |

### ⏳ Pending (1/10)

| Test | Status |
|------|--------|
| T2.8 | CJM + uncertain_hedger - Still running after 10+ minutes (unusually long) |

## Key Findings

### 1. Validate Closure: SUCCESS ✅

**8/9 tests properly terminated with validate**. The Tier 1 fixes (adding validate to MEC strict, boosting saturation bonuses, adding late-phase gates) successfully resolved the "no closure" bug from Tier 1.

**Exception**: T2.9 (JTBD + brief_responder) hit max turns before validate could close properly.

### 2. Strategy Dominance: FAILURE ⚠️

**Severe dominance (>70% of turns)**:
- T2.2 (MEC + verbose_tangential): ground 78%
- T2.5 (CIT + emotionally_reactive): ascend 78%
- T2.6 (CIT + retrospective_rationalizer): ascend 78%

**Moderate dominance (50-70% of turns)**:
- T2.1 (MEC + brief_responder): ground 56%
- T2.4 (MEC + skeptical_analyst): ascend 56%
- T2.9 (JTBD + brief_responder): revitalize 70% (hit max turns)

**Healthy distribution (no >50% dominance)**:
- T2.3 (MEC + single_topic_fixator): ascend 44% (acceptable)
- T2.7 (CJM + fatiguing_responder): Balanced ✅
- T2.10 (RG + uncertain_hedger): Balanced ✅

### 3. Persona-Specific Stress Patterns

| Persona | Expected Stress | Observed Behavior | Status |
|---------|----------------|-------------------|--------|
| brief_responder (MEC) | Low depth → ground/anchor | ground 56% dominance | ⚠️ Expected ground, but too dominant |
| brief_responder (JTBD) | Same persona, different method | revitalize 70%, hit max turns | ❌ FAILED - JTBD can't handle brief responses |
| verbose_tangential | Noisy extraction → anchor | ground 78% (not anchor!) | ❌ FAILED - anchor not firing |
| single_topic_fixator | Node exhaustion → bridge/branch | ascend 44% dominance | ⚠️ Expected bridge/branch, got ascend |
| skeptical_analyst | Low engagement → suppress depth | ascend 56% dominance | ❌ FAILED - ascend not suppressed |
| emotionally_reactive | High valence → emotion strategies | ascend 78% (not emotion!) | ❌ FAILED - CIT emotion strategies not firing |
| retrospective_rationalizer | Probe specificity | ascend 78% | ⚠️ ascend dominance, not specificity probing |
| fatiguing_responder | Engagement drop → revitalize | Balanced diversity | ✅ PASSED |
| uncertain_hedger (RG) | Construct validation | Balanced diversity | ✅ PASSED |

### 4. Methodology-Specific Issues

**MEC strict**:
- Ground dominance persists despite calibration (56-78% across 3 tests)
- Ascend dominance also present (44-56% across 2 tests)
- Repetition penalties insufficient to break streaks

**CIT**:
- Severe ascend dominance (78% across 2 tests)
- CIT-specific strategies (elicit_narrative) only fire 11% of the time
- Ascend is winning despite CIT having narrative-specific strategies

**JTBD**:
- **CRITICAL FAILURE**: Cannot handle brief_responder persona
- Revitalize fires excessively (70%) but doesn't prevent max turns
- Different methodology, same brief_responder persona → drastically different outcome vs MEC

**CJM**:
- **HEALTHY**: Fatiguing_responder produces balanced strategy distribution
- Temporal flow strategies work as designed

**RG**:
- **HEALTHY**: Uncertain_hedger produces balanced strategy distribution
- Construct elicitation strategies fire appropriately

## Root Cause Analysis

### Why Repetition Penalties Aren't Working

The calibration applied stronger repetition penalties (e.g., ascend: -0.15 → -0.5, added `strategy_repetition_count.high: -1.0`), but dominance persists. Analysis:

1. **Signal symmetry**: Many signals are "global" (same value for all strategies at a given turn). Changing their weights shifts all scores equally and cannot fix dominance.

2. **Penalty asymmetry**: The dominant strategy may lack penalties that competitors carry. Check YAML for `<<: [*strategy_break]` patterns.

3. **Phase multiplier amplification**: If phase multipliers consistently widen the gap between winner and runner-up, they amplify dominance rather than enable phase-appropriate behavior.

4. **Structural advantages**: Some strategies have inherently higher positive signal mass. If both dominant and runner-up have similar total mass but one wins consistently, there's a structural advantage (multiplier differentials, missing negative signals).

### Why JTBD Failed with brief_responder

T2.9 (JTBD + brief_responder) hit max turns with revitalize dominating (70%). Hypothesis:

- JTBD's revitalize may not have strong enough phase gates or penalties
- Brief responses trigger revitalize repeatedly without advancing the interview
- JTBD's job-focused ontology may not ground well with brief answers
- Contrast with T2.1 (MEC + brief_responder) which terminated properly

## Recommendations

### Immediate Actions (Priority 1)

1. **Fix JTBD revitalize dominance**:
   - Add stronger phase gates to revitalize (early/mid: -3.0)
   - Reduce revitalize base weights or increase repetition penalty
   - Check if JTBD's revitalize is structurally different from MEC's

2. **Fix MEC ground dominance**:
   - Investigate why ground wins 78% with verbose_tangential (expected anchor)
   - Check if anchor's `valid_when: graph.node.is_orphan` is firing correctly
   - May need to boost anchor weights or reduce ground's foundation signal weight

3. **Fix CIT ascend dominance**:
   - CIT has narrative-specific strategies (elicit_narrative) that should fire more
   - Ascend at 78% indicates CIT is behaving like MEC
   - Check if CIT's elicit_narrative weights are too low relative to ascend

### Secondary Actions (Priority 2)

4. **Investigate signal symmetry**:
   - Use scoring CSV to identify global signals that add flat offsets
   - Replace global signals with strategy-specific asymmetries

5. **Check penalty asymmetry**:
   - Audit which strategies carry which negative-weight signals
   - Ensure dominant strategies don't lack penalties that competitors carry

6. **Phase multiplier audit**:
   - Compare phase_multiplier × base_score between winner and runner-up
   - If multipliers consistently widen gaps, reduce phase weight variance

### T2.8 Investigation

T2.8 (CJM + uncertain_hedger) has been running for 10+ minutes, which is unusually long. Investigate:
- Check if the simulation is stuck in a loop
- Verify CJM + uncertain_hedger combination doesn't create infinite clarification
- May need to kill and restart with max_turns=5 for diagnostic

## Comparison with Tier 1

| Metric | Tier 1 | Tier 2 (Current) | Change |
|--------|--------|------------------|--------|
| MEC validate closure | ❌ Failed | ✅ 3/3 passed | FIXED |
| RG validate closure | ❌ Failed | ✅ 1/1 passed | FIXED |
| Strategy dominance | Present | SEVERE | WORSENED |
| JTBD health | ✅ Passed baseline | ❌ Failed brief_responder | REGRESSED |

**Conclusion**: Tier 1 calibration fixed validate closure but did not address (and may have exacerbated) strategy dominance. A different calibration approach is needed for monotony prevention.

## Next Steps

1. Wait for T2.8 to complete or investigate if stuck
2. Generate detailed reviews using interview-simulation-reviewer skill for each failing test
3. Apply targeted fixes for JTBD revitalize, MEC ground, CIT ascend
4. Re-run failed tests with additional logging to understand dominance patterns
5. Consider phase 2 calibration: structural changes rather than just weight tweaks
