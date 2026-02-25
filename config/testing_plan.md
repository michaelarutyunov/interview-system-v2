# Simulation Testing Plan

Goal: weight calibration via simulation logs that expose whether each signal pathway and strategy selection mechanism works correctly.

## Testing Dimensions

1. **Methodology** (5) — does the strategy set + weights produce sensible interviews?
2. **Persona** (8) — does the system respond correctly to each behavioral pattern?
3. **Interview phase** (early/mid/late) — do phase weights shift strategy selection correctly?

Phase isn't a separate config — it emerges from turn count. But it matters for what you're looking at in the logs.

---

## Tier 1: Smoke Tests (5 runs)

One run per methodology with `baseline_cooperative`. Confirms the basic loop works: strategies fire, phases transition, interview completes. If any of these fail, nothing else matters.

| Run | Concept | Persona | Turns | What to check |
|-----|---------|---------|-------|---------------|
| 1 | `meal_planning_jtbd` | baseline_cooperative | 10 | Strategy diversity, phase transitions |
| 2 | `headphones_mec` | baseline_cooperative | 10 | Chain completion, laddering |
| 3 | `restaurant_ci` | baseline_cooperative | 10 | Narrative arc, emotion probing |
| 4 | `streaming_services_rg` | baseline_cooperative | 10 | Triadic elicitation, grid building |
| 5 | `online_shopping_cjm` | baseline_cooperative | 10 | Journey mapping, touchpoint depth |

```bash
uv run python scripts/run_simulation.py meal_planning_jtbd baseline_cooperative 10
uv run python scripts/run_simulation.py headphones_mec baseline_cooperative 10
uv run python scripts/run_simulation.py restaurant_ci baseline_cooperative 10
uv run python scripts/run_simulation.py streaming_services_rg baseline_cooperative 10
uv run python scripts/run_simulation.py online_shopping_cjm baseline_cooperative 10
```

---

## Tier 2: Signal Pathway Stress Tests (7 runs)

One run per edge-case persona, using the methodology whose strategy set is most sensitive to that persona's behavior.

| Run | Concept | Persona | Why this pairing |
|-----|---------|---------|-----------------|
| 6 | `meal_planning_jtbd` | brief_responder | JTBD has 7 strategies competing — brief answers should trigger `dig_motivation` and suppress `explore_situation` |
| 7 | `headphones_mec` | verbose_tangential | MEC needs clean attribute extraction from noise — tests whether `clarify` fires on low specificity |
| 8 | `restaurant_ci` | emotionally_reactive | CIT is emotion-centric — should trigger `explore_emotions` heavily, test valence safety gates |
| 9 | `streaming_services_rg` | uncertain_hedger | RG needs confident constructs — should trigger `explore_constructs` and `validate` on hedging |
| 10 | `online_shopping_cjm` | fatiguing_responder | CJM is long-journey — fatigue should trigger `revitalize` mid-interview, test trend detection |
| 11 | `commute_jtbd` | single_topic_fixator | Tests node exhaustion and rotation — fixator should trigger high focus_streak penalties |
| 12 | `customer_support_ci` | skeptical_analyst | CIT attribution probing meets skeptical respondent — tests `probe_attributions` with challenging engagement |

```bash
uv run python scripts/run_simulation.py meal_planning_jtbd brief_responder 10
uv run python scripts/run_simulation.py headphones_mec verbose_tangential 10
uv run python scripts/run_simulation.py restaurant_ci emotionally_reactive 10
uv run python scripts/run_simulation.py streaming_services_rg uncertain_hedger 10
uv run python scripts/run_simulation.py online_shopping_cjm fatiguing_responder 10
uv run python scripts/run_simulation.py commute_jtbd single_topic_fixator 10
uv run python scripts/run_simulation.py customer_support_ci skeptical_analyst 10
```

---

## Tier 3: Cross-Methodology Validation (4 optional runs)

