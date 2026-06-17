# Interview Review — 20260505_094020

**Methodology:** jobs_to_be_done_v2 | **Concept:** zerofizz_beverage_jtbd | **Persona:** baseline_cooperative | **Turns:** 15

---

## 1. Transcript Quality

Overall: The conversation flows naturally with good followership — questions consistently build from the respondent's last answer. No system-state leaks or meta-language contamination. The main weakness is repetitive ascend laddering in the mid phase (turns 7–11), which creates a "survey" feel as the same "why does X matter?" pattern cycles through different nodes.

### Flags
- Turn 3 [ascend]: Leading question — "Why does it matter to you that choosing a drink doesn't say anything about who you are?" The respondent explicitly pushes back: "Honestly, I'm not sure I'd frame it that way." → **resistance_adapted** (Turn 4 pivots to a different angle)
- Turns 7–11 [ascend ×5]: Pattern fatigue — "Why does having a few sodas a day feel different...", "Why does knowing what you're getting into matter...", "When you check what's in a drink...", "When you glance at that label...", "Why does making sure it's actually zero or minimal sugar matter..." — all ascend with minimal variation in question form → **laddering_monotony**
- Turn 14 [close]: Good summary closure — accurately reflects the transparency/ingredient-checking theme. But the final "Anything else?" is weak for a closing question.

### Behavioral Pattern Summary
- Tangents: 0 detected
- Contradictions: 0 detected
- Resistance: 1 explicit redirect (Turn 3) → adapted in Turn 4

### Strengths
- Strong opening question: situates the respondent in a specific recent moment
- Good use of respondent's own language in follow-ups
- Turn 6 (ground) is well-executed — shifts from abstract identity talk to concrete situations
- Turn 12 (ground) picks up on an underexplored thread (ingredient distrust)

---

## 2. Focus Node Fidelity

Fidelity Rate: 7/10 node-bound turns faithful — **concern** (70% threshold met, but barely)

### Mismatches
- Turn 3 [ascend]: focus_node="feeling thirsty with a drink readily available" (Job Trigger) but question probes identity/meaning of drink choice. The focus node is about physiological thirst + availability; the question is about social signaling. → **focus_drift**
- Turn 6 [ground]: focus_node="avoiding the pressure of drink choices feeling like a health identity statement" (Pain Point) but question asks "What situations come up where you really notice the difference between ZeroFizz and regular soda?" — this is asking for concrete contexts, which is grounding, but the focus node is about pressure/identity, not situations. → **loose_coupling**
- Turn 9 [ascend]: focus_node="consuming multiple sodas per day" (Job Context, L0) but question is "When you check what's in a drink before buying it, what are you really protecting yourself from?" — this references content from Turn 8, not the focus node. The focus node is a context about soda frequency; the question is about label-checking motivation. → **focus_drift**

### Focus-less turns (expected for some strategies)
- Turns 1, 4, 13 [anchor]: `node_binding: required` but focus_node="not recorded (pre-fix run)" — these should have focus nodes. Likely a tracker/slot resolution issue.
- Turn 14 [close]: `node_binding: none`, `generates_closing_question: true` — no focus node is expected and correct.

### High-Fidelity Turns
- Turn 2 [ascend]: focus_node="at work during the day", question "Why doesn't choosing ZeroFizz instead of regular soda feel like it says something about who you are?" — cleanly ascends from the workplace context to identity
- Turn 5 [anchor]: focus_node="being a little more intentional about drink choice in the moment", question "When you're being intentional about grabbing ZeroFizz, what's actually going through your head in that moment?" — directly builds from the focus node
- Turn 7 [ascend]: focus_node="consuming multiple sodas per day", question "Why does having a few sodas a day feel different when you're drinking ZeroFizz instead of regular soda?" — clean ladder from context to emotional driver
- Turn 8 [ascend]: focus_node="knowing exactly what you are getting into with regular soda", question "Why does knowing what you're getting into matter to you?" — tight, direct ascend
- Turn 10 [ascend]: focus_node="knowing exactly what you are getting into with regular soda", question "When you glance at that label before buying, what does it actually give you peace of mind about?" — builds from the trigger node
- Turn 11 [ascend]: focus_node="grabbing a drink without checking its contents first", question "Why does making sure it's actually zero or minimal sugar matter to you?" — clean ladder
- Turn 12 [ground]: focus_node="avoiding tooth damage from sugary drinks", question "What's made you feel like drinks aren't always as healthy as they claim to be?" — effectively grounds the pain point in experience

---

## 3. Strategy Assessment

Distribution: **issues** — ascend dominates (57%), anchor overused for a node-bound strategy with 3/5 turns missing focus nodes.

