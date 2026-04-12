# Post-Scoring-Change Tidy-Up & Testing Plan

**Created**: 2026-04-12  
**Context**: Chain-aware architecture (P2/P3) merged — MEC now uses 6 strategies with `valid_when` gates and `score_threshold` fallback. Legacy strategies removed.

---

## Phase 1: Lock Down What Changed

- [x] Run `uv run python scripts/check_doc_drift.py` — note all stale docs
- [x] Update `docs/SYSTEM_DESIGN.md` to reflect:
  - `valid_when` gate mechanism
  - 6 MEC strategies replacing legacy ones (ascend, ground, bridge, branch, anchor, revitalize)
  - `score_threshold` fallback to conversation-level strategies
  - Chain completion scoring
- [x] Verify `.claude/context/strategy-scoring.md` is current
- [x] Verify `.claude/context/strategy-selection.md` is current

**Log:**

### Doc Drift Baseline (2026-04-12)
`check_doc_drift.py` returned zero warnings — no timestamp-based drift detected. Cross-reference validation also clean.

### `strategy-scoring.md` — CURRENT, no changes needed
Already covers: `valid_when` gates, 6 MEC strategies, score threshold fallback, chain topology signals, legacy strategy removal.

### `strategy-selection.md` — CURRENT, no changes needed
Already covers: D2 two-stage selection, `valid_when` gate, phase weights, post-selection ordering.

### `SYSTEM_DESIGN.md` — 3 issues found and fixed

**Issue A (YAML example, lines 299–319)**: Example showed legacy strategy names (`deepen`, `explore`, `reflect`) in strategies section and phases block. Replaced with chain-aware strategies (`ascend`, `branch`, `ground`), added `valid_when: graph.node.gap_above` to example strategy, and added `chain_completion:` config block with `score_threshold: 0.15`.

**Issue B (Strategy Selection Flow, lines 324–331)**: Described old D1 flow as a simple 6-step numbered list calling `select_strategy_and_focus()`. Rewrote to explicitly describe the two sub-stages: Stage 1 `rank_strategies()` (global signals only), Stage 2 `rank_strategy_node_pairs()` (joint scoring with `valid_when` filtering). Added `score_threshold` fallback as step 6.

**Issue C (missing content)**: No mention of chain-aware strategies, `valid_when` gates, or score threshold fallback anywhere in the doc. Added "Chain-Aware Strategies (MEC)" subsection under "Signal Pools Architecture" with:
- 6-strategy table with `valid_when` gates
- Legacy strategy removal note
- Score threshold fallback description
- Non-MEC methodology isolation note

### Post-fix drift check: CLEAN
Re-ran `check_doc_drift.py` after all edits — zero warnings.

---

## Phase 2: Methodology Inventory & Quality Review

For each active methodology, three questions:
1. **Does the baseline schema work?** — strategy composition is methodologically correct, weights produce sensible selection
2. **Does the interview feel natural?** — questions read like a skilled practitioner, flow is coherent, not mechanical
3. **What meaningful variants could be introduced?** — flavors with distinct research purpose, not just parameter tweaking

### How to evaluate

Run each methodology with `baseline_cooperative` (10–12 turns), then read the transcript and score:

| Criterion | Question |
|-----------|----------|
| **Strategy composition** | Are the strategy names and `valid_when` gates grounded in the methodology's actual logic? Is anything missing or misnamed? |
| **Weight calibration** | Do phase weights shift selection the right way across early/mid/late? Are any weights so dominant that they crowd out meaningful diversity? |
| **Naturalness** | Do the questions sound like a skilled human interviewer? Or mechanical/formulaic? |
| **Methodology fidelity** | Does the interview follow the methodology's logic? (MEC: laddering up; CIT: narrative arc; RG: triadic elicitation; CJM: journey breadth first) |
| **Flow coherence** | Does each question feel like it follows from the previous answer, or does it feel like a non-sequitur? |

---

### means_end_chain.yaml (baseline)

**Strategies** (6): `ascend`, `ground`, `bridge`, `branch`, `anchor`, `revitalize`  
All 5 structural strategies have `valid_when` gates tied to node topology signals.

