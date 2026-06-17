# Signal Optimization Report

**Date:** 2026-03-05
**Data:** 23 simulations across 5 methodologies, 5 personas, ~219 scored turns
**Tools:** `signal_importance.py` (observational pruning) + `sensitivity_analysis.py` (decision impact)

---

## Summary

| Methodology | Signals | Prunable (Approach 1) | Load-bearing | Safe to Remove |
|---|---|---|---|---|
| means_end_chain | 24 | 13 (54%) | 22 | ~3 |
| jobs_to_be_done | 37 | 15 (41%) | 34 | ~2 |
| critical_incident | 33 | 11 (33%) | 13 | ~2 |
| customer_journey_mapping | 36 | 16 (44%) | 30 | ~4 |
| repertory_grid | 32 | 12 (38%) | 30 | ~1 |
| **Total** | **162** | **67 (41%)** | — | **~12** |

---

## Key Finding: The CONSTANT Paradox

Approach 1 (observational) classified ~43 signals as **CONSTANT** — contributing identically across all strategies within a turn. The naive interpretation is that these are safe to remove. Approach 2 (sensitivity) contradicts this for most of them: **many CONSTANT signals are highly load-bearing**, flipping strategy selection in 10–70% of turns when removed.

**Why:** A signal can be constant *within* the strategies that configure it, yet still discriminate *between* strategies — because some strategies simply don't include it in their weight table. Removing the signal removes its contribution only from strategies that have it, breaking the relative ranking with those that don't.

**Implication:** CONSTANT classification alone is not sufficient to justify pruning. You need both approaches in conjunction.

---

## Findings by Signal Category

### 1. Dead Signals — Universally Safe to Remove

These never fire across any simulation. No decision impact whatsoever.

| Signal | Affected Methodologies | Notes |
|---|---|---|
| `graph.node.focus_streak.high` | CI, CJM, JTBD, MEC, RG | "High" streak threshold never reached in practice — likely set too aggressively |
| `graph.node.recency_score` | RG (configured but dead); decorative in all | Only signal decorative in **all** methodologies in sensitivity analysis |
| `graph.node.is_orphan.true` | CJM | Dead and decorative; orphan condition too rare for CJM concept types |
| `meta.conversation.saturation.high` | CJM, JTBD | Binary "high" threshold never triggered |

**Recommendation:** Remove these unconditionally. They add complexity with zero contribution.

---

### 2. Uniform Bias Signals — Remove or Differentiate

These fire consistently but contribute the same amount to every strategy that includes them. They shift all scores in lock-step and don't discriminate. **However:** if their weight differs across strategies (or some strategies lack them), they do affect rankings — the paradox above.

The signals below are CONSTANT *and* their flip patterns in sensitivity show they flip the same strategy repeatedly (i.e., they systematically favour one strategy over all others — a bias, not a discriminator):

| Signal | Observation | Recommendation |
|---|---|---|
| `llm.intellectual_engagement.high/mid` | CONSTANT in 4/5 methodologies; when it flips, it repeatedly shifts away from `probe_attributions`, `compare_expectations`, or `uncover_obstacles` | Either differentiate weights per strategy (higher weight for strategies that reward intellectual depth) or remove from strategies where it isn't semantically meaningful |
| `meta.canonical.saturation` (continuous) | CONSTANT everywhere; low values (0.01–0.20) dominate; continuous form barely moves the needle | Replace with the binary `.high` form only, where the threshold is actually meaningful |
| `temporal.turns_since_strategy_change` | CONSTANT in CI, MEC, CJM; penalizes the current strategy uniformly | Semantic concern: this should penalize the *same* strategy, not all strategies equally — the current implementation doesn't do what it intends |
| `graph.max_depth` | CONSTANT in CI, CJM, RG (same weight across strategies); flip rate 13–41% | Only semantically appropriate for strategies that are depth-sensitive (e.g., `deepen`, `reflect` in MEC). Should be removed from strategies where depth is irrelevant |

---

### 3. MEC-Specific Issues

MEC has the highest pruning rate (54%) but the analysis reveals a more fundamental issue:

**`llm.response_depth.high/low/mid` are completely dead in MEC.**
MEC uses `.moderate` as the category name, not `.high/.mid/.low`. This is a naming inconsistency between the MEC YAML and the LLM signal detector's output vocabulary. The signal fires — but under a different key that the YAML never looks for. **This means MEC's response-depth-based triggering is broken.** All response depth logic in MEC currently reads 0.

**`graph.chain_completion.has_complete.false`** is load-bearing (40% flip rate) and drives `deepen` strategy selection. This is semantically correct for MEC: an incomplete means-end chain should prompt deeper probing. Keep it.

---

### 4. Signals That Make Sense Semantically

The following signals are load-bearing and semantically coherent for their strategies:

**`llm.engagement` (high/low)** — Universal, flip rate 15–55%
Correctly drives strategy selection across all methodologies. Low engagement triggers `revitalize`/recovery strategies; high engagement enables depth-seeking strategies (`deepen`, `dig_motivation`, `probe_attributions`). This is the most reliable signal in the system.