| Strategy | Count | % | Assessment |
|----------|-------|---|------------|
| ascend | 8 | 57% | **Monotony risk** — exceeds 50% threshold |
| anchor | 5 | 36% | 3/5 turns missing focus nodes ("pre-fix run") |
| ground | 2 | 14% | Underused — only fired twice in mid phase |
| close | 1 | 7% | Correctly fires once in late phase |
| surface_tension | 0 | 0% | Never fired — certainty.low fired 38% but may not have overcome anchor's structural mass |
| revitalize | 0 | 0% | Never fired — engagement.high fired 40%, engagement.low never fired |

Phase Alignment: **misaligned**
- Early phase (turns 1–5): anchor×3, ascend×2. Methodology YAML says ground should be prioritized (1.2× multiplier), but ground fired 0 times in early phase. Ascend at 1.0× multiplier still won twice over ground at 1.2× — suggests ground's node-level signals are weaker than ascend's.
- Mid phase (turns 6–13): ascend×6, ground×2, anchor×1. Methodology YAML says ascend and ground should be equal at 1.3× each, but ascend fired 6× vs ground 2×. Ground's structural signals are being outcompeted by ascend's broader positive mass.
- Late phase (turn 14): close fires correctly with 1.5× multiplier.

Score Separation: **healthy** — Phase Multiplier Differential table shows winner/runner-up gaps from 0.000 to 1.000. Most turns have clear winners. Turn 13 is close (-0.510 against winner = anchor won despite ground having 1.3× multiplier).

Structural Fidelity: **critical failure** — see Section 4.

### Anomalies
- **ascend streak (5 consecutive, turns 7–11)**: `interview.strategy.self_count` brake at -0.30 should accumulate to -1.50 by turn 5 of the streak, but ascend's positive mass (275.933 net in signal budget) overwhelms this. The brake is too weak relative to structural positive mass.
- **ground under-selection**: Net budget for ground (421.447) exceeds ascend (275.933), yet ascend won 8× vs ground's 2×. This suggests the phase multiplier differential is not the issue — node-level signals are systematically favoring ascend over ground. `gap.above.true` fires at 89% vs `gap.below.true` at 87% — both near-identical. The difference may be in recency/novelty routing.
- **surface_tension never fires**: Certainty.low fires 38% of the time (243/647), and surface_tension has `certainty.low: 0.40` as primary gate. But `self_count: -1.00` is the strongest brake in the system — even a single prior use would make it score negative. Combined with anchor's `is_orphan.true: 0.50` competing for the same nodes, surface_tension can't gain traction.

---

## 4. Causal Chain Quality

### Structural Completeness
- Full chains: 0/0 (0%) — **critical failure**
- The graph has 50 nodes but **0 chain-relevant edges**. Edge extraction produced no edges at all for this run. Every node is an orphan — `convgraph.node.is_orphan.true` fires at 100% (647/647).

This means:
- No causal chains were constructed
- No structural understanding of how jobs connect to solutions
- The interview produced a flat list of concepts with no relational structure
- Every strategy is operating on isolated nodes — ascend/ground can't actually ladder because there are no chain gaps to detect

### Root Cause: Zero Edge Extraction

The simulation output shows "Edges: 0" in the graph summary. The causal chain report confirms "Chain edges traversed: 0" for both surface and canonical graphs. This is not a chain construction issue — it's an **edge extraction failure**. The extraction stage (Stage 3) or edge extraction bridge (Stage 4.6) produced no relationships.

Possible causes to investigate:
1. **Edge extraction Haiku model returning empty results** — The edge extraction was switched from Sonnet to Haiku (commit `85b9e09`). Haiku may be failing to produce edges for the JTBD methodology's 9 edge types.
2. **Methodology YAML edge type mismatch** — JTBD defines 9 edge types (triggers, implies, supports, drives, occurs_in, addresses, achieves, conflicts_with, revises). The edge extraction prompt may not be correctly rendering all 9 types.
3. **Feature flag or configuration issue** — Stage 4.5B edge extraction was made mandatory in B11 (commit `4a80203`), but something may be silently failing in the bridge stage.

### Methodology-Specific Assessment
- **Zero chain progression**: With 5 ontology levels (L0→L4) and no edges, there is no chain structure at all. The interview cannot demonstrate JTBD's core value proposition of connecting jobs to solutions through causal chains.
- **All nodes orphaned**: 50 nodes, 0 edges. The `is_orphan.true` signal fires at 100% because no node has any edges.
- **No terminal nodes reached**: The terminal node type `solution_approach` was extracted (7 nodes: drink in fridge at work, choosing ZeroFizz..., checking drink contents..., glancing at label..., scanning for zero sugar..., scrutinising ingredient list..., checking for artificial sweeteners...), but none are connected to the jobs they solve.