- [ ] Run: `uv run python scripts/run_simulation.py glp1_food_mec baseline_cooperative 12`
- [ ] Strategy composition: are all 6 semantically correct for MEC? Anything missing (e.g., a strategy for over-abstract answers that need grounding in concrete attributes)?
- [ ] Weight calibration: do phase weights shift from attribute-building (early) → chain-ascending (mid) → value-synthesis (late)?
- [ ] Gate check: terminal nodes never scored `ascend`; orphan nodes trigger `anchor`
- [ ] Score threshold fallback: `revitalize` fires when chain completion is low
- [ ] Naturalness: questions sound like laddering, not a generic interview
- [ ] Flow coherence: questions build on prior answers, not non-sequiturs

**Current variants**: `means_end_chain_v2_strict.yaml`, `means_end_chain_v3_flex.yaml`
- [ ] Run strict vs flex on same concept, compare transcripts
- [ ] Decision: which variant(s) ship as production?

**Variant ideas:**
- `emotional_priority` — weight psychosocial/value levels higher from mid-phase (for brand/identity research)
- `attribute_depth` — linger at attribute level longer, building a wide base before ascending (for product design)

**Log:**

---

### jobs_to_be_done.yaml / jobs_to_be_done_v2.yaml

**Strategies** (7): `explore_situation`, `probe_alternatives`, `dig_motivation`, `validate_outcome`, `revitalize`, `uncover_obstacles`, `clarify_assumption`  
No `valid_when` gates — all strategies compete on weights alone, no structural filtering.

- [ ] Run: `uv run python scripts/run_simulation.py glp1_food_jtbd baseline_cooperative 10`
- [ ] Run: `uv run python scripts/run_simulation.py coffee_jtbd_v2 baseline_cooperative 10`
- [ ] Strategy composition: does the set cover the JTBD interview arc? Missing: hire/fire trigger strategy, social job probing, progress narrative. Evaluate whether `dig_motivation` is doing too much work.
- [ ] Weight calibration: do weights shift from situation-mapping (early) → job-probing (mid) → validation/insight (late)?
- [ ] Consider: would `valid_when` gates improve selection? (e.g., `probe_alternatives` only when a job_statement exists)
- [ ] Naturalness: questions feel like JTBD practitioner, not generic "tell me more"
- [ ] Check `docs/drafts/jtbd_v3_implementation_spec.md` — is v3 ready to promote?

**Variant ideas:**
- `switch_interview` — emphasize hire/fire triggers, timeline of switch, push/pull forces
- `outcome_driven` — focus on measuring importance × satisfaction gaps across outcomes
- `progress_narrative` — focus on what progress the job enables, not just the job itself

**Log:**

---

### critical_incident.yaml

**Strategies** (7): `elicit_incident`, `deepen_narrative`, `explore_emotions`, `probe_attributions`, `extract_insights`, `revitalize`, `validate`  
No `valid_when` gates — all compete on weights alone.

- [ ] Run: `uv run python scripts/run_simulation.py <CIT concept> baseline_cooperative 10`  
  *(create concept first — see Phase 3)*
- [ ] Strategy composition: does the arc follow CIT logic? `elicit_incident` should dominate early, `deepen_narrative` mid, `probe_attributions`/`extract_insights` late. Check whether `validate` fires appropriately (late phase, uncertain statements).
- [ ] Weight calibration: early phase should strongly favor `elicit_incident` — does it?
- [ ] Consider: `valid_when` gate for `probe_attributions` (only when an outcome node exists), `explore_emotions` (only when emotion node exists or valence detected)
- [ ] Narrative arc: interview has a story shape — elicit → deepen → reflect — not a flat list of probes
- [ ] Naturalness: questions invite storytelling, not facts

**Variant ideas:**
- `positive_only` — opening_bias and weights tuned for peak positive experiences (advocacy/NPS research)
- `negative_only` — opening_bias and weights tuned for failure/pain incidents (churn/complaints research)
- `comparison` — elicit a positive and negative incident, use late-phase contrast strategy

**Log:**

---

### customer_journey_mapping.yaml

**Strategies** (7): `map_journey`, `explore_touchpoint`, `probe_friction`, `track_emotions`, `compare_expectations`, `revitalize`, `validate`  
No `valid_when` gates — all compete on weights alone.

- [ ] Run: `uv run python scripts/run_simulation.py <CJM concept> baseline_cooperative 10`  
  *(create concept first — see Phase 3)*