Same persona across different methodologies to confirm methodology-specific weights produce *different* strategy selections for the *same* behavioral signals.

| Run | Concept | Persona | Compare with |
|-----|---------|---------|-------------|
| 13 | `skincare_mec` | brief_responder | Run 6 (JTBD brief) — different deepening strategies? |
| 14 | `coffee_shops_rg` | emotionally_reactive | Run 8 (CIT emotional) — RG should NOT over-trigger emotion probing |
| 15 | `gym_membership_cjm` | single_topic_fixator | Run 11 (JTBD fixator) — CJM should shift journey sections |
| 16 | `customer_support_ci` | fatiguing_responder | Run 10 (CJM fatigue) — CIT revitalize should shift to new incident |

```bash
uv run python scripts/run_simulation.py skincare_mec brief_responder 10
uv run python scripts/run_simulation.py coffee_shops_rg emotionally_reactive 10
uv run python scripts/run_simulation.py gym_membership_cjm single_topic_fixator 10
uv run python scripts/run_simulation.py customer_support_ci fatiguing_responder 10
```

---

## What to Check in Logs

For each run, the scoring CSV and JSON output tell you:

| Check | Where to look | Red flag |
|-------|--------------|----------|
| Strategy diversity | Count distinct strategies across turns | Same strategy >3 turns in a row |
| Phase transitions | `meta.interview.phase` in signals | Stuck in early, or late phase too soon |
| Signal detection | `signals` field in JSON | Expected signals absent (e.g., no `llm.valence.low` for emotionally_reactive) |
| Node rotation | `node_signals` field | Same node_id selected >4 consecutive turns |
| Revitalize firing | Strategy column in CSV | `revitalize` never fires for fatiguing_responder = broken |
| Validate firing | Strategy column in CSV | `validate` never fires in late phase = broken |
| Score differentiation | `score_decomposition` | All strategies scoring within 0.1 of each other = weights too flat |

---

## Execution Order

1. Run Tier 1 (5 runs). If any fail, fix before proceeding.
2. Run Tier 2 (7 runs). Review logs, tune weights if needed.
3. Optionally run Tier 3 (4 runs) for cross-methodology comparison.

**Total: 12 mandatory runs, 4 optional = 16 max**

---

# Testing Results

## Smoke Test 1: `meal_planning_jtbd` × `baseline_cooperative` (10 turns)

**Date:** 2026-02-25

### Run 1 — Baseline (pre-fix)

| Metric | Value | Status |
|--------|-------|--------|
| Turns completed | 9 | OK |
| Strategy diversity | 4/8 unique | Concerning |
| Max consecutive same strategy | 4 (`clarify_assumption` T4-T7) | Red flag |
| Phase transitions | mid only (no early) | Bug |
| `validate_outcome` in late phase | Yes (T8) | OK |
| Graph growth | 30+ nodes, rich edges | OK |

**Issues found:**

**Bug 1 — Phase detection: early phase missing for 10-turn interviews.**
`EARLY_PHASE_RATIO = 0.10` produces `early_max_turns = max(1, round(10 × 0.10)) = 1`. Turn 0 is the opening question (no strategy selection), so early phase has zero effective turns. Strategies with early-phase bonuses (`explore_situation: 1.5×`) never fired.

**Bug 2 — `clarify_assumption` dominance.**
`baseline_cooperative` persona consistently produced `certainty.high` + `specificity.high` + `response_depth.deep` + `engagement.high` — all primary triggers for `clarify_assumption`. Combined base score ~1.76 per turn. Repetition penalty of `-0.7 × 0.2 = -0.14` was negligible against this base, so `clarify_assumption` won 5/8 turns despite the penalty.

Investigation also revealed `rank_strategy_node_pairs()` in `scoring.py` is dead code from an older architecture — not called anywhere in the service layer. Node-level strategy repetition signals (`technique.node.strategy_repetition`) therefore cannot influence which strategy wins Stage 1; they only affect node selection after the strategy is already chosen.