### Orphan Analysis
All 50 nodes are orphans. The most concerning orphan clusters:
- **Solution nodes with no job connections**: 7 solution_approach nodes exist but none connect to the jobs they address. For example, "scanning for zero or minimal sugar on the label" should connect to "reducing sugar consumption throughout the day" via achieves/drives edges — but no edge exists.
- **Job statements without emotional drivers**: "cutting back on sugar intake" and "getting the fizz sensation without feeling like doing something bad for oneself" are job statements that should have upward edges to emotional_job nodes — none exist.

---

## 5. Graph Health

- Growth: **healthy pattern** — 6→3→2→2→4→4→4→3→6→4→3→3→4→3→0 (50 nodes over 15 turns). Steady extraction throughout.
- Orphans: **100% throughout** — every single node is an orphan because no edges exist. This is not a dedup issue; it's an edge extraction failure.
- Density: **0.00 edge/node** — critical failure. Healthy range is 1.0–2.0 for JTBD.
- Node type balance: **reasonable** — pain_point (16), emotional_job (8), gain_point (7), solution_approach (7), job_statement (7), job_context (3), job_trigger (2), social_job (1). Pain points dominate at 32%, which is acceptable for JTBD (pain is central to job discovery).

---

## 6. Actionable Recommendations

### Critical Priority

1. **Investigate zero edge extraction for JTBD** — The fundamental issue: 0 edges across 15 turns.
   - Evidence: Graph summary shows 0 edges. Causal chains shows 0 chains. `is_orphan.true` fires at 100%.
   - Check: `src/services/edge_extraction_service.py` — does the Haiku model produce edges for JTBD's 9 edge types?
   - Check: `src/llm/prompts/edge_extraction.py` — is the JTBD edge type schema rendered correctly in the prompt?
   - Quick diagnostic: Run `zerofizz_beverage_mec` (MEC strict) with same parameters and check if edges are produced. If MEC produces edges but JTBD doesn't, the issue is JTBD-specific (edge type count or prompt rendering).
   - Expected impact: Without edges, the entire chain-aware architecture (ascend, ground, chain topology signals) is operating on null data. Fixing this transforms the interview from a flat concept collector to a structured causal discovery tool.

### High Priority

2. **Strengthen ascend repetition brake** — ascend fired 8× (57% of turns) with a 5-turn consecutive streak despite `self_count: -0.30`.
   - Evidence: Turns 7–11 all ascend. Net budget for ascend is 275.933 vs ground's 421.447, yet ascend dominated.
   - Fix: Increase `interview.strategy.self_count` for ascend from -0.30 to -0.50 (matching revitalize's brake) in `config/methodologies/jobs_to_be_done_v2.yaml`.
   - Expected impact: Reduces ascend monoculture, gives ground more opportunities to fire.

3. **Fix anchor focus node resolution** — 3/5 anchor turns show "not recorded (pre-fix run)".
   - Evidence: Turns 1, 4, 13 all use anchor but have no focus node.
   - Check: `src/services/focus_selection_service.py` or the node tracker's focus resolution for anchor's `bridge_target: either` + `extraction_mode: prefer_existing`.
   - Expected impact: Anchor questions will reference specific nodes rather than being generic follow-ups.

### Medium Priority

4. **Investigate surface_tension never firing** — `self_count: -1.00` brake kills it after any single use.
   - Evidence: certainty.low fires 38% of turns, but surface_tension never selected.
   - Fix: Consider reducing brake to -0.50 and adding `convgraph.node.focus.streak.none: 0.20` for baseline competitiveness.
   - Reference: `.claude/context/strategy-scoring.md` — escape valve repetition weights section.

5. **Re-examine ascend vs ground signal balance** — Both have near-identical structural signal firing rates (gap.above 89%, gap.below 87%), yet ascend dominates 8:2.
   - Evidence: Signal budget shows ground has higher net mass (421.447 vs 275.933), suggesting the issue is in how node-level signals route during joint scoring, not in the weights themselves.
   - Check: `src/services/methodology_strategy_service.py` — joint scoring may be routing recency/novelty in a way that systematically favors ascend over ground.

### Low Priority / Verify

6. **Turn 3 respondent pushback** — Question framed the respondent's statement in a way they disagreed with.
   - Evidence: "Honestly, I'm not sure I'd frame it that way."
   - This is a question generation nuance — the LLM over-interpreted "drink selection carries no social signal" as "it matters to you that it doesn't say anything." The fix is in prompt tuning, not urgent.