**`llm.certainty` (all levels)** — Universal, flip rate 10–49%
High certainty in CI drives shift from `probe_attributions` → `explore_emotions` — semantically correct: when the respondent is confident about facts, move to emotional/evaluative territory. In JTBD, high certainty pushes toward `uncover_obstacles` — respondent knows their situation well, so structural barriers become the next frontier.

**`temporal.strategy_repetition_count`** — Active, flip rate 10–37%
Correctly penalises overuse of any single strategy. Most impactful in JTBD where it competes with the dominant `uncover_obstacles` gravity. However: note that `temporal.strategy_repetition_count.high` (the binary threshold form) has weight 0 in most configurations yet flips decisions — this suggests the continuous version absorbs all the signal and the threshold version is redundant.

**`graph.node.exhaustion_score.low`** — Active, moderate flip rate
Semantically correct: prefer fresh nodes for continued exploration. Appropriately used in all methodologies. Note: its low flip rate (~7–37%) reflects that it only affects node selection within a strategy, not the strategy choice itself — which is correct.

**`graph.node.focus_streak.none/medium`** — Active, moderate flip rate
`.none` (no recent focus on this node) correctly boosts node freshness. `.medium` (moderate streak) correctly penalises over-focus. Both are semantically sound. `.high` is dead (see above).

**`meta.interview.phase.early/mid`** (JTBD only) — 43–47% flip rate
Phase-gated strategy selection works as intended in JTBD. The reason these appear as CONSTANT in Approach 1 is that phase signals apply to strategy-level scoring but are excluded from node-pair scoring (by design). No issue here.

**`llm.global_response_trend.fatigued`** — Active, flip rate 5–45%
Correctly triggers recovery strategies (`revitalize`, `reflect`) when the respondent shows declining engagement. Especially important in JTBD. Dead in RG — possibly because fatiguing patterns don't manifest with the RG persona/concept combinations tested.

---

## Recommendations

### Immediate Pruning (Low Risk)

Remove without consequence — confirmed dead and decorative:

1. `graph.node.focus_streak.high` — remove from all 5 methodologies
2. `graph.node.recency_score` — remove from RG
3. `graph.node.is_orphan.true` — remove from CJM
4. `meta.conversation.saturation.high` — remove from CJM and JTBD

**Complexity reduction:** ~8 weight entries removed; no change in behaviour.

### Fix Before Pruning

5. **MEC response depth naming bug** — `llm.response_depth.high/low/mid` are dead because MEC YAML uses `.high/.mid/.low` but the detector emits `.surface/.shallow/.moderate/.deep`. Replace with correct category names in MEC. This will immediately activate the deepen/explore/clarify differentiation that was intended but non-functional.

### Design Improvements (Moderate Risk)

6. **`temporal.strategy_repetition_count.high`** — weight is 0 in most configurations but still fires. Remove the binary form everywhere; the continuous form is sufficient.

7. **`meta.canonical.saturation` (continuous)** — replace with `.high` binary form only. The continuous values are too small (max 0.20) to carry meaningful signal; the threshold form is more interpretable and shows cleaner flip patterns.

8. **`temporal.turns_since_strategy_change`** — review intent. Currently penalises all strategies equally when the current one has been used for many turns, which creates a uniform pressure rather than targeted rotation. Consider whether this should instead penalise only the currently-selected strategy (i.e., use `temporal.strategy_repetition_count` exclusively and remove this one).

9. **`graph.max_depth`** — currently assigned identical weight across all strategies in CI, CJM, RG (CONSTANT). This makes it a systematic bias rather than a discriminator. Either:
   - Give it higher weight for depth-sensitive strategies (`deepen_narrative`, `probe_attributions`) and lower/zero for surface strategies (`validate`, `revitalize`), or
   - Remove it from strategies where depth is not a selection criterion

10. **`llm.intellectual_engagement`** — similar to above. This signal makes strong semantic sense for strategies that reward analytical respondents (`probe_attributions`, `extract_insights`, `ladder_constructs`), but applying it uniformly across all strategies just inflates everyone's score equally. Differentiate weights or restrict to relevant strategies.

### Schema Complexity After Recommendations

If changes 1–10 are implemented:

| Methodology | Current entries | Estimated after | Reduction |
|---|---|---|---|
| means_end_chain | 24 | ~18 | 25% |
| jobs_to_be_done | 37 | ~28 | 24% |
| critical_incident | 33 | ~25 | 24% |
| customer_journey_mapping | 36 | ~26 | 28% |
| repertory_grid | 32 | ~26 | 19% |
| **Total** | **162** | **~123** | **~24%** |

The reduction is conservative because most of the improvement comes from fixing design issues (non-uniform weights, naming bug) rather than pure pruning.

---

## Data Limitations

Results are based on 23 simulations, predominantly `baseline_cooperative` and `brief_responder` personas. Edge-case personas (`emotionally_reactive`, `fatiguing_responder`) are underrepresented. Signals involving emotional responses (`llm.valence.low`, `llm.global_response_trend.fatigued`) may have understated importance. Recommend running 5–10 more simulations per methodology across diverse personas before acting on the moderate-risk recommendations.
