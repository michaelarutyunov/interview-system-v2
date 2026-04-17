# Phase D Test Plan — Per-Concept LLM Signal Validation

**Created**: 2026-04-17
**Context**: Phase D of epic `zltr` — Rationalize LLM signals into per-concept + global rating model
**Purpose**: Validate behavioral parity between old (6 global signals) and new (per-concept elaboration/charge + global engagement/certainty) signal architectures through simulation-based testing and weight tuning.

---

## System Context

This test plan validates the **per-concept LLM signal migration** (Phases A-C) by comparing simulation outputs against a pre-migration baseline. The migration refactored 6 flat response-level signals into a 2-tier model:

### Signal Architecture Changes

| Old Signal (Removed) | New Destination | Scope |
|----------------------|-----------------|-------|
| `llm.response_depth` | Derived from per-concept `elaboration` mean | Global (computed) |
| `llm.specificity` | Folded into per-concept `elaboration` | Per-node |
| `llm.valence` | Folded into per-concept `charge` | Per-node |
| `llm.engagement` | **KEPT AS GLOBAL** (replaced with new prompt) | Global |
| `llm.intellectual_engagement` | Folded into per-concept `elaboration` | Per-node |
| `llm.certainty` | **KEPT AS-IS** | Global |

### New Signals Introduced

| Signal | Scope | Values | Source |
|--------|-------|--------|--------|
| `graph.node.elaboration` | Per-node | `[0, 1]` float | Mean of per-concept ratings |
| `graph.node.elaboration.{low,medium,high}` | Per-node | bool | Threshold bins |
| `graph.node.charge` | Per-node | `[0, 1]` float | Mean of per-concept ratings |
| `graph.node.charge.{positive,negative}` | Per-node | bool | Threshold bins |
| `graph.node.has_quality_data` | Per-node | bool | `extraction_count >= 1` |

---

## Phase D Scope

This test plan covers **validation ONLY** — no new code features. Phases A-C (design + implementation) are already complete (beads ukyk, 7p6s, ymom, 4540, f965 all CLOSED).

### What Phase D Validates

1. **Behavioral parity**: Strategy selection distributions should remain similar (within acceptable bounds)
2. **Node coverage**: No regression in node rotation or coverage patterns
3. **Signal fidelity**: Derived `llm.response_depth` produces equivalent categorization
4. **Edge case handling**: System degrades gracefully under stress conditions
5. **Weight correctness**: Mechanical migration (Section C.4) produces sane weights; tuning addresses residual drift

### What Phase D Does NOT Cover

- Context doc updates (deferred to separate follow-up bead per Phase C-impl notes)
- New signal features (e.g., novelty dimension, mentioned-but-not-extracted concepts)
- Performance benchmarks (LLM call latency, token counts — out of scope for v1)

---

## Test Infrastructure

### Simulation Command

```bash
# Run a simulation with specified concept, methodology, and persona
uv run python scripts/run_simulation.py <concept_id> <persona_id> <max_turns>

# Example:
uv run python scripts/run_simulation.py glp1_food_mec_strict baseline_cooperative 10
```

### Output Location

Simulations write to `data/simulations/<session_id>.json`. Each JSON contains:
- `transcript`: Full question/response history
- `scoring_history`: Per-turn strategy selection with score decompositions
- `graph_state`: Node coverage, edge counts, metrics
- `llm_usage`: Token counts, costs

### Analysis Tools

- `/interview-simulation-reviewer` skill — Comprehensive transcript review with 5 checks including focus node fidelity, contradiction detection, depth momentum
- `scripts/analyze_simulation.py` — (if exists) Batch CSV extraction for quantitative comparison

---

## Part 1: Baseline Capture

### 1.1 Baseline Protocol

**CRITICAL**: Baseline MUST be captured from the **pre-Phase B** code state. The current codebase already has Phases A-C implemented (commits 0cbbb71, 653d0e1), so we need to check if a baseline was captured BEFORE those changes.

**Check for existing baseline**:
```bash
# Check if baseline tag exists
git tag | grep pre-signal-rationalization

# If not found, baseline was NOT captured before implementation
# This is a deviation from the original plan — document this
```

### 1.2 Baseline Test Matrix

If baseline exists, it should cover:

| Test ID | Concept | Methodology | Persona | Turns | Purpose |
|---------|---------|------------|---------|-------|---------|
| B.1 | `glp1_food_mec_strict` | means_end_chain_v2_strict | baseline_cooperative | 10 | MEC baseline behavior |
| B.2 | `glp1_food_jtbd` | jobs_to_be_done_v2 | baseline_cooperative | 10 | JTBD baseline behavior |
| B.3 | `cold_brew_discovery_cit` | critical_incident_v2 | baseline_cooperative | 10 | CIT baseline behavior |
| B.4 | `coffee_subscription_cjm` | customer_journey_mapping_v2 | baseline_cooperative | 10 | CJM baseline behavior |
| B.5 | `plant_milk_comparison_rg` | repertory_grid_v2 | baseline_cooperative | 10 | RG baseline behavior |

### 1.3 Baseline Artifacts

For each baseline test, capture:
- **Strategy distribution**: CSV with columns `turn, strategy, node_id, score`
- **Node coverage`: CSV with columns `node_id, first_seen_turn, exposure_count, last_seen_turn`
- **Signal decompositions**: JSON with per-turn signal contributions
- **Transcript**: Full Q&A for qualitative review

### 1.4 Baseline Status

**Current situation**: Phases A-C are already merged. This means:
- ❌ Baseline was NOT captured pre-implementation (as originally planned)
- ✅ We have `docs/drafts/test_plan.md` Phase 4.1 test results from 2026-04-15 (pre-signal-rationalization)
- ✅ These can serve as a **proxy baseline** for comparison

**Proxy baseline artifacts**:
- `docs/drafts/tier1_test_summary.md` — Tier 1 smoke test results
- `docs/drafts/tier2_test_summary.md` — Tier 2 persona stress test results
- `docs/drafts/persona_stress_test_analysis.md` — Detailed analysis

---

## Part 2: Simulation Comparison

### 2.1 Comparison Test Matrix

Re-run the same tests from the proxy baseline with the NEW signal system:

| Test ID | Concept | Methodology | Persona | Turns | Expected Delta |
|---------|---------|------------|---------|-------|----------------|
| C.1 | `glp1_food_mec_strict` | means_end_chain_v2_strict | baseline_cooperative | 10 | Strategy distribution within ±20% |
| C.2 | `glp1_food_jtbd` | jobs_to_be_done_v2 | baseline_cooperative | 10 | Strategy distribution within ±20% |
| C.3 | `cold_brew_discovery_cit` | critical_incident_v2 | baseline_cooperative | 10 | Strategy distribution within ±20% |
| C.4 | `coffee_subscription_cjm` | customer_journey_mapping_v2 | baseline_cooperative | 10 | Strategy distribution within ±20% |
| C.5 | `plant_milk_comparison_rg` | repertory_grid_v2 | baseline_cooperative | 10 | Strategy distribution within ±20% |

### 2.2 Comparison Metrics

For each test, compute:

**Quantitative metrics**:
```python
# Strategy distribution delta
delta_strategy = abs(new_pct - old_pct)

# Node coverage similarity
jaccard_similarity = len(new_nodes ∩ old_nodes) / len(new_nodes ∪ old_nodes)

# Response depth categorization agreement
depth_agreement = sum(new_depth == old_depth) / total_turns

# Score decomposition correlation
pearson_r = correlate(new_scores, old_scores)
```

**Qualitative checks**:
- Transcript naturalness (do questions read like a skilled interviewer?)
- Methodology fidelity (does MEC ladder? Does CIT tell stories?)
- Flow coherence (does each question follow from the previous answer?)

### 2.3 Acceptance Criteria

A comparison test **PASSES** if:
1. **Strategy distribution**: No strategy changes by more than ±30% of turns
2. **Node coverage**: Jaccard similarity ≥ 0.6 (at least 60% overlap)
3. **Response depth**: Categorization agreement ≥ 70%
4. **No regressions**: Node rotation patterns NOT worse than baseline
5. **Transcript quality**: `/interview-simulation-reviewer` skill reports no new red flags

### 2.4 Comparison Report Template

For each test, produce a markdown section:

```markdown
## Test C.X: <methodology> with <persona>

### Strategy Distribution

