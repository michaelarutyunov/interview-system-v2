# Phase 4.1 Test Plan — External Review Request

## System Context

This is an **adaptive interview system** that conducts qualitative research interviews using an AI moderator. The system selects interview strategies based on a **signal-driven scoring engine** — each turn, the engine evaluates all (strategy, node) pairs and picks the highest-scoring one. The scoring is controlled by YAML methodology configs that define signal weights, phase multipliers, and strategy validity gates.

**5 active methodologies**, each with their own YAML config:
- **MEC** (Means-End Chain): 6 strategies, chain-aware (ascend, ground, bridge, branch, anchor, revitalize + now validate)
- **JTBD** (Jobs to Be Done): 7 strategies (elaborate, ascend, ground, probe_pain, anchor, revitalize, validate)
- **CIT** (Critical Incident Technique): 7 strategies (elicit_narrative, ascend, ground, bridge, anchor, revitalize, validate)
- **RG** (Repertory Grid): 8 strategies (explore_construct, ladder_construct, rate_elements, triadic_elicit, explore_ideal, anchor, revitalize, validate)
- **CJM** (Customer Journey Mapping): 8 strategies (map_journey, deepen_stage, advance_stage, track_emotions, probe_friction, anchor, revitalize, validate)

The system uses a **simulation mode** with synthetic personas to test methodology configs without human respondents.

---

## Phase 4 Findings (What Led to Calibration)

### Tier 1 Smoke Tests (baseline_cooperative persona)

| Test | Methodology | Result | Key Issue |
|------|-------------|--------|-----------|
| T1.1 | MEC strict | FAIL | 7x consecutive ascend, no validate closing, only 3 unique strategies |
| T1.2 | JTBD | PASS | Proper termination, good diversity |
| T1.3 | CIT | PASS | Proper termination, narrative intact |
| T1.4 | RG | FAIL | No validate closing, 3x consecutive ladder_construct, hit max turns |
| T1.5 | CJM | PASS | Proper termination, healthy alternation |

### Tier 2 Persona Stress Tests (edge-case personas)

| Test | Persona | Methodology | Result | Key Issue |
|------|---------|-------------|--------|-----------|
| T2.2 | verbose_tangential | MEC strict | FAIL | Ascend dominance, never ladders from deep content |
| T2.3 | single_topic_fixator | MEC strict | FAIL | Same node targeted 4+ turns, validate absent |
| T2.5 | emotionally_reactive | CIT | FAIL | Ascend at 78%, elicit_narrative only 11% |
| T2.6 | retrospective_rationalizer | CIT | FAIL | Ascend at 78%, elicit_narrative loops |
| T2.9 | brief_responder | JTBD | FAIL | Revitalize at 70%, max turns hit |
| T2.10 | uncertain_hedger | RG | FAIL | Ladder_construct streaks, triadic logic weak |

### External LLM Critique Findings (independent review of transcripts)

| Finding | Transcripts | Nature |
|---------|-------------|--------|
| Strategy repetition/monotony | 4/5 | Scoring issue — YAML weights |
| Focus node vs question mismatch | 4/5 | Execution issue — question generation |
| No tangent/contradiction management | 3/5 | Execution issue — question generation |
| Method-specific structural failures | 3/5 | Scoring issue — YAML weights |

### Root Cause Analysis

The fundamental problem was **signal mass asymmetry**: structural signals (fan_in, has_attribute_foundation, recency) accumulate monotonically and grow over time, while penalties are flat or linear. This creates a "runaway leader" effect where one strategy dominates regardless of context.

---

## Calibration Actions Applied

1. **MEC strict**: Reduced ascend's positive signal mass (fan_in 0.067->0.033, foundation 0.400->0.200, recency 0.20->0.15); strengthened penalties (exhaustion -0.6->-0.8, focus_count.high -0.4->-0.8, repetition -0.15->-1.5); added response_depth.deep (+0.3) to trigger laddering on deep content; added response_depth.deep (-0.3) to validate to suppress premature closure; **added validate strategy (was entirely missing from MEC!)**; late phase branch boost (1.1->1.3)

2. **JTBD**: Flipped revitalize repetition weight from +0.15 (escape valve) to -0.5 (brake) to prevent brief-responder loops; added elaborate response_depth.surface (+0.4) and shallow (+0.3) to route brief answers to exploration; boosted elaborate specificity.low (0.2->0.4); elaborate phase bonus (0.1->0.2)

3. **CIT**: Boosted elicit_narrative specificity.low (0.7->0.9), certainty.low (0.4->0.6); added certainty.mid (+0.3), valence.high (+0.3), valence.low (+0.2) to give narrative elicitation competitive firepower; reduced self-penalty (-0.7->-0.5) so it can fire more than once; strengthened ascend repetition brake (-0.15->-0.5); late phase elicit_narrative boost (0.5->0.7 + bonus +0.2)

