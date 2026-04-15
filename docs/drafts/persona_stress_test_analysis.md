# Persona Stress Test Analysis

**Date**: 2026-04-15
**Scope**: Review of 8 edge case personas for Tier 2 stress testing quality
**Goal**: Assess whether personas represent meaningful behavioral edge cases for methodology validation

---

## Executive Summary

**Overall Assessment**: GOOD with minor gaps ✅

The 8 edge case personas cover most critical behavioral dimensions for stress testing:
- Response length (brief → verbose)
- Cognitive engagement (low → high)
- Emotional intensity (flat → reactive)
- Certainty level (uncertain → overconfident)
- Topic discipline (focused → fixated)
- Energy pattern (stable → fatiguing)

**Missing Coverage**: No "hostile/refusal" persona, no "cultural/linguistic barrier" persona

---

## Persona-by-Persona Analysis

### 1. brief_responder ✅ EXCELLENT

**What it stresses**: Low response depth, sparse extraction material
**Signal impact**: `response_depth.low`, `specificity.low`, `engagement.low`
**Methodology pairing**: MEC (tests `ground` for gap filling), JTBD (comparison baseline)

**Stress value**: HIGH - Forces system to work harder for every concept. Tests whether `ground` strategy triggers correctly for terminal nodes and whether interview can progress with minimal material.

**Tier 2 mapping**: T2.1 (MEC), T2.9 (JTBD) ✅

---

### 2. verbose_tangential ✅ GOOD

**What it stresses**: Noisy extraction, many orphan nodes
**Signal impact**: High node count, low coherence, many `is_orphan` nodes
**Methodology pairing**: MEC (tests `anchor` dominance)

**Stress value**: HIGH - Tests extraction quality from messy responses. Tests whether `anchor` strategy fires to connect orphan nodes back to graph structure.

**Tier 2 mapping**: T2.2 ✅

---

### 3. single_topic_fixator ✅ EXCELLENT

**What it stresses**: Node exhaustion, focus streak penalties, strategy rotation
**Signal impact**: `exhaustion_score.high`, `focus_streak.high`, low novelty
**Methodology pairing**: MEC (tests `bridge`/`branch` forcing lateral moves)

**Stress value**: CRITICAL - This is a KEY stress test for the node rotation bug fix (bead 119q). Tests whether the system correctly detects when the same node has been selected 4+ times and forces rotation.

**Tier 2 mapping**: T2.3 ✅

**Note**: This persona specifically validates the node exhaustion/rotation bug fix from Phase 1.

---

### 4. skeptical_analyst ✅ EXCELLENT

**What it stresses**: Low engagement, high intellectual engagement mismatch, safety gates
**Signal impact**: `engagement.low`, `intellectual_engagement.high`, `certainty.high`
**Methodology pairing**: MEC (tests engagement safety gates)

**Stress value**: HIGH - Tests whether engagement safety gates suppress depth strategies when emotional engagement is low despite intellectual engagement being high. Critical for safety.

**Tier 2 mapping**: T2.4 ✅

---

### 5. emotionally_reactive ✅ EXCELLENT

**What it stresses**: Valence extremes, emotion amplification, safety gates
**Signal impact**: `valence.extreme` (both positive/negative), emotion node generation
**Methodology pairing**: CIT (emotion-targeting strategies), CJM (breadth under emotion pressure)

**Stress value**: HIGH - Tests whether emotion-targeting strategies fire correctly and whether valence safety gates activate. Important for CIT narrative arc and CJM breadth maintenance.

**Tier 2 mapping**: T2.5 (CIT), T3.2 (contrast) ✅

---

### 6. retrospective_rationalizer ✅ EXCELLENT

**What it stresses**: Post-hoc reasoning, specificity probing, claim revision
**Signal impact**: High initial `certainty.high`, cracks under probing to reveal emotional/social
**Methodology pairing**: CIT (tests specificity probing, incident vs rationalization)

**Stress value**: HIGH - Specifically designed to test CIT's ability to distinguish genuine incident recall from post-hoc rationalization. Tests whether system probes for concrete detail rather than accepting confident-sounding but shallow answers.

