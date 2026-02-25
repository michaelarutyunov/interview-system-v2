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
