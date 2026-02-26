# Testing Synthesis Report: Signal-Strategy Scoring System

**Date:** 2026-02-26
**Scope:** 16 simulation runs across 5 methodologies, 8 personas, 3 testing tiers
**Overall results:** 14 PASS, 1 PARTIAL PASS, 1 FAIL

---

## Part 1: Fine-Tuning Recommendations

Concrete YAML weight changes to address known issues. All changes are "cosmetic" — no architecture or Python code modifications.

### 1.1 CJM `compare_expectations` Rotation Fix (Run 15 — blocking)

**Problem:** 9 consecutive turns of `compare_expectations` with `single_topic_fixator`. Worst rotation across all 16 runs.

**Root cause:** `compare_expectations` accumulates a high base score from multiple independent signals (certainty.high: 0.5, specificity.high: 0.4, intellectual_engagement.high: 0.4, response_depth: 0.3, engagement: 0.3) while the repetition penalty (-0.7) is insufficient to overcome this ~2.0+ ceiling. The fixator persona produces stable high-quality signals every turn, so the penalty never catches up.

**Fix:** Apply the same calibration principle that resolved ST1 (`clarify_assumption`) and Run 6 (`revitalize`):

| Weight | Current | Proposed | Rationale |
|--------|---------|----------|-----------|
| `temporal.strategy_repetition_count` | -0.7 | -1.5 | Penalty ≥ 0.85× ceiling base score (~2.0) |
| `temporal.strategy_repetition_count.high` | -0.3 | -0.8 | Escalating penalty for 3+ consecutive |

This is a proven pattern — the exact same fix worked for JTBD's `clarify_assumption` (ST1) and `revitalize` (Run 6).

### 1.2 MEC `deepen` Repetition Penalty (Run 7 — non-blocking)

**Problem:** Max consecutive = 5, down from 7 after chain_completion fix but still above the >4 threshold.

**Fix:**

| Weight | Current | Proposed | Rationale |
|--------|---------|----------|-----------|
| `temporal.strategy_repetition_count` | -0.3 | -0.7 | Align with JTBD's dig_motivation penalty |

This is conservative — MEC's laddering nature means 3-4 consecutive `deepen` turns are expected. The goal is to cap at 4, not eliminate dominance.

### 1.3 CIT `explore_emotions` Underfiring (Run 8 — non-blocking)

**Problem:** Only 1/10 turns despite `emotionally_reactive` persona producing valence=0.0 throughout. `probe_attributions` outcompetes because it has more signal triggers.

**Fix:**

| Weight | Current | Proposed | Rationale |
|--------|---------|----------|-----------|
| `explore_emotions.llm.valence.low` | 0.7 | 0.9 | Stronger differentiation at extreme negative valence |
| `explore_emotions.llm.valence.high` | 0.7 | 0.9 | Symmetrically boost extreme positive valence |

This gives `explore_emotions` a 0.2-point advantage over `probe_attributions` (which has `llm.valence.low: 0.5`) when valence is extreme, without affecting non-extreme turns.

### 1.4 Summary of All Fine-Tuning Changes

| Methodology | Strategy | Change | Priority |
|-------------|----------|--------|----------|
| CJM | `compare_expectations` | repetition -0.7→-1.5, .high -0.3→-0.8 | **Blocking** |
| MEC | `deepen` | repetition -0.3→-0.7 | Non-blocking |
| CIT | `explore_emotions` | valence.low/high 0.7→0.9 | Non-blocking |

---

## Part 2: Enhancement and Optimization Recommendations

Structural improvements to signal and strategy composition that would improve system behavior beyond fine-tuning. These require design decisions, not just weight changes.

### 2.1 Node-Level Signal Coverage Gap

**Observation:** Methodologies with richer node-level signals in their strategy weights produce better rotation. JTBD (7+ node-level weights per strategy) handles fixation well; CJM (3-4 node-level weights) does not.

**Evidence:**
- Run 11 (JTBD × fixator): 4 unique strategies, max consecutive = 3, 3 distinct focus nodes
- Run 15 (CJM × fixator): 2 unique strategies, max consecutive = 9, effectively no rotation
- Run 13 (MEC × brief): 2 unique strategies — MEC also has fewer node-level weights

**Recommendation:** Audit all methodologies for node-level signal coverage. Ensure every mid-phase strategy has at minimum:
- `graph.node.exhaustion_score.low` (positive, encourage fresh nodes)
- `graph.node.focus_streak.medium` (negative, penalize staleness)
- `graph.node.focus_streak.high` (stronger negative)