**Tier 2 mapping**: T2.6 ✅

**Note**: This persona has sophisticated design - it's not just "difficult" but tests a specific CIT capability (incident validation).

---

### 7. fatiguing_responder ✅ EXCELLENT

**What it stresses**: Global response trend, `revitalize` triggering, journey mapping breadth
**Signal impact**: `global_response_trend.decreasing`, engagement drop over time
**Methodology pairing**: CJM (tests `revitalize` + journey section shifting)

**Stress value**: CRITICAL - Tests whether `revitalize` fires when engagement drops mid-interview and whether journey mapping shifts sections rather than stalling. Validates temporal trend detection.

**Tier 2 mapping**: T2.7 ✅

**Note**: This is the KEY test for `revitalize` strategy functionality.

---

### 8. uncertain_hedger ✅ GOOD

**What it stresses**: Certainty detection, `validate` triggering, hedge loops
**Signal impact**: `certainty.low`, frequent hedging, self-contradiction
**Methodology pairing**: RG (tests construct validation), CJM (tests hedge handling)

**Stress value**: MEDIUM-HIGH - Tests whether `validate` strategy fires to summarize uncertain positions and whether system gets stuck in infinite clarification loops. Important for RG where confident constructs are needed.

**Tier 2 mapping**: T2.8 (CJM), T2.10 (RG) ✅

**Potential issue**: Risk of infinite "are you sure?" loops if `validate` not properly tuned.

---

## Domain Personas

### baseline_cooperative ✅ ESSENTIAL

**Purpose**: Control group, calibration baseline
**Usage**: Tier 1 smoke tests, Tier 3 cross-methodology contrast

**Assessment**: ESSENTIAL - Not an edge case but the reference point for all other testing. Well-designed with natural speech patterns.

---

### glp1_user ✅ GOOD

**Purpose**: Domain-specific persona for GLP-1 concepts
**Usage**: Domain validation, realistic scenario testing

**Assessment**: GOOD - Provides domain authenticity for food/health concepts. Not a stress test persona but valuable for domain validation.

---

## Coverage Analysis

### Behavioral Dimensions Covered ✅

| Dimension | Low | Medium | High |
|-----------|-----|--------|------|
| **Response length** | brief_responder | baseline | verbose_tangential |
| **Engagement** | skeptical_analyst | baseline | emotionally_reactive |
| **Certainty** | uncertain_hedger | baseline | retrospective_rationalizer |
| **Topic discipline** | single_topic_fixator | baseline | brief_responder (scattered) |
| **Energy pattern** | fatiguing_responder | baseline | emotionally_reactive (high) |
| **Cognitive load** | brief_responder | baseline | skeptical_analyst |

**Assessment**: All major behavioral dimensions have coverage. Good spread across low/medium/high for each dimension.

---

### Signal Pathway Coverage ✅

| Signal | Persona that triggers it | Test |
|--------|------------------------|------|
| `response_depth.low` | brief_responder | T2.1, T2.9 |
| `is_orphan` | verbose_tangential | T2.2 |
| `exhaustion_score.high` | single_topic_fixator | T2.3 |
| `engagement.low` | skeptical_analyst | T2.4 |
| `valence.extreme` | emotionally_reactive | T2.5, T3.2 |
| `global_response_trend.decreasing` | fatiguing_responder | T2.7 |
| `certainty.low` | uncertain_hedger | T2.8, T2.10 |

**Assessment**: All major signal pathways have corresponding stress tests. Good alignment between persona design and signal detection logic.

---

## Gaps and Recommendations

### Missing Edge Cases

1. **Hostile/Refusal Persona** ⚠️
   - **Gap**: No persona that actively refuses or pushes back
   - **Use case**: Test system handling of "I don't want to answer that"
   - **Priority**: LOW - System may not need to handle hostility
   - **Recommendation**: Add if interview system targets sensitive topics