| Strategy | Baseline % | New % | Delta | Status |
|----------|-----------|-------|-------|--------|
| ascend | 40% | 35% | -5% | ✅ |
| ground | 20% | 22% | +2% | ✅ |
| validate | 10% | 12% | +2% | ✅ |

**Overall distribution shift**: 12% (within ±30% threshold) ✅

### Node Coverage

- **Baseline**: 8 unique nodes, Jaccard=0.75
- **New**: 7 unique nodes, Jaccard=0.70
- **Overlap**: 6 nodes shared (75%)
- **Status**: ✅ Acceptable

### Response Depth

| Depth | Baseline | New | Agreement |
|-------|----------|-----|-----------|
| surface | 2 | 2 | ✅ |
| shallow | 3 | 4 | ⚠️ |
| moderate | 3 | 2 | ✅ |
| deep | 2 | 2 | ✅ |

**Agreement**: 80% ✅

### Transcript Quality

- **Naturalness**: ✅ Questions read well
- **Methodology fidelity**: ✅ Laddering present
- **Flow coherence**: ✅ Each question follows previous

### Conclusion

**PASS** — All quantitative metrics within thresholds. No qualitative regressions.
```

---

## Part 3: Edge Case Testing

### 3.1 Edge Case Scenarios

#### EC.1: Many Concepts (5+)

**Purpose**: Validate system handles rich extractions without breaking.

**Setup**:
- Use `verbose_tangential` persona (produces many extractions)
- Run with MEC strict (methodology with complex signal routing)
- Expect: 5+ concepts extracted in at least one turn

**Validation**:
- [ ] No crash or timeout when 5+ concepts extracted
- [ ] All concepts receive `elaboration` and `charge` ratings
- [ ] Per-concept → per-node routing succeeds for all concepts
- [ ] Strategy selection completes without error

**Expected behavior**:
- System should process all concepts without degradation
- Node tracker should append quality history for all resolved nodes
- Derived `llm.response_depth` should reflect mean across all concepts

**Failure mode**: LLM omits concepts from JSON response, or system crashes on large concept lists.

---

#### EC.2: No Extracted Concepts

**Purpose**: Validate graceful degradation when extraction fails.

**Setup**:
- Use `brief_responder` persona (produces sparse extractions)
- Craft a prompt that yields zero extractable concepts
- Check for `extraction.is_extractable == False` path

**Validation**:
- [ ] System does NOT crash when extraction is empty
- [ ] `concept_to_node_id` map remains empty
- [ ] Batch detector is NOT called (bypassed per Section C.6 case 4)
- [ ] Global signals default to neutral values
- [ ] Strategy selection proceeds with degraded input

**Expected behavior**:
- `llm.response_depth = "surface"` (no extractions = no new information)
- Node signals emit zeroed floats (no quality data)
- Interview continues (does not stall)

**Failure mode**: System raises `ValueError` on empty concepts, or crashes in bridge step.

---

#### EC.3: Shared Evidence Across Concepts

**Purpose**: Validate attribution when multiple concepts draw from the same quote.

**Setup**:
- Use `baseline_cooperative` with a concept where extractions overlap
- Example: "I love oat milk because it's creamy and sustainable" → two concepts sharing one quote

**Validation**:
- [ ] Both concepts receive ratings (not deduplicated at rating level)
- [ ] Source quotes are correctly attached to each concept
- [ ] If both concepts map to same node (semantic dedup), both ratings append to that node's `quality_history`

**Expected behavior**:
- Concept-level: Each concept gets its own rating
- Node-level: If concepts resolve to same node, node receives multiple quality samples (correct behavior per Section C.6 case 2)

**Failure mode**: Ratings are dropped due to quote de-duplication, or node receives only one rating.

---

#### EC.4: Missing Concept Fallback

**Purpose**: Validate LLM prompt contract enforcement when concepts are missing.

**Setup**:
- Manually craft a test where LLM JSON omits a concept
- Or use `skeptical_analyst` persona (produces sparse responses)

**Validation**:
- [ ] Missing concept key triggers fallback (Section B.1 key-absence handling)
- [ ] Fallback values: `elaboration=1, charge=3` (neutral)
- [ ] Warning logged for missing key
- [ ] System does NOT crash or retry

**Expected behavior**:
- Missing concept receives neutral ratings
- Transcript quality degrades but interview continues
- No silent failures (all missing keys logged)

**Failure mode**: System crashes with `KeyError`, or silently proceeds with incomplete data.

---

### 3.2 Edge Case Test Execution

For each edge case:

1. **Setup**: Configure concept/persona to trigger the scenario
2. **Run**: Execute simulation for 5-10 turns
3. **Capture**: Save simulation JSON and logs
4. **Validate**: Check against acceptance criteria above
5. **Document**: Record result (PASS/FAIL) with evidence

### 3.3 Edge Case Test Report Template

```markdown
## Edge Case EC.X: <title>