CJM's `compare_expectations` already has these but the weights are moderate (-0.4/-0.7). The issue is that its many positive global signals (~2.0 ceiling) overwhelm the node-level penalties. Two complementary approaches:

**Option A — Increase node-level penalty weights.** Raise `focus_streak.high` from -0.7 to -1.2 for CJM strategies. This directly addresses the fixation problem but doesn't change the fundamental global/node signal balance.

**Option B — Add `graph.node.yield_stagnation` to CJM.** Currently only MEC's `explore` uses this signal. Adding `graph.node.yield_stagnation.true: -0.6` to `compare_expectations` would penalize the strategy when a node stops producing new extraction. The fixator in Run 15 produced new content every turn (64 nodes), so this alone wouldn't fix Run 15 — but it would help in real interviews where fixation genuinely stalls extraction.

### 2.2 Missing Signal: Topic Diversity Detector

**Observation:** The system has no signal for "the respondent keeps returning to the same semantic territory." The fixator persona in Run 15 produced 64 nodes — the system saw high extraction yield and had no signal to indicate that these 64 nodes all clustered around "expectations vs reality."

**Current signals detect:**
- Engagement decline (llm.engagement) — fixator stays engaged
- Response depth decline (llm.response_depth) — fixator gives deep answers
- Node exhaustion (graph.node.exhaustion_score) — works per-node but the fixator generates new nodes each turn
- Saturation (meta.conversation.saturation) — never triggers because new nodes keep appearing

**Gap:** No signal detects *semantic clustering* — that all new content falls within a narrow semantic region despite being superficially novel.

**Possible implementation:** A new `graph.semantic_diversity` signal that measures the average pairwise embedding distance of nodes extracted in the last N turns. When this drops below a threshold, it signals thematic fixation even if node count is growing. This would require:
- Computing embeddings (already available — nodes have `embedding BLOB` in schema)
- A new signal detector in `src/signals/graph/`
- Weights in methodology YAMLs

This is a meaningful enhancement but requires architecture work (new signal detector class + registration).

### 2.3 Strategy Composition: Missing Breadth-Forcing Mechanisms

**Observation:** Each methodology has a "deepening" strategy that dominates mid-phase: `dig_motivation` (JTBD), `deepen` (MEC), `probe_attributions` (CIT), `ladder_constructs` (RG), `compare_expectations` (CJM). This is correct — mid-phase should deepen. But the system lacks a consistent mechanism to *force breadth* when deepening has stalled.

**Current breadth mechanisms per methodology:**

| Methodology | Breadth Strategy | Trigger | Effectiveness |
|-------------|-----------------|---------|---------------|
| JTBD | `explore_situation` | Low certainty, early phase | Good — fires in early phase |
| MEC | `explore` | Low certainty, repetition penalty | Weak — rarely beats `deepen` |
| CIT | `deepen_narrative` | Early phase | OK but not a true breadth strategy |
| RG | `explore_constructs` | Low specificity | OK — fires when hedger is vague |
| CJM | `explore_touchpoint` | Low certainty | Weak — `compare_expectations` blocks it |

**Recommendation:** Ensure each methodology has at least one strategy with:
- Strong `temporal.turns_since_strategy_change` weight (fires when any strategy has run too long)
- `meta.conversation.saturation` weight (fires when extraction yield is declining)
- Weak dependence on respondent quality signals (so it can fire even with cooperative/engaged respondents)

`revitalize` partially serves this role but it's designed for *disengagement recovery*, not *breadth forcing*. A methodology-specific "pivot" strategy that fires on strategic staleness (not engagement decline) would be more targeted.

### 2.4 Phase Bonus Interaction with Structural Signals