2. **Cultural/Language Barrier Persona** ⚠️
   - **Gap**: No persona with idioms, cultural references, or ESL patterns
   - **Use case**: Test extraction robustness across communication styles
   - **Priority**: MEDIUM - Important for global applicability
   - **Recommendation**: Add if system targets diverse populations

3. **Over-Sharer/Boundary-Crossing** ⚠️
   - **Gap**: No persona that shares too much inappropriate content
   - **Use case**: Test whether system maintains boundaries
   - **Priority**: LOW - Probably not relevant for most research contexts

---

### Tier 2 Test Plan Alignment ✅

The current Tier 2 test plan (from `docs/drafts/test_plan.md`) maps well to available personas:

| Test | Concept | Persona | Stresses | Available? |
|------|---------|---------|----------|------------|
| T2.1 | `glp1_food_mec_strict` | `brief_responder` | Low response depth | ✅ |
| T2.2 | `glp1_food_mec_strict` | `verbose_tangential` | Noisy extraction | ✅ |
| T2.3 | `glp1_food_mec_strict` | `single_topic_fixator` | Node exhaustion | ✅ |
| T2.4 | `glp1_food_mec_strict` | `skeptical_analyst` | Low engagement | ✅ |
| T2.5 | `cold_brew_discovery_cit` | `emotionally_reactive` | Valence extremes | ✅ |
| T2.6 | `cold_brew_discovery_cit` | `retrospective_rationalizer` | Post-hoc reasoning | ✅ |
| T2.7 | `coffee_subscription_cjm` | `fatiguing_responder` | Engagement drop | ✅ |
| T2.8 | `coffee_subscription_cjm` | `uncertain_hedger` | Hedging | ✅ |
| T2.9 | `coffee_jtbd_v2` | `brief_responder` | Cross-methodology comparison | ✅ |
| T2.10 | `plant_milk_comparison_rg` | `uncertain_hedger` | Construct validation | ✅ |

**Assessment**: All Tier 2 tests have corresponding personas. Good methodology-persona pairing.

---

## Persona Quality Assessment

### Strengths ✅

1. **Methodologically grounded**: Each persona maps to specific signals and strategies
2. **Well-documented**: Clear descriptions of speech patterns and response behaviors
3. **Behaviorally distinct**: No overlap - each persona tests different dimension
4. **Realistic**: Based on actual interview patterns, not cartoonish extremes
5. **Tier 2 ready**: Direct mapping to test plan use cases

### Areas for Improvement

1. **Quantitative calibration needed**: Response patterns (detailed/medium/brief ratios) need validation against real interview data
2. **Signal weights untested**: Do these personas actually trigger the intended signals at expected intensity?
3. **No interaction effects**: What happens when `brief_responder` is also `fatiguing`? (Current personas are pure types)

---

## Recommendations

### Immediate Actions ✅

1. **Proceed with Tier 2 testing**: Current personas are adequate for stress testing
2. **Document signal weights**: After Tier 2, document which signals actually fired for each persona
3. **Calibrate response patterns**: Adjust detailed/medium/brief ratios based on test results

### Future Enhancements

1. **Add ESL/Cultural persona** if global applicability is required
2. **Consider hybrid personas** (e.g., "brief + fatiguing") for more realistic stress testing
3. **Create persona validation tests**: Run each persona against baseline to confirm it triggers expected signals

---

## Conclusion

**Verdict**: The 8 edge case personas represent a **strong stress testing suite** that covers all major behavioral dimensions and signal pathways. They are well-designed, methodologically grounded, and ready for Tier 2 testing.

**Key Strengths**:
- Coverage of all critical signal pathways
- Good methodology-persona pairing in Tier 2
- Realistic behavioral patterns (not cartoonish)
- Direct mapping to system capabilities under test

**Minor Gaps**:
- No hostile/refusal persona (probably not needed)
- No cultural/linguistic barrier persona (add if needed for global use)
- Pure types only (no hybrid stress cases)

**Recommendation**: **PROCEED** with Tier 2 testing using current personas. They will effectively expose weaknesses in strategy selection, signal detection, and termination logic.
