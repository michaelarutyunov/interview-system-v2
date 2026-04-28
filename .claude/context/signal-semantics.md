# Signal Semantics Catalog

> **Historical note:** This audit was conducted on 2026-04-17. A signal naming refactor (commit `e4030c4`, 2026-04-21) renamed all signals to a source-first namespace. Signal names in this document reflect the audit-era naming; the semantic assessments remain valid. For current names, see `docs/signals_moderator_guide.md`.
>
> Key renames since this audit:
> - `llm.*` (per-turn) → `response.semantic.llm.*`
> - `graph.*` (surface graph) → `convgraph.*`
> - `graph.canonical_*` → `canongraph.*`
> - `temporal.*` → `interview.strategy.*` / `interview.focus.*`
> - `meta.interview.phase` → `interview.phase`
> - `meta.conversation.saturation` → `meta.saturation.conversation`
> - `meta.canonical.saturation` → `meta.saturation.canonical`

> **Purpose:** Per-signal catalog mapping each signal's stated intent to its actual computation, with semantic match assessment. This is the developer-facing companion to `docs/signals_moderator_guide.md` (which is moderator-facing prose). When the moderator guide says *what* a signal means, this catalog says *whether the code agrees*.

## How to use this doc

- **When adding a new signal:** add a row before merging. The row is the contract; the code must satisfy it.
- **When debugging strategy scoring:** check the `Failure mode` column for the signal involved — semantic drift looks identical to a working signal at runtime.
- **When auditing:** the next audit is a *diff* against this file. Update rows whose computation has changed; re-grade matches that have shifted.
- **When renaming or removing a signal:** update both the code and the row in the same commit.

## Severity legend

| Tag | Meaning |
|-----|---------|
| `plausible-impact` | Drift could plausibly affect strategy scoring, moderator decisions, or developer mental models. Worth fixing. |
| `likely-trivial` | Wording or framing mismatch with no behavioral consequence. Document for awareness; fix opportunistically. |
| `none` | Code, name, doc, and YAML usage agree. No action. |

## Failure mode reference

| Mode | Name | One-line |
|------|------|----------|
| 1 | Name overpromises | Name implies more than the computation delivers |
| 2 | Doc/code mental model mismatch | Computation is reasonable but doesn't match the moderator's intuition |
| 3 | Magic constants encode hidden intent | Thresholds/binning are uncalibrated to the stated meaning |
| 4 | Hidden dependency | Computation relies on something the name doesn't hint at |
| 5 | Edge case violates meaning | Empty/small/extreme inputs return values that betray the stated semantics |
| 6 | Consumer mismatch | YAML uses the signal as a proxy for something it doesn't actually measure |

## Ground truth approach

A+C blend: the moderator guide (`docs/signals_moderator_guide.md`) is the authoritative statement of intent. Where doc and code agree, apply independent reasoning ("would a fresh moderator expect this?") as a sanity check.

---

## Summary roll-up

**Audit date:** 2026-04-07
**Signals audited:** 34 (8 graph-global, 12 graph-node, 6 LLM, 4 session/temporal, 4 meta)

### Counts

| Pool | ✅ clean | ⚠️ drift | ❌ broken | plausible-impact | likely-trivial |
|------|---------|----------|-----------|------------------|----------------|
| graph-global | 3 | 5 | 0 | 4 | 4 |
| graph-node | 7 | 4 | 1 | 4 | 4 |
| LLM | 2 | 4 | 0 | 1 | 4 |
| session/temporal | 1 | 3 | 0 | 1 | 3 |
| meta | 2 | 2 | 0 | 2 | 2 |
| **Total** | **15** | **18** | **1** | **12** | **17** |

### 🚨 Critical findings (must fix)

1. **`response.semantic.llm.engagement.trend` doc drift in agent spec** (session/temporal). ✅ **FIXED** — `signal-specialist/AGENT.md` Section 10 now correctly lists `deepening/stable/shallowing/fatigued`. The prior `improving/degrading/stable` vocabulary has been corrected.
   **Note:** Moderator guide's "last 4" claim still imprecise — code actually uses a last-6 window with 4-sample minimum gate.

### Plausible-impact findings (worth fixing)