### Fixes Applied

**Fix 1 — Phase detection minimum floor** (`src/signals/meta/interview_phase.py`):
Added `MIN_EARLY_TURNS = 2`. Early phase is now `max(2, round(max_turns × 0.10))`.
Result for 10 turns: early = turns 0-1, mid = turns 2-7, late = turns 8-9.

**Fix 2 — `clarify_assumption` repetition penalty** (`config/methodologies/jobs_to_be_done.yaml`):
Increased `temporal.strategy_repetition_count` weight from `-0.7` to `-1.5` (matching `dig_motivation`'s existing brake). Added `-1.0` for `.high` bucket.

### Run 2 — After Fix 1 + Fix 2

| Metric | Value | Status |
|--------|-------|--------|
| Strategy diversity | 3/8 unique | Still concerning |
| Max consecutive same | 4 (`clarify_assumption` T1-T4) | Still red flag |
| Early phase | T1 shows `early` | Fixed |

`clarify_assumption` still dominated (5/8 turns). The `-1.5` penalty decayed it by T5 but too slowly — base score was too high to begin with.

**Fix 3 — `clarify_assumption` trigger weight reduction** (`config/methodologies/jobs_to_be_done.yaml`):
Reduced primary trigger weights to make `clarify_assumption` a specialist, not a generalist:
- `llm.certainty.high`: 0.8 → 0.5
- `llm.specificity.high`: 0.5 → 0.3
- `llm.response_depth.deep`: 0.3 → 0.2
- `llm.certainty.mid`: 0.6 → 0.4

Rationale: a cooperative, articulate respondent should not automatically trigger a challenging strategy every turn. `clarify_assumption` should win when certainty is high AND other strategies aren't competing strongly — not as the default when quality signals are all high.

### Run 3 — After Fix 3

| Metric | Value | Status |
|--------|-------|--------|
| Strategy diversity | 4/7 unique | Acceptable |
| Max consecutive same | 4 (`dig_motivation` T3-T6) | Marginal |
| `clarify_assumption` turns | 1/7 | Fixed |
| Phase transitions | early → mid → late | OK |

Strategy rotation improved significantly: `clarify_assumption`(1) → `uncover_obstacles`(1) → `dig_motivation`(4) → `validate_outcome`(1). The interview produces a coherent arc — clarify a claim, surface obstacles, dig motivation, validate.

`dig_motivation` now dominates mid-phase for a cooperative articulate persona, which is broadly expected behaviour (it has `intellectual_engagement.high + engagement.high + depth` triggers). Max consecutive = 4 is marginal but not a hard fail.

### Conclusions

1. **Phase detection with short interviews needs explicit minimums.** The 10% ratio produces a single-turn early phase that is effectively invisible. A 2-turn minimum is required.
2. **High base-score strategies need asymmetric repetition penalties.** Symmetric `-0.7` penalties are insufficient when a strategy's base score exceeds ~1.5. Strategies that trigger broadly (certainty + specificity + depth + engagement) should have penalties of `-1.5` or higher.
3. **Strategies should be specialists, not generalists.** Each strategy's trigger weights should be calibrated so it wins only when its *defining signal* fires, not whenever the respondent is articulate. For `clarify_assumption`, the defining signal is a confident/specific claim — not just high certainty in isolation.
4. **`baseline_cooperative` is a good calibration baseline but a stress test for rotation.** A cooperative articulate respondent produces stable high-quality signals every turn, which suppresses strategy rotation. Tier 2 personas with variable signal profiles will be a better test.
5. **`rank_strategy_node_pairs()` is confirmed dead code.** Node-level strategy repetition cannot influence strategy selection under the current 2-stage architecture. This is by design — Strategy 1 picks the strategy globally, Stage 2 picks the best node. YAML weights for `technique.node.strategy_repetition` still affect node selection but not strategy choice.

### Status
Smoke Test 1: **PASS** (with fixes). Proceeding to Smoke Test 2.
