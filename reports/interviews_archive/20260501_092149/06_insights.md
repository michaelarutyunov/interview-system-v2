# Interview Review — 20260501_092149

**Concept**: ZeroFizz Sugar-Free Carbonated Beverage (JTBD)
**Persona**: Baseline Cooperative Respondent
**Methodology**: `jobs_to_be_done_v2` (V3.1, 5-level ontology)
**Turns**: 12 | **Status**: Closing strategy selected

---

## 1. Transcript Quality

Overall: Natural and well-followed with a coherent guilt-to-freedom narrative arc. However, 5 consecutive ascends (Turns 6-10) create a survey-like rhythm in the mid-phase, and two focus-node mismatches suggest the strategy selector and question generator are drifting apart.

### Flags

- **Turn 3 [ascend]**: focus_node="eating out at a restaurant" (L0 job_context) but question asks "Why does that lingering aftertaste bother you enough to skip the drink altogether?" — the question is about Turn 2's aftertaste pain point, not the restaurant context. → `focus_node_mismatch`
- **Turn 5 [ground]**: focus_node="lingering metallic or chemical aftertaste" (L1 pain_point) but question asks "What situations make you actually want a carbonated drink?" — valid ground question but targets the wrong node; the aftertaste node doesn't need situational antecedents. → `focus_node_mismatch`
- **Turn 7 [ascend]**: Repeats "carbonation cuts through heavy food" as focus node (same as Turn 6). Re-targeting a just-laddered node suggests `focus.streak.none` (97% fire, 0.30 weight) overpowered recency dampening. → `stale_focus_node`
- **Turns 6→7→8→9→10**: Five consecutive ascends — the rhythm becomes mechanical. A ground or anchor between Turns 8-9 would have diversified the laddering angle by exploring the social dimension (introduced Turn 5 but never returned to).

### Behavioral Pattern Summary

- **Tangents**: 0 detected — interviewer stays on-thread throughout
- **Contradictions**: 0 detected — respondent is consistent
- **Resistance**: 0 explicit redirects — baseline cooperative persona lives up to its name
- **System state leak**: None — all questions read as human-plausible

### Strengths

- Opening question is excellent: specific, contextual, open-ended, no leading language
- Turns 8→9→10 produce a clean guilt-to-freedom ladder: "guilt awareness with regular soda" → "drinking without a guilty inner voice" → "feel at ease and unselfconscious" → "decision fatigue from constant dietary self-monitoring"
- Turn 11 (close) is well-timed and natural: "Is there anything else about how ZeroFizz fits into your life without that guilt that feels important to mention?" — synthesizes the dominant narrative
- The interviewer discovers an emotionally resonant job (guilt-free consumption as permission to stop monitoring) that the respondent hadn't articulated before Turn 8

---

## 2. Focus Node Fidelity

Fidelity Rate: 7/10 turns with recorded focus nodes — **borderline (70%)**

### Mismatches