4. **`convgraph.state.node.count`, `convgraph.state.edge.count`, `convgraph.state.node.orphan_count` are unbounded ints** (graph-global).
   The scoring engine multiplies signal value × weight. With raw counts in the 10s, a 0.5 weight contributes 5–15 points — dwarfing any [0,1] signal. Currently dormant because no YAML uses them in `signal_weights` (only in declaration lists). One YAML edit away from wildly miscalibrated scoring.
   **Fix:** Normalize at the signal layer (e.g., `min(count, 20) / 20`) OR add explicit guard rails preventing raw counts from being weighted.

5. **`canongraph.state.edge.density` is unbounded above 1.0** (graph-global).
   Edge/node ratio can exceed 1.0 (e.g., 3 edges / 2 nodes = 1.5). Threshold-bin logic assumes [0,1] input. Currently dormant in YAML weights.
   **Fix:** Document the unbounded range; if YAML weights are added, use bare-key direct multiplication, not `.high` suffix.

6. **`canongraph.state.exhaustion` "canonical" guarantee is conditional** (graph-global).
   When `enable_canonical_slots=False`, `NodeStateTracker` falls back to surface-node IDs and the signal silently averages surface-node exhaustion while presenting as "canonical."
   **Fix:** Log a warning when computing over surface-keyed states, or skip the signal entirely when canonical slots are disabled.

7. **`convgraph.node.exhaustion` shallow_ratio counts both `surface` AND `shallow`** (graph-node).
   Agent doc Section 4 says "fraction of entries equal to `surface`." Base class counts both `surface` and `shallow`. The two-category count is more nuanced and probably correct, but the agent doc lies.
   **Fix:** ✅ **FIXED** — Updated Section 4 of `signal-specialist/AGENT.md` (line 69) and `docs/signals_moderator_guide.md` (line 89) to correctly state "counts both `surface` AND `shallow`". Also updated the quick reference to clarify the moderator interpretation of the signal.

8. **`response.semantic.llm.response_depth` name vs computation** (LLM).
   Name evokes laddering depth (semantic). Rubric measures *number of distinct propositions* introduced (informational breadth). A respondent giving five surface facts scores 4–5 ("deep"); a respondent giving one introspective insight scores 2. YAML strategies treating `response_depth.deep` as "respondent is going deep" silently misuse the signal.
   **Fix:** Rename to `llm.response_richness` OR update guide + class description to clarify "depth = proposition count, not semantic depth."

9. **`meta.saturation.canonical` edge case inverted** (meta).
   When `surface_delta == 0` (no extraction), code returns `novelty_ratio = 1.0` → `saturation = 0.0`. But "no extraction at all" is arguably the *most* saturated state, not the least. The comment "no extraction — not saturated" encodes a debatable design choice.
   **Fix:** Either return `1.0` (truly saturated) or split into two signals — one for novelty, one for productivity.