- [ ] Strategy composition: does the set cover breadth-first journey mapping? `map_journey` should dominate early to establish stages before any touchpoint drilling. Check whether there's a gap: no strategy for surfacing `moment_of_truth` nodes explicitly.
- [ ] Weight calibration: early phase should strongly favor `map_journey` — does it avoid premature `explore_touchpoint` drilling?
- [ ] Consider: `valid_when` gate for `explore_touchpoint` (only when ≥1 stage node exists), `probe_friction` (only when a touchpoint is mapped)
- [ ] Breadth-first check: interview maps the full journey arc before deepening at any single stage
- [ ] Naturalness: questions feel like a journey walkthrough, not a topic-by-topic interrogation

**Variant ideas:**
- `emotion_led` — `track_emotions` weighted heavily throughout (service design, empathy mapping)
- `friction_led` — `probe_friction` weighted heavily from mid-phase (CX improvement, pain point research)
- `decision_led` — add a `probe_decisions` strategy for moment_of_truth nodes (conversion/switching research)

**Log:**

---

### repertory_grid.yaml

**Strategies** (7): `triadic_elicitation`, `explore_constructs`, `ladder_constructs`, `rate_elements`, `explore_ideal`, `revitalize`, `validate`  
No `valid_when` gates — all compete on weights alone.

- [ ] Run: `uv run python scripts/run_simulation.py <RG concept> baseline_cooperative 10`  
  *(create concept first — see Phase 3)*
- [ ] Strategy composition: does the arc follow RG logic? `triadic_elicitation` should dominate early to build the grid, `ladder_constructs` mid, `rate_elements`/`explore_ideal` late. Is there a gap: no explicit strategy for sorting/ranking constructs by importance?
- [ ] Weight calibration: early phase must favor `triadic_elicitation` — without it, no constructs to work with
- [ ] Consider: `valid_when` gate for `ladder_constructs` (only when ≥2 constructs exist), `rate_elements` (only when ≥2 elements and ≥1 construct exist)
- [ ] Triadic check: does the system actually introduce triadic comparisons ("of these three, which two are most similar?"), or does it devolve into direct questions?
- [ ] Naturalness: questions feel like construct elicitation, not preference questions

**Variant ideas:**
- `provided_elements` — researcher pre-specifies elements to compare rather than respondent-elicited (more consistent grids for quantitative follow-up)
- `laddered_grid` — hybrid RG+MEC: after construct elicitation, ladder up on the most personally important constructs

---

## Phase 3: Concept Coverage

**Required**: at least one concept per active methodology to run smoke tests.

| Methodology | Concept ID | Status |
|-------------|-----------|--------|
| MEC (baseline) | `glp1_food_mec` | exists |
| MEC strict | `glp1_food_mec_strict` | exists |
| MEC flex | `glp1_food_mec_flex` | exists |
| JTBD | `glp1_food_jtbd` | exists |
| JTBD v2 | `coffee_jtbd_v2`, `meal_planning_jtbd_v2` | exists |
| Critical Incident | — | missing |
| Customer Journey Mapping | — | missing |
| Repertory Grid | — | missing |

- [ ] Create concept config for Critical Incident methodology
- [ ] Create concept config for Customer Journey Mapping methodology
- [ ] Create concept config for Repertory Grid methodology
- [ ] Update CLAUDE.md valid concept IDs list

**Log:**

---

## Phase 4: Tiered Testing

### Tier 1 — Smoke Tests (one per methodology, baseline persona)

Goal: confirms the basic loop works — strategies fire, phases transition, interview completes.

| # | Concept | Persona | Turns | Status | Notes |
|---|---------|---------|-------|--------|-------|
| T1.1 | `glp1_food_mec` | baseline_cooperative | 12 | [ ] | |
| T1.2 | `glp1_food_jtbd` | baseline_cooperative | 10 | [ ] | |
| T1.3 | *(CIT concept)* | baseline_cooperative | 10 | [ ] | |
| T1.4 | *(RG concept)* | baseline_cooperative | 10 | [ ] | |
| T1.5 | *(CJM concept)* | baseline_cooperative | 10 | [ ] | |

---

### Tier 2 — Persona Stress Tests

Each persona represents a distinct behavioral edge case. The methodology is chosen to maximally expose the stress that persona creates.