- **Turn 3 [ascend]**: focus_node="eating out at a restaurant" but question probes aftertaste → Likely cause: the node scorer selected the L0 context node, but the question generator attended to the most recent extraction (Turn 2's aftertaste). Two pipeline stages disagreeing on what's "current."
- **Turn 5 [ground]**: focus_node="lingering metallic or chemical aftertaste" but question asks about carbonation situations → Likely cause: ground's "find antecedents" instruction led the question generator to ask about triggers (contexts preceding aftertaste sensitivity), but the focus recorder logged the aftertaste node rather than the contextual trigger being probed.
- **Turn 7 [ascend]**: focus_node="carbonation cuts through heavy food" — same node as Turn 6, unchanged after Turn 6 already laddered from it → Likely cause: `convgraph.node.focus.streak.none` (97% fire, 0.30 weight) and `focus.count.none` (88% fire, 0.20 weight) gave this node persistent competitive advantage despite recent use.

### High-Fidelity Turns

- **Turn 1 [ascend]**: focus_node="low engagement with fizzy drinks category" → question cleanly asks "Why is it that fizzy drinks just aren't something you reach for regularly?"
- **Turn 6 [ascend]**: focus_node="carbonation cuts through heavy food" → question asks "Why does that feeling of cutting through the heaviness matter to you?"
- **Turn 8 [ascend]**: focus_node="feel free from self-monitoring and dietary vigilance" → question cleanly builds: "what changes about how much you're thinking about what you're consuming?"
- **Turn 9 [ascend]**: focus_node="drinking without a guilty inner voice" → question feels the emotional state: "What does it feel like when you're drinking ZeroFizz and that guilt voice just... isn't there?"
- **Turn 10 [ascend]**: focus_node="feel at ease and unselfconscious while drinking" → question ladders naturally: "Why does being able to just enjoy the drink without that nagging feeling matter so much to you?"

---

## 3. Strategy Assessment

### Distribution: Severe ascend monoculture

| Strategy | Count | % | Assessment |
|----------|-------|---|------------|
| ascend | 7 | 70% | **MONOTONY** — 5 consecutive mid-phase ascends |
| ground | 2 | 20% | Under-used; one was mis-targeted (Turn 5) |
| anchor | 1 | 10% | Competitive net (+173) but overshadowed by ascend (+213) |
| surface_tension | 0 | 0% | +159 net, zero negative mass, never fires |
| revitalize | 0 | 0% | Dead — all engagement signals at 0% |
| close | 1 | 10% | Correct phase placement; -28 net mathematically dead outside late |

ascend at 70% far exceeds the 50% monotony threshold. The 5-turn streak (Turns 6-10) is the longest consecutive ascend run across all 7 recent JTBD reviews.

### Streaks

- **Turns 6→7→8→9→10**: Five consecutive ascends. The respondent stays engaged (cooperative persona) but the rhythm becomes mechanical. Turn 7 repeats Turn 6's focus node — the streak is self-reinforcing.

### Phase Alignment: Multipliers can't correct the imbalance

- **Early (Turns 1-4)**: ascend, ground, ascend, anchor — reasonable mix. ground gets 1.2× but ascend still wins Turn 3.
- **Mid (Turns 5-10)**: ground, ascend×5 — ascend and ground have identical 1.3× mid multipliers, so they can't break ties. The 5-turn streak happens entirely within mid phase.
- **Late (Turn 11)**: close — the 1.50 multiplier (vs ground's 0.90) creates a 1.200 gap, the only multiplier-driven selection.

Phase multipliers are structurally neutral for ascend vs. ground in mid phase (both 1.3×) — base score advantage determines the winner every time.

### Score Separation: ascend's structural advantage is decisive

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 301.920 | -88.934 | **212.986** |
| anchor | 284.380 | -110.868 | 173.512 |
| surface_tension | 159.050 | **0.000** | 159.050 |
| ground | 265.220 | -147.716 | 117.504 |
| revitalize | 0.000 | -2.990 | -2.990 |
| close | 2.000 | -30.000 | -28.000 |

ascend's 212 → 173 gap over anchor is ~39 points — small in absolute terms but anchor's orphan-triggered architecture (`is_orphan.true` at 0% fire, dead signal) means anchor can never surpass ascend when the graph is well-connected.

**surface_tension paradox**: 159.050 positive mass with **zero negative mass**. No repetition brake, no saturation suppressor — pure upside. Yet it never fires because its node-scoped signals (`yield_stagnation.true` 5%, `focus.count.medium` dead at 0%) rarely activate. The strategy has mass but no trigger. The global `certainty.low` signal fires at 89% (always-on for this hedging persona), but without node-scoped signals to select a target, the joint scorer can't produce a winning pair.

### Structural Fidelity: No full chains reach L4

Zero full chains (see Section 4). Five advanced chains reach L3 (emotional_job/social_job) but none complete the final step to L4 (solution_approach). The `drives` edge from emotional_job to solution_approach is systematically under-extracted.

---

## 4. Causal Chain Quality

### Structural Completeness

- **Full chains**: 0/18 surface (0%) — **structural failure for 12-turn cooperative interview**
- **Advanced chains**: 5/18 (28%) — reach L3, one gap to full
- **Developing chains**: 3/18 (17%)
- **Started chains**: 10/18 (56%) — fragments that never connected

The complete absence of full chains in a 12-turn cooperative interview is the gravest finding. Compare: the 20260430_105032 Baseline Cooperative (15 turns) produced 4 full chains. Something degraded between those runs.

### Chain-by-Chain Assessment

| Chain | Tier | Coherence | Evidence | Actionable | Key Issue |
|-------|------|-----------|----------|------------|-----------|
| Advanced 1 [surface] | advanced | strong | strong | yes | Shortcut to L4 (L0→L1→L2→L4, skips L3) |
| Advanced 2 [surface] | advanced | strong | strong | yes | Same shortcut pattern (L1→L2→L4) |
| Advanced 3 [surface] | advanced | strong | strong | yes | Heavy food → carbonation → freedom from self-monitoring. Stops at L3 |
| Advanced 4 [surface] | advanced | strong | moderate | partial | Blood sugar worry → eat/socialize → free from self-monitoring. Convergent with Chain 3 |
| Advanced 5 [surface] | advanced | strong | moderate | yes | Same start as 4 but reaches social_job (L3) — only chain reaching social dimension |
| Developing 2 [surface] | developing | strong | strong | **yes** | Social trigger → avoid standing out → choose ZeroFizz. Reaches L4 via social job — structurally most complete |

### Chain Convergence

Advanced Chains 3, 4, and 5 all converge on the guilt/freedom cluster. These are three paths through the same narrative territory — the interview discovered one strong job and explored it thoroughly, but produced no alternative job narratives. Not necessarily a failure: a single well-understood job beats three shallow ones.

### Business Insights

1. **"Permission to stop the mental math"**: The core job is removing the cognitive load of dietary self-monitoring. ZeroFizz lets the respondent "just have a soda without that guilt thing in the back of my head." This is a positioning insight: market the removal of decision fatigue, not the absence of sugar. — Supported by Advanced Chains 3, 4, 5.

2. **"Social belonging without deviance"**: The social chain (Developing 2) shows ZeroFizz solves "not wanting to be the person just holding water." The job is fitting in without the health cost of regular soda. This is a distribution/occasion insight: social eating triggers hiring. — Supported by Developing Chain 2.

3. **"Carbonation as digestive comfort"**: The physical sensation of "cutting through heavy food" is a distinct functional job separate from the guilt narrative. The carbonation level matters for the food-pairing use case. — Supported by Advanced Chain 3.

### Methodology-Specific Assessment

- **L3→L4 gap is systematic**: 5 advanced chains all stall at L3. The `drives` edge (emotional_job → solution_approach) is present in extraction (Turn 8: "guilt awareness → choosing ZeroFizz") but the chain builder doesn't traverse them into full chains. Check `config/chain_rules/jobs_to_be_done_v2.yaml` — `drives` is classified as `upward`, which should allow L3→L4 traversal. The issue may be that `drives` edges are created in extraction but not traversed by the chain builder's completeness validator.
- **No `circular_chain` or `shortcut_chain` flags** — chain topology is clean, just incomplete.
- **Canonical chains** (2 started) are expected to be sparse per `.claude/context/canonical-slots.md` — not a concern. The 37→4 compression (89%) is aggressive but within normal range for a single coherent narrative.
- **social_job appears once**: Advanced Chain 5 reaches `be fully present in the social eating experience` — the ontology supports social_job at L3 but extraction rarely produces it.

### Orphan Analysis

No orphan nodes — the graph is fully connected. This is a double-edged finding: good connectivity means extraction is finding relationships, but zero orphans means `anchor`'s `is_orphan.true` signal (0.50 weight) will never fire. Anchor's only path to selection is through `charge.negative` (0.30, 34% fire rate).

---

## 5. Graph Health

- **Growth**: 37 surface nodes over 12 turns (3.1/turn avg) — healthy, consistent extraction. No stalling.
- **Canonical compression**: 37 → 4 nodes (89% reduction). Heavy but expected for a coherent single narrative.
- **Orphans**: 0 — fully connected. Every node participates in at least one chain edge.
- **Density**: 43 chain edges / 37 nodes = 1.16 edge/node — healthy.
- **Node type balance**: pain_point and gain_point most frequent; social_job singly represented; job_trigger sparse. Reflects the guilt/freedom narrative dominance — more emotional/affective nodes, fewer situational/trigger nodes.

---

## 6. Actionable Recommendations

### High Priority

1. **ascend self_count brake too weak** → `config/methodologies/jobs_to_be_done_v2.yaml`, `strategies.ascend.signal_weights`
   - Evidence: 5 consecutive ascends (Turns 6-10), 70% ascend share. Brake (-0.15) dwarfed by 301.92 positive mass.
   - Fix: Increase to -0.30 (matching ground). At -0.30, 5th consecutive ascend has -1.50 penalty.
   - Expected impact: ascend share drops to 40-50%, ground and anchor gain 2-3 more selections.

2. **Zero full chains in 12-turn cooperative interview** → `config/chain_rules/jobs_to_be_done_v2.yaml` or chain builder in `scripts/reporting/generate_causal_chains.py`
   - Evidence: 5 advanced chains stall at L3. `drives` edges (emotional_job → solution_approach) are extracted but chains don't traverse L3→L4.
   - Fix: Audit chain builder traversal of `drives` edges. Check whether the chain completeness validator requires all intermediate levels without gaps — "advanced" classification tolerates one gap but still excludes from "full."
   - Expected impact: 2-4 full chains in cooperative 12-turn interviews.

3. **surface_tension has zero negative mass (159+ net, 0 negative)** → `config/methodologies/jobs_to_be_done_v2.yaml`, `strategies.surface_tension.signal_weights`
   - Evidence: Zero negative mass in budget. Strategy never fires because node-scoped signals rarely activate, but when they do there are no brakes.
   - Fix: Add `interview.strategy.self_count: -0.30` and `meta.saturation.canonical.high: -0.30`.
   - Expected impact: surface_tension becomes a targeted tool (1-2 uses/interview) rather than a latent risk.

### Medium Priority

4. **close is mathematically dead outside late phase** → `config/methodologies/jobs_to_be_done_v2.yaml`, `strategies.close.signal_weights`
   - Evidence: -28.000 net. Only positive signal is `interview.phase.late: 2.0` against -30 of phase penalties. No other positive mass.
   - Fix: Add `meta.saturation.conversation.high: 0.30` and `meta.saturation.canonical.high: 0.20`.
   - Expected impact: close becomes selectable in late phase without needing competitor exhaustion.

5. **anchor's `is_orphan.true` structurally dead (0% fire)** → `src/signals/graph/` or detection service
   - Evidence: 0 orphan nodes. `supports` edges aggressively connect everything. `is_orphan.true` (0.50 weight) has no targets.
   - Fix: Increase `convgraph.node.llm.charge.negative` weight from 0.30 to 0.40 — make charge the de facto anchor trigger since orphans are rare.
   - Expected impact: anchor fires 2-3 times/interview on negative-charge nodes.

### Low Priority / Verify

6. **Turn 3 and Turn 5 focus_node mismatches** — verify that `resolve_focus_from_strategy_output()` in `FocusSelectionService` and the question generator's concept injection use the same recency window. Check `src/services/turn_pipeline/stages/strategy_selection_stage.py` and `question_generation_stage.py`.