**Observation (Calibration Principle #4):** Phase bonuses compound with structural signal advantages. When a strategy has both a persistent structural signal (like `chain_completion`) AND a phase multiplier (1.3×), the combined advantage becomes unrecoverable for competitors.

**Recommendation:** Consider adding a rule to the scoring logic: if a strategy's base score includes contributions from persistent/binary signals (weight > 0.3 from any single `graph.*` signal), reduce its phase multiplier by a dampening factor (e.g., 0.8×). This would require a small code change in `src/methodologies/scoring.py` to detect structural signal contributions during scoring.

Alternatively, this can be handled purely through YAML discipline: never assign both a high structural signal weight AND a high phase multiplier to the same strategy. Document this as a calibration guideline.

### 2.5 Revitalize Strategy Generalization

**Observation (Runs 10, 16):** `revitalize` behaves differently per methodology — CJM uses it for journey-section shifting, CIT for within-incident re-engagement. But both use the same generic mechanism (shift to fresh topic). CIT could benefit from an incident-switching variant.

**Recommendation:** For CIT specifically, add a `revitalize`-adjacent signal weight:
- `meta.node.opportunity.exhausted: 0.5` — when current incident's attribution chain is complete, boost `elicit_incident` to compete with `revitalize`. This would let the system shift to a *new incident* rather than just re-engaging on the current one.

This is a YAML-only change (add weight to `elicit_incident`), not a new strategy.

---

## Part 3: Inherent Limitations

Structural constraints of the 2-stage scoring architecture that cannot be resolved through weight tuning alone.

### 3.1 The Global-Signal-Dominance Problem

**The fundamental tension:** Stage 1 selects strategy using *global* signals (engagement, depth, certainty — averaged across the entire response). Stage 2 selects the best *node* for that strategy. This means:

- A strategy's global score is determined by *response-level* quality signals
- Node-level signals can only influence *which node* is selected, not *which strategy* wins
- When a persona produces uniformly high (or uniformly low) quality signals, Stage 1 collapses to a single dominant strategy because there's no signal variance to differentiate competitors

**Where this breaks down:**
- `single_topic_fixator`: High engagement + high certainty + deep responses → `compare_expectations` wins every turn because global signals are consistently favorable. Node-level exhaustion can rotate *nodes* but cannot override the strategy selection.
- `brief_responder`: Low engagement across all turns → `revitalize` wins every turn because no other strategy accumulates positive signal scores.

**Why this can't be fully fixed with weights:** The 2-stage architecture structurally separates strategy selection from node selection. Adding node-level signals to Stage 1 would violate the architecture's clean separation. The only levers available in Stage 1 are: global signal weights, phase multipliers/bonuses, and temporal penalties (repetition count, turns since change). When a persona produces flat global signals, these levers lose their discriminating power.

**Practical impact:** For ~80% of respondents (who produce variable signal profiles), the system works well — natural signal variance drives strategy rotation. For the ~20% extreme personas (persistently disengaged, persistently fixated, persistently uncertain), the system converges on a single dominant strategy because there's no signal variance to exploit.

### 3.2 The Repetition Penalty Ceiling

**The pattern:** Every single strategy rotation fix across all 16 runs used the same mechanism — increasing `temporal.strategy_repetition_count` penalty. ST1 fixed `clarify_assumption` (-0.7→-1.5), Run 6 fixed `revitalize` (-0.7→-1.5), Run 15 needs the same fix for `compare_expectations`.

**The limitation:** Repetition penalties are linear and additive. A strategy at repetition count 3 gets 3× the penalty weight. But strategies with high base scores (>2.0) need penalties of -1.5 or more to break dominance — which means after just 2 repetitions, the penalty (-3.0) exceeds the base score. This creates a binary oscillation: the strategy either wins overwhelmingly or is completely suppressed.

**The implication:** The system cannot produce a "gentle preference for variety." It either dominates or is killed by the penalty. This is why:
- Run 6 (JTBD × brief) oscillates between `revitalize` and `uncover_obstacles` rather than smoothly rotating through all 7 strategies
- Run 15 (CJM × fixator) runs 9 straight before any competition emerges

A non-linear (decaying or sigmoidal) repetition penalty would produce smoother rotation, but this requires a code change to the scoring function — not a YAML weight adjustment.

### 3.3 The Persona-Methodology Compatibility Matrix

**Not all persona-methodology pairings can produce good interviews.** This is not a system failure — it's a domain reality.

| Persona Type | Strong With | Weak With | Reason |
|-------------|------------|-----------|--------|
| brief_responder | JTBD (7 strategies) | MEC (5 strategies, 10 nodes extracted) | MEC needs elaboration to build chains; brief answers starve it |
| single_topic_fixator | JTBD (node-level rotation) | CJM (global signal dominance) | CJM needs journey breadth; fixator prevents horizontal exploration |
| fatiguing_responder | CJM (graceful degradation) | Any (rich content declines after T5) | All methodologies lose signal quality; system can only validate + close |
| uncertain_hedger | RG (validates uncertainty) | MEC (needs confident attribute claims) | MEC's laddering requires "why does X matter?" which hedgers can't answer decisively |

**The implication:** No single weight configuration can make all 5 methodologies work optimally with all 8 personas. The system should be evaluated on *average performance across realistic respondent distributions*, not on worst-case persona-methodology pairings. A real interview population will rarely produce pure brief_responders or pure fixators — these are stress-test extremes.

### 3.4 Signal Detection Is Quality-Oriented, Not Content-Oriented

**The LLM signal detector rates response *quality* (engagement, depth, specificity) but not response *content* (topic relevance, semantic novelty, thematic diversity).** This is by design — content analysis would require methodology-specific prompt engineering — but it creates blind spots:

- `verbose_tangential` (Run 7): High quality scores (engagement=1.0, depth=deep) despite tangential content. System sees quality, not focus.
- `single_topic_fixator` (Run 15): High quality scores despite thematic repetition. System sees deep answers, not topic monotony.
- `emotionally_reactive` (Run 8): System detects low valence but doesn't assess whether emotional content is productive or circular.

**The implication:** Strategies that should trigger on *content problems* (off-topic, circular, repetitive themes) cannot fire because no content-analysis signal exists. The `graph.semantic_diversity` signal proposed in §2.2 would partially address this, but it operates on extracted nodes (post-extraction), not on the raw response (pre-extraction). A true content-oriented signal would need a dedicated LLM evaluation pass, adding latency and cost.

### 3.5 The 10-Turn Interview Horizon

**All tests used 10 turns.** Several findings are directly shaped by this constraint:

- MEC never reaches terminal values (needs 12-15 turns)
- Late-phase strategies only get 2-3 turns before cutoff
- Fatigue detection (3-turn rolling window) can only detect fatigue at T4+ and respond at T6+, leaving only 4 turns for recovery/validation
- Strategy rotation metrics (unique strategies, max consecutive) are evaluated over a short horizon where early dominance weighs heavily

**The implication:** Some "failures" would self-correct with longer interviews. MEC's `deepen` dominance at 5 consecutive turns is more concerning in a 10-turn interview (50%) than in a 15-turn interview (33%). The system's performance should be re-evaluated at 15-turn and 20-turn horizons for methodologies that require deeper exploration (MEC, RG).

### 3.6 The Phase Boundary Rigidity

**Phase transitions are turn-count-based (early < 2-4, mid < 8-12, late thereafter), not content-based.** This means:

- A brief_responder enters "late phase" at the same turn as a verbose respondent, despite having extracted 17 nodes vs 58
- A fixator who has barely explored breadth enters "late phase" and gets channeled toward validation/reflection
- Fatiguing respondents who are exhausted by T5 still have 3+ mid-phase turns before late-phase validation kicks in

**The implication:** Phase transitions should ideally consider graph state (node count, coverage, saturation) in addition to turn count. A respondent who has produced 60 nodes in 5 turns might be ready for late-phase validation, while one with 10 nodes needs more mid-phase exploration. This would require modifying the `InterviewPhaseSignal` detector to incorporate graph metrics — a meaningful architecture change.

---

## Summary

### What works well (no changes needed)
- Methodology isolation (zero cross-contamination in Tier 3)
- Late-phase convergence (all methodologies wrap up correctly)
- Safety mechanisms (late-stage gate, fatigue detection, revitalize)
- Persona-strategy alignment (emergent, not engineered)
- Node-level exhaustion and rotation (JTBD, RG)
- Graph enrichment from diverse personas

### What needs weight tuning (YAML-only)
1. CJM `compare_expectations` repetition penalty (blocking)
2. MEC `deepen` repetition penalty (non-blocking)
3. CIT `explore_emotions` valence weights (non-blocking)

### What needs design work (code changes)
1. Semantic diversity signal (§2.2) — detects thematic fixation
2. Non-linear repetition penalty (§3.2) — smoother rotation
3. Content-aware phase transitions (§3.6) — graph-state-based phases

### What cannot be fixed (inherent limitations)
1. Extreme personas (pure fixators, pure brief_responders) will always converge to 1-2 dominant strategies due to flat global signal profiles
2. Quality-oriented signals cannot detect content problems (tangential, circular, thematic repetition)
3. The 2-stage architecture structurally separates strategy and node selection — node-level diversity cannot override a bad strategy choice