10. **`convgraph.node.is_current_focus` reads `previous_focus`** (graph-node).
    Behavior is correct given Stage 8 ordering (`update_focus()` hasn't been called yet at signal detection time), but the name "is current focus" is misleading. Reads as "the node focused in the prior turn at detection time."
    **Fix:** Rename to `convgraph.node.is_prior_focus` OR add a clarifying note in the moderator guide.

### Likely-trivial findings (document, fix opportunistically)

- `convgraph.state.max_depth`: methodology-relative normalization (already documented in guide as a known limitation)
- `convgraph.chain.completion.ratio`: brittle with N=1 (already documented)
- `canongraph.state.node.count`: returns `{}` not `0.0` when canonical graph is None — guide claim of "returns 0.0" is wrong
- `canongraph.state.edge.density`: same `{}` vs `0.0` issue in guide
- `convgraph.node.novelty`: guide says "high = last 2 turns" but `>= 0.6` boundary includes age=2 — effectively "last 3 turns"
- `llm.specificity`: class docstring and decorator description are inverted (1=specific, 5=ambiguous) — rubric is correct, runtime unaffected, but a developer trap
- `llm.valence`: rubric measures emotional tone, not topic sentiment — calm description of negative event scores 3 (neutral). May surprise moderators expecting sentiment tracking
- `response.semantic.llm.engagement` vs `llm.intellectual_engagement`: rubrics are well-separated; risk is YAML authors conflating them by name
- `response.semantic.llm.response_depth` 5→4 collapse: undocumented but currently harmless (no YAML uses the missing fifth bin)
- `interview.strategy.self_count`: minimum non-zero value is 0.2 (current turn already in history), not 0.0 as implied
- `interview.strategy.turns_since_change`: same 0.2 floor
- `meta.saturation.conversation`: at turn 1 returns 0.0 (peak == 0) — contradicts guide claim "respondent can be at 1.0 in early turns"
- `interview.phase`: returns 3 keys (`phase`, `phase_reason`, `is_late_stage`) — only `phase` is documented in the moderator guide

### Recommended action priority

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Fix `canongraph.node.novelty` instance lifecycle bug | Medium (touches NodeSignalDetectionService) |
| P0 | ✅ **DONE:** Correct `signal-specialist/AGENT.md` Section 10 `global_response_trend` values | Trivial (text edit) |
| P1 | Normalize or guard raw count signals (`node_count`, `edge_count`, `orphan_count`) | Low |
| P1 | Decide rename or document for `response.semantic.llm.response_depth` (depth vs richness) | Low (decision); medium (rename) |
| P1 | Fix `meta.saturation.canonical` empty-extraction edge case (or accept design) | Low (decision) |
| ✅ | **DONE:** Fix `signal-specialist/AGENT.md` Section 4 shallow_ratio definition | Trivial |
| P2 | Update moderator guide for the documented likely-trivial drifts | Low |

---

## Catalog

### Graph signals (global)

> Source: `src/signals/graph/graph_signals.py`

| Signal | Stated intent (guide) | Actual computation | Match | Failure mode | Severity | Recommended action |
|---|---|---|---|---|---|---|
| `convgraph.state.node.count` | Count of active surface nodes — breadth of coverage | Returns `graph_state.node_count` as unbounded `int` | ⚠️ | Mode 3+6: raw int multiplied by weight in scoring; no [0,1] normalization | plausible-impact | Normalize at signal layer (`min(count, 20) / 20`) or document the scaling behavior |
| `convgraph.state.edge.count` | Count of directed edges — connectivity | Returns `graph_state.edge_count` as unbounded `int` | ⚠️ | Mode 3+6: same unbounded-int issue | plausible-impact | Same normalization recommendation |
| `convgraph.state.node.orphan_count` | Count of nodes with zero incoming AND zero outgoing edges | Returns `graph_state.orphan_count` as unbounded `int` | ⚠️ | Mode 3+6: same unbounded-int issue | plausible-impact | Normalize, or reframe as `orphan_ratio = orphan_count / max(node_count, 1)` |
| `convgraph.state.max_depth` | Length of longest causal chain, normalized by ontology level count | BFS from root nodes; longest path / ontology level count; clamped [0,1]; fallback level count = 5.0 | ✅ | Mode 4 (mild): fallback constant 5.0 is MEC-calibrated | likely-trivial | Accept with caveat — already in guide's "Limitations" section |
| `convgraph.chain.completion.ratio` | Fraction of level-1 nodes with complete BFS path to terminal | `complete_chain_count / max(level_1_count, 1)` | ✅ | Mode 5: brittle with N=1 (already in guide) | likely-trivial | None — documented |
| `convgraph.chain.completion.has_complete` | Boolean: at least one complete chain exists | `complete_chain_count > 0` | ✅ | none | none | None |
| `canongraph.state.node.count` | Count of active canonical slots | Returns `cg_state.concept_count`; returns `{}` (absent) when `cg_state is None` | ⚠️ | Mode 5: guide claims "returns 0.0", code returns absent | likely-trivial | Fix guide wording — signal is absent (not 0.0) when canonical graph not initialized |
| `canongraph.state.edge.density` | Edge-to-concept ratio in canonical graph | `cg_state.edge_count / cg_state.concept_count`; 0.0 when `concept_count==0`; absent when `cg_state is None` | ⚠️ | Mode 3+5: unbounded above 1.0; absent vs 0.0 confusion | plausible-impact | Document unbounded range; fix guide's "0.0" claim |
| `canongraph.state.exhaustion` | Average exhaustion across canonical slots, deduplicated | Iterates `node_tracker.states.values()` averaging per-state exhaustion; "canonical" guarantee depends on `enable_canonical_slots=True` | ⚠️ | Mode 4+5: silent fallback to surface-keyed states when canonical slots disabled | plausible-impact | Log warning or skip signal when canonical slots disabled |

### Graph signals (node-level)

> Source: `src/signals/graph/node_signals.py`

| Signal | Stated intent (guide) | Actual computation | Match | Failure mode | Severity | Recommended action |
|---|---|---|---|---|---|---|
| `convgraph.node.exhaustion` | 0–1 weighted sum: 40% turns_since_yield + 30% focus_streak + 30% shallow_ratio | Formula matches exactly. `shallow_ratio` counts both `surface` AND `shallow`. ✅ **FIXED** — agent doc and moderator guide now correctly state both categories are counted | ✅ | none | none | None — all docs now align |
| `convgraph.node.yield_stagnation` | Boolean: no yield for 3+ consecutive turns on previously-focused node | `focus_count > 0` AND `turns_since_last_yield >= 3` | ✅ | none | none | None |
| `convgraph.node.focus.streak` | Categorical count of consecutive focus turns: none=0, low=1, medium=2-3, high=4+ | Bins exactly as documented; reads `state.current_focus_streak` (correctly NOT reset in `record_yield()`) | ✅ | none | none | None — bin thresholds match guide |
| `convgraph.node.is_current_focus` | Boolean: true for currently active focus node | Compares each `node_id` to `node_tracker.previous_focus` | ⚠️ | Mode 2: name says "current," reads "previous" — correct given stage timing but misleading | plausible-impact | Rename to `convgraph.node.is_prior_focus` OR add a clarifying note in the moderator guide. ✅ **CLARIFIED** — moderator guide updated (line 92) to note that signal reads previous_focus due to pipeline stage ordering |
| `convgraph.node.recency` | Float 1.0→0.0 decaying over 20 turns since last focus | `max(0.0, 1.0 - turns_since_last_focus / 20.0)`; 0.0 if never focused | ✅ | none | none | None |
| `convgraph.node.is_orphan` | Boolean: zero incoming AND zero outgoing edges | Reads `state.is_orphan` property | ✅ | none | none | None |
| `convgraph.node.edge_count` | Sum of incoming + outgoing edges per node | `state.edge_count_incoming + state.edge_count_outgoing` | ✅ | none | none | None |
| `convgraph.node.has_outgoing` | Boolean: at least one outgoing edge | `state.edge_count_outgoing > 0` | ✅ | none | none | None |
| `convgraph.node.novelty` | Age-based freshness; high≥0.6 (last 2 turns), medium 0.3-0.6, low <0.3 | `max(0.0, 1.0 - age/5)` where age=current_turn-created_at_turn; bins high≥0.6, medium≥0.3 | ⚠️ | Mode 3: boundary-inclusive — age=2 → score=0.6 → still `high`, effectively "last 3 turns" | likely-trivial | Fix guide wording to "last 3 turns (age 0–2)" |
| `convgraph.node.focus.count` | Cumulative total focus turns; none=0, low=1-2, medium=3-4, high=5+ | Bins exactly as documented; reads `state.focus_count` | ✅ | none | none | None — bin thresholds match guide |
| `canongraph.node.novelty` | Classifies node as new/confirming/orphan based on canonical slot history | `_slot_first_seen` is an instance attribute on a class re-instantiated every turn — cross-turn memory destroyed; every slot reads as "new" | ❌ | Mode 4+5: hidden dependency on persistent instance, invalidated by service architecture | plausible-impact | **CRITICAL** — move `_slot_first_seen` into `NodeStateTracker` or maintain singleton signal instance |

### LLM signals

> Source: `src/signals/llm/signals/`

| Signal | Stated intent (guide) | Actual computation (rubric) | Match | Failure mode | Severity | Recommended action |
|---|---|---|---|---|---|---|
| `response.semantic.llm.response_depth` | How much information is shared; 1=surface, 4-5=deep | Rubric counts **distinct propositions/concepts introduced** (informational breadth, not semantic depth). Score 4 and 5 collapse to `"deep"` | ⚠️ | Mode 1: name evokes laddering depth, rubric measures proposition count; Mode 3: 5→4 collapse undocumented | plausible-impact (mode 1) / likely-trivial (collapse) | Rename to `llm.response_richness` OR update guide to clarify "depth = proposition count" |
| `response.semantic.llm.certainty` | Confidence; low=hedging, high=unqualified | Rubric scores expressed confidence with social-softener calibration ("I think" as opener ≠ hedge). Continuous | ✅ | none | none | None — most precisely specified LLM signal |
| `response.semantic.llm.engagement` | Willingness to participate | Rubric: participatory behavior, volunteering, deflection; orthogonal to intellectual_engagement | ⚠️ | Mode 4: name risks YAML authors confusing with intellectual_engagement | likely-trivial | Add callout in guide distinguishing the two signals |

### Session / temporal signals

> Source: `src/signals/session/`

| Signal | Stated intent (guide) | Actual computation | Match | Failure mode | Severity | Recommended action |
|---|---|---|---|---|---|---|
| `response.semantic.llm.engagement.trend` | Categorical from last 4 response_depth values: deepening/stable/shallowing/fatigued | Code returns `deepening/stable/shallowing/fatigued` (matches guide). Uses last-6 window with 4-sample minimum gate (not "last 4"). YAML matches code | ⚠️ | Mode 2: agent doc Section 10 falsely claims `improving/degrading/stable`; Mode 3: guide's "last 4" is imprecise (last-6 window) | plausible-impact (agent doc) / likely-trivial (guide imprecision) | **CRITICAL** — fix `signal-specialist/AGENT.md` Section 10. Clarify guide's window size |
| `interview.strategy.self_count` | Count of current strategy in last 5 turns / 5; high≥0.75 | `count(strategy_history[-1] in strategy_history[-5:]) / 5`. Current turn already in history → minimum value is 0.2, not 0.0 | ⚠️ | Mode 5: floor of 0.2 on first use, contradicts implied 0.0 minimum | likely-trivial | Add note to guide: minimum non-zero value is 0.2 |
| `interview.strategy.turns_since_change` | Count of consecutive same-strategy turns / 5; high≥0.6 | Iterates `reversed(strategy_history)` counting trailing identical entries / 5; same 0.2 floor as above | ⚠️ | Mode 5: same 0.2 floor | likely-trivial | Same note as above |
| `interview.focus.streak` | Per-node consecutive same-strategy: none=0, low=1-2, medium=3-4, high=5+ | Reads `state.consecutive_same_strategy`; bins exactly as documented; iterates all nodes via `_get_all_node_states()` | ✅ | none | none | None |

### Meta signals

> Source: `src/signals/meta/`

| Signal | Stated intent (guide) | Actual computation | Match | Failure mode | Severity | Recommended action |
|---|---|---|---|---|---|---|
| `interview.phase` | Categorical early/mid/late from turn count + YAML phase boundaries | Reads `interview_config.phases.{exploratory,focused}.n_turns` from YAML; maps `early_max = exploratory_n + 1`, `mid_max = exploratory_n + focused_n + 1`. Returns 3 keys: `phase`, `phase_reason`, `is_late_stage` | ⚠️ | Mode 2 (mild): guide documents only the `phase` key, not `phase_reason` and `is_late_stage` | likely-trivial | Document the auxiliary keys in the guide |
| `meta.saturation.conversation` | "Are responses drying up?"; 1 - min(current_new_nodes / peak, 1) | Formula matches exactly. When `peak == 0` (turn 1), returns `yield_ratio = 1.0` → saturation = 0.0 | ⚠️ | Mode 5: at turn 1, never saturated regardless of yield (peak undefined). Guide claims "respondent can be at 1.0 in early turns" — impossible at turn 1 | likely-trivial | Fix guide claim about turn-1 behavior |
| `meta.saturation.canonical` | "Are we in redundant territory?"; 1 - min(new_canonical / new_surface, 1) | Formula matches. When `surface_delta == 0`, returns `novelty_ratio = 1.0` → saturation = 0.0. Comment: "no extraction — not saturated" | ⚠️ | Mode 5: empty-extraction edge case is debatable. "No extraction at all" is arguably the *most* saturated state, not the least | plausible-impact | Decide: return 1.0 (truly saturated) or split into two signals (novelty + productivity) |

---

## Audit metadata

- **Auditors:** 4 parallel Sonnet sub-agents (graph-global, graph-node, LLM, session/temporal) + 1 inline review (meta)
- **Method:** A+C blend per `## Ground truth approach`. Each signal: read source class, read moderator guide entry, read YAML usage, assess against failure mode taxonomy.
- **Coverage gaps:** None — all active signals audited. Deleted signals excluded: `convgraph.state.avg_depth`, `graph.depth_by_element`, `meta.interview_progress`, `meta.node.opportunity`, `convgraph.node.exhausted`, `llm.specificity`, `llm.valence`, `llm.intellectual_engagement`.
- **Next audit:** Should be a diff against this file. Re-grade rows whose code has changed; add rows for any new signals.