4. **RG**: Reduced ladder_construct positive mass (intellectual_engagement 0.5->0.3, engagement 0.4->0.2, response_depth 0.4->0.25); strengthened repetition (-1.2->-2.0); reduced explore_ideal late bonus (0.5->0.3) to let validate compete; boosted validate late (0.8->1.0); added late phase bonuses

5. **CJM**: Boosted advance_stage focus_streak.high (0.6->0.9) for stronger advance trigger; mid phase advance_stage multiplier (1.2->1.3)

---

## Phase 4.1: Post-Calibration Re-Test Plan

Re-run Tier 1 and Tier 2 tests with tuned YAMLs to verify calibration effectiveness.

### Tier 1 Re-Tests (baseline_cooperative)

| # | Concept | Methodology | Persona | Turns | Acceptance Criteria |
|---|---------|------------|---------|-------|---------------------|
| T4.1.1 | glp1_food_mec_strict | means_end_chain_v2_strict | baseline_cooperative | 12 | ascend streak <4, validate closes interview |
| T4.1.2 | glp1_food_jtbd | jobs_to_be_done_v2 | baseline_cooperative | 10 | revitalize <40%, elaborate fires at least once |
| T4.1.3 | cold_brew_discovery_cit | critical_incident_v2 | baseline_cooperative | 10 | elicit_narrative >25% of turns, ascend <50% |
| T4.1.4 | plant_milk_comparison_rg | repertory_grid_v2 | baseline_cooperative | 10 | ladder_construct <40%, validate closes |
| T4.1.5 | coffee_subscription_cjm | customer_journey_mapping_v2 | baseline_cooperative | 10 | advance_stage fires at least once |

### Tier 2 Re-Tests (edge-case personas — previously failing tests only)

| # | Concept | Methodology | Persona | Turns | Acceptance Criteria |
|---|---------|------------|---------|-------|---------------------|
| T4.1.6 | glp1_food_mec_strict | means_end_chain_v2_strict | verbose_tangential | 10 | ascend <60%, deep content triggers laddering |
| T4.1.7 | glp1_food_mec_strict | means_end_chain_v2_strict | single_topic_fixator | 10 | node rotation (5+ distinct nodes in 10 turns) |
| T4.1.8 | cold_brew_discovery_cit | critical_incident_v2 | emotionally_reactive | 10 | elicit_narrative >20%, ascend <60% |
| T4.1.9 | glp1_food_jtbd | jobs_to_be_done_v2 | brief_responder | 10 | revitalize <40%, elaborate >25% |
| T4.1.10 | plant_milk_comparison_rg | repertory_grid_v2 | uncertain_hedger | 10 | ladder_construct <40%, triadic_elicit fires |

### Review Process

After re-tests, run the updated `/interview-simulation-reviewer` skill on each transcript. The skill now includes:
- Part 1.5: Focus Node Fidelity Check (question vs node alignment)
- Part 1: Contradiction/tangent/resistance detection
- Part 2: Depth momentum tracking + methodology fidelity audit
- Part 4: Signal-to-question traceability

### Open Code/Prompt Issues (not addressed by YAML tuning)

These issues were identified by the external critique but require code changes, not YAML tuning:
1. Focus node vs question mismatch (bead tks0) — question generator doesn't reference scored focus node
2. No tangent/contradiction management (bead 47eo) — prompts lack behavioral awareness
3. RG triadic logic weak (bead r52u) — triadic_elicit generates dyadic comparisons
4. Concept extraction duplication (bead 0gj2) — same quote re-extracted across turns

---

## Questions for the Reviewer

Please evaluate this Phase 4.1 plan considering:

1. **Test coverage**: Are the 10 re-tests sufficient to validate the calibration changes? Are there any missing test cases that should be included?

2. **Acceptance criteria**: Are the thresholds reasonable? (e.g., ascend <50% for CIT, ladder_construct <40% for RG, 5+ distinct nodes in 10 turns)

3. **Test design**: Should we re-test ALL Tier 2 combinations (including T2.1, T2.4, T2.7, T2.8 that weren't flagged as failing), or is testing only the previously-failing ones sufficient?

4. **Regression risk**: Could the calibration changes introduce new issues in previously-passing tests (T1.2 JTBD, T1.3 CIT, T1.5 CJM)?

5. **Edge cases**: Are there interactions between the calibration changes that could cause unexpected behavior?

6. **Methodology fidelity**: The acceptance criteria focus on strategy distribution. Should we also verify methodology-specific outcomes (e.g., MEC produces chains reaching level 4+, CIT elicits concrete incidents)?

7. **Signal weight calibration approach**: The fundamental approach was "reduce positive mass, not just increase penalties" and "boost competing strategies asymmetrically." Is this the right philosophy, or could it lead to strategy oscillation (overcorrection)?