### Setup
- **Concept**: `<concept_id>`
- **Persona**: `<persona_id>`
- **Trigger condition**: <how to reproduce>

### Execution
- **Turns run**: 8
- **Concepts extracted**: 6
- **Simulation ID**: `<session_id>`

### Validation Results

| Criterion | Expected | Actual | Status |
|-----------|----------|--------|--------|
| No crash | ✅ | ✅ | ✅ |
| All concepts rated | ✅ | ✅ | ✅ |
| Routing succeeds | ✅ | ✅ | ✅ |

### Evidence
- Log snippet: `<relevant log lines>`
- Quality history sample: `<node_id>: [elaboration_scores]`

### Conclusion

**PASS** — System handles 5+ concepts without errors.
```

---

## Part 4: Weight Tuning

### 4.1 When to Tune Weights

Weight tuning is required if:
1. **Strategy distribution shift exceeds ±30%** for any strategy
2. **Node coverage regresses** (Jaccard < 0.6)
3. **Methodology fidelity breaks** (e.g., MEC stops laddering)
4. **External critique flags** the same issues post-migration

### 4.2 Tuning Process

**Step 1**: Identify the problematic strategy
- Compare baseline vs new distributions
- Find strategies with largest delta
- Check score decompositions for signal contribution shifts

**Step 2**: Diagnose the root cause
- Is it a signal name mismatch? (mechanical migration error)
- Is it a weight magnitude issue? (old weight too high/low)
- Is it a missing signal? (new per-concept signal not contributing)

**Step 3**: Apply tuning fix
- For name mismatches: Fix the YAML weight key
- For magnitude issues: Adjust weight up/down by 0.1-0.2
- For missing signals: Add new weight entry following Section C.4 rules

**Step 4**: Re-run simulation
- Use same concept/persona/turns
- Verify fix addresses the issue
- Check for unintended side effects

**Step 5**: Document the rationale
- Add YAML comment explaining the change
- Record in test plan: "Tuned X strategy weight from 0.5 to 0.3 because..."

### 4.3 Tuning Examples

#### Example 1: Ascend Dominance in MEC

**Problem**: Ascend fires 70% of turns (baseline: 40%)
**Diagnosis**: Per-concept `elaboration` weights sum to 1.2, higher than old `response_depth.deep` (0.8)
**Fix**: Reduce `graph.node.elaboration.high` weight on `ascend` from +0.5 to +0.3
**Result**: Ascend drops to 45% (within threshold)

#### Example 2: Validate Never Fires

**Problem**: Validate strategy absent (baseline: 10%)
**Diagnosis**: `llm.response_depth.deep` removed, but validate didn't receive replacement weight
**Fix**: Add `graph.node.elaboration.high: +0.4` to validate's `signal_weights`
**Result**: Validate fires at 12% (matches baseline)

### 4.4 Per-Methodology Tuning Log

| Methodology | Strategy | Old Weight | New Weight | Rationale | Date |
|-------------|----------|-----------|------------|-----------|------|
| MEC strict | ascend / elaboration.high | +0.5 | +0.3 | Over-dominance post-migration | 2026-04-17 |
| JTBD | elaborate / elaboration.low | 0.0 | +0.4 | Brief responders need elaboration trigger | 2026-04-17 |
| CIT | elicit_narrative / elaboration.high | +0.2 | +0.5 | Narrative richness under-indexed | 2026-04-17 |

---

## Part 5: Regression Prevention

### 5.1 Pre-Tuning Regression Tests

Before applying any tuning, run the **Phase 4.1 regression tests** to ensure the migration didn't break previously passing tests:

| Test ID | Concept | Methodology | Persona | Purpose |
|---------|---------|------------|---------|---------|
| R.1 | `glp1_food_jtbd` | jobs_to_be_done_v2 | baseline_cooperative | JTBD still passes |
| R.2 | `cold_brew_discovery_cit` | critical_incident_v2 | baseline_cooperative | CIT still passes |
| R.3 | `coffee_subscription_cjm` | customer_journey_mapping_v2 | baseline_cooperative | CJM still passes |

These tests passed in Phase 4.1 (2026-04-15). If they fail post-migration, the tuning is too aggressive.

### 5.2 Post-Tuning Smoke Tests

After each tuning iteration, run a **quick smoke test** to verify basic functionality:

```bash
# Fast smoke test (5 turns)
uv run python scripts/run_simulation.py glp1_food_mec_strict baseline_cooperative 5
```

**Checks**:
- [ ] Interview completes without errors
- [ ] At least 3 distinct strategies fire
- [ ] Node coverage ≥ 3 nodes
- [ ] Transcript reads naturally

### 5.3 Guardrails

**Never**:
- Change weights by more than ±0.3 in a single iteration
- Tune more than 2 strategies per methodology in one iteration
- Apply tuning across ALL methodologies without per-methodology testing

**Always**:
- Re-run the specific test that exposed the issue
- Check for unintended side effects on other strategies
- Document the rationale in YAML comments and this test plan

---

## Part 6: Execution Checklist

### 6.1 Pre-Execution

- [ ] Verify Phases A-C are merged (commits 0cbbb71, 653d0e1 present)
- [ ] Confirm signal migration contract exists (`docs/drafts/signal-migration-contract.md`)
- [ ] Check that `/interview-simulation-reviewer` skill is available
- [ ] Create output directory: `mkdir -p data/simulations/phase_d_validation/`

### 6.2 Part 1: Baseline

- [ ] Locate proxy baseline artifacts (Phase 4.1 test results from 2026-04-15)
- [ ] Document baseline deviation (baseline NOT captured pre-implementation)
- [ ] Extract baseline metrics from `docs/drafts/tier1_test_summary.md`

### 6.3 Part 2: Comparison Tests

- [ ] Run C.1-C.5 comparison tests (all 5 methodologies with baseline_cooperative)
- [ ] Compute quantitative metrics (strategy delta, Jaccard, depth agreement)
- [ ] Run `/interview-simulation-reviewer` on each transcript
- [ ] Document results in comparison report template

### 6.4 Part 3: Edge Cases

- [ ] Execute EC.1: Many concepts (verbose_tangential + MEC)
- [ ] Execute EC.2: No concepts (brief_responder + crafted prompt)
- [ ] Execute EC.3: Shared evidence (baseline_cooperative + overlapping concepts)
- [ ] Execute EC.4: Missing concept fallback (skeptical_analyst or manual test)
- [ ] Document results in edge case report template

### 6.5 Part 4: Weight Tuning (if needed)

- [ ] Identify strategies exceeding ±30% threshold
- [ ] Diagnose root cause (signal name / magnitude / missing)
- [ ] Apply tuning fixes per methodology
- [ ] Re-run affected tests
- [ ] Document tuning in per-methodology log

### 6.6 Part 5: Regression Prevention

- [ ] Run R.1-R.3 regression tests before tuning
- [ ] Run smoke tests after each tuning iteration
- [ ] Verify no unintended side effects

### 6.7 Post-Execution

- [ ] Compile all test results into final report
- [ ] Update `docs/drafts/signal-migration-contract.md` with Phase D section
- [ ] Close bead 1gqc with summary of findings
- [ ] Close epic zltr if all acceptance criteria met

---

## Part 7: Success Criteria

Phase D is **COMPLETE** when:

1. **All comparison tests pass**: Strategy distributions within ±30%, node coverage ≥ 0.6 Jaccard
2. **All edge cases pass**: System handles stress conditions gracefully
3. **No regressions**: Previously passing tests still pass
4. **Tuning documented**: All weight changes recorded with rationale
5. **Report generated**: Final validation report with all test results

### Blocking Issues

If any of these occur, Phase D is **BLOCKED**:

- System crash in any edge case (EC.1-EC.4)
- Strategy distribution shift > 50% (indicates architectural problem)
- Node coverage regression < 0.4 Jaccard (indicates routing failure)
- Transcript quality degradation (mechanical questions, incoherent flow)

### Unblock Procedure

1. **Investigate**: Add debug logging to isolate the failure point
2. **Diagnose**: Check if it's a code bug (Phases A-C) or a tuning issue
3. **Fix**: If code bug, file new bead and revert to last working state
4. **Re-test**: After fix, re-run all affected tests

---

## Appendix A: Test Data Reference

### Available Concepts

| Concept ID | Methodology | Nodes | Notes |
|-----------|-------------|-------|-------|
| `glp1_food_mec_strict` | MEC strict | ~43 | Baseline MEC concept |
| `glp1_food_mec_flex` | MEC flex | ~43 | Variant without permitted_connections |
| `glp1_food_jtbd` | JTBD | ~40 | JTBD baseline |
| `coffee_jtbd_v2` | JTBD | ~25 | Coffee-specific JTBD |
| `meal_planning_jtbd_v2` | JTBD | ~30 | Meal planning JTBD |
| `cold_brew_discovery_cit` | CIT | ~35 | Critical incident concept |
| `coffee_subscription_cjm` | CJM | ~40 | Customer journey concept |
| `plant_milk_comparison_rg` | RG | ~30 | Repertory grid concept |

### Available Personas

| Persona ID | Type | Behavioral Stress |
|-----------|------|-------------------|
| `baseline_cooperative` | Domain | Baseline (no stress) |
| `brief_responder` | Edge case | Low response depth |
| `verbose_tangential` | Edge case | Many orphan nodes |
| `single_topic_fixator` | Edge case | Node exhaustion |
| `skeptical_analyst` | Edge case | Low engagement |
| `emotionally_reactive` | Edge case | High valence |
| `retrospective_rationalizer` | Edge case | Post-hoc reasoning |
| `fatiguing_responder` | Edge case | Engagement drop mid-interview |
| `uncertain_hedger` | Edge case | Hedged answers |
| `glp1_user` | Domain | Domain-specific persona |
| `health_conscious` | Domain | Health-focused persona |

### Methodology Strategy Counts

| Methodology | Strategies | Chain-Aware? |
|-------------|-----------|--------------|
| MEC v2 strict | 6 | Yes (ascend, ground, bridge, branch, anchor, revitalize) |
| MEC v2 flex | 6 | Yes (same as strict, no permitted_connections) |
| JTBD v2 | 7 | Yes (5 MEC + elaborate, probe_pain) |
| CIT v2 | 7 | Yes (5 MEC + elicit_narrative, bridge) |
| CJM v2 | 8 | No (temporal flow, flat ontology) |
| RG v2 | 8 | No (dimensional, flat ontology) |

---

## Appendix B: Related Documentation

- **Signal Migration Contract**: `docs/drafts/signal-migration-contract.md` — Full design spec for Phases A-C
- **Phase 4.1 Test Plan**: `docs/drafts/test_plan.md` — Methodology YAML tuning tests (proxy baseline)
- **System Design**: `docs/SYSTEM_DESIGN.md` — Architecture overview
- **Pipeline Contracts**: `.claude/context/pipeline-contracts.md` — Stage input/output contracts
- **Signal Detection (LLM)**: `.claude/context/signal-detection-llm.md` — LLM signal detection specs (pre-migration)

---

## Appendix C: Glossary

- **Per-concept signal**: Signal computed for EACH extracted concept (e.g., elaboration, charge)
- **Global signal**: Signal computed once per response (e.g., engagement, certainty)
- **Node-scoped signal**: Signal available at the KG node level for strategy scoring (e.g., `graph.node.elaboration`)
- **Derived signal**: Signal computed from other signals (e.g., `llm.response_depth` from elaboration mean)
- **Bridge step**: Stage 6 logic that maps per-concept ratings to node IDs via `concept_to_node_id`
- **Mechanical migration**: Automated rewrite of YAML weight keys following Section C.4 rules
- **Weight tuning**: Manual adjustment of YAML weights to correct behavioral drift post-migration
- **Jaccard similarity**: Intersection-over-union metric for node coverage overlap