| # | Concept | Persona | What this persona stresses | What to check | Status | Notes |
|---|---------|---------|--------------------------|---------------|--------|-------|
| T2.1 | `glp1_food_mec` | `brief_responder` | Low response depth → should trigger `ground` (fill gap below) or `anchor` (orphan nodes) | No chain laddering above L1 | [ ] | |
| T2.2 | `glp1_food_mec` | `verbose_tangential` | Noisy extraction → many orphan nodes → `anchor` should dominate | `anchor` fires; score_threshold fallback may suppress other strategies | [ ] | |
| T2.3 | `glp1_food_mec` | `single_topic_fixator` | Node exhaustion → focus_streak penalties → `bridge` or `branch` should force lateral moves | Node rotation — same node_id not selected >4 consecutive turns | [ ] | |
| T2.4 | `glp1_food_mec` | `skeptical_analyst` | Low engagement → engagement gate should suppress depth strategies | Engagement safety gate fires; strategies shift conservative | [ ] | |
| T2.5 | *(CIT concept)* | `emotionally_reactive` | High valence + emotional expression → emotion-targeting strategies should dominate | Emotion strategies fire; valence safety gates active | [ ] | |
| T2.6 | *(CIT concept)* | `retrospective_rationalizer` | Post-hoc reasoning instead of real incident recall → should probe for specificity | System probes for concrete detail, doesn't accept rationalization as incident | [ ] | |
| T2.7 | *(CJM concept)* | `fatiguing_responder` | Engagement drop mid-interview → `revitalize` should fire; journey mapping should shift sections | `revitalize` fires; interview doesn't stall at single journey stage | [ ] | |
| T2.8 | *(CJM concept)* | `uncertain_hedger` | Hedged answers → uncertainty signals → `validate` and confirming strategies | Hedging doesn't cause infinite clarification loops | [ ] | |
| T2.9 | `glp1_food_jtbd` | `brief_responder` | Compare with T2.1 — same persona, different methodology | JTBD and MEC should respond differently to brief answers | [ ] | |
| T2.10 | *(RG concept)* | `uncertain_hedger` | RG needs confident constructs — hedging should trigger construct validation | Triadic elicitation doesn't collapse; constructs still emerge | [ ] | |

---

### Tier 3 — Cross-Methodology Contrast (optional)

Same persona across methodologies — confirms methodology-specific weights produce meaningfully different selections.

| # | Concept A | Concept B | Persona | What to compare | Status | Notes |
|---|-----------|-----------|---------|-----------------|--------|-------|
| T3.1 | `glp1_food_mec` | `glp1_food_jtbd` | baseline_cooperative | Strategy distributions differ; MEC ladders, JTBD explores jobs | [ ] | |
| T3.2 | *(CIT concept)* | *(CJM concept)* | emotionally_reactive | CIT amplifies emotion; CJM keeps breadth despite emotional pressure | [ ] | |
| T3.3 | `glp1_food_mec_strict` | `glp1_food_mec_flex` | brief_responder | Strict vs flex diverge under sparse input | [ ] | |

---

## What to Check in Logs

| Check | Where to look | Red flag |
|-------|--------------|----------|
| Strategy diversity | Count distinct strategies across turns | Same strategy >3 turns in a row |
| `valid_when` gate | Strategy column — terminal nodes | `ascend` appearing on terminal nodes |
| Score threshold fallback | Strategy column — low chain completion turns | `revitalize` never fires when chain incomplete |
| Phase transitions | `meta.interview.phase` in signals | Stuck in early, or late phase too soon |
| Node rotation | `node_signals` field | Same node_id selected >4 consecutive turns |
| Score differentiation | `score_decomposition` | All strategies scoring within 0.1 of each other = weights too flat |
| Non-MEC contamination | Strategy names in non-MEC runs | `ascend`/`ground`/`bridge` appearing in JTBD/CJM/CIT/RG runs |
| Transcript naturalness | Read the question column | Questions sound mechanical, formulaic, or non-sequitur |

---

## Phase 5: Calibration Log

| Run | Issue observed | Change made | Result |
|-----|---------------|-------------|--------|
| | | | |

---

## Overall Progress

- [x] Persona reorganisation: `config/personas/edge_cases/` (8 behavioral stress personas) and `config/personas/domains/` (2 domain personas). Loader updated to `rglob`.
- [x] Phase 1: Docs updated
- [ ] Phase 2: All methodologies reviewed for quality + variant decisions made
- [ ] Phase 3: Concept coverage complete (CIT, CJM, RG concepts created)
- [ ] Phase 4 Tier 1: All smoke tests pass
- [ ] Phase 4 Tier 2: All persona stress tests pass
- [ ] Phase 4 Tier 3: Cross-methodology contrasts evaluated
- [ ] Phase 5: Weights calibrated, no red flags
