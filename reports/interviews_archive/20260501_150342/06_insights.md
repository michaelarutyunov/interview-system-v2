# Interview Review — 20260501_150342

**Concept**: ZeroFizz Sugar-Free Carbonated Beverage (MEC)
**Persona**: Baseline Cooperative Respondent
**Methodology**: `means_end_chain_v2_strict` (V3.1, 5-level ontology: attribute → functional_consequence → psychosocial_consequence → instrumental_value → terminal_value)
**Turns**: 12 | **Status**: Closing strategy selected

---

## 1. Transcript Quality

Overall: Coherent, natural conversation. The interviewer follows the respondent's thread well, and the questions read as human-plausible with no system_state_leak. However, the conversation stays on the same narrow territory — taste quality and brand perception — for the entire interview. The respondent is cooperative but the interviewer never breaks through to values.

### Flags

- **Turn 6 [branch]**: Returns to "acceptable taste despite no sugar" for the THIRD time (also Turns 1, 2, 3, 4). The respondent is repeating themselves. → `stale_focus_node`
- **Turn 8 [branch]**: Returns to "acceptable taste despite no sugar" for the FOURTH time. → `stale_focus_node`
- **Turn 9 [branch]**: FIFTH time on "acceptable taste despite no sugar." The respondent finally expands into brand philosophy territory but only because the interviewer kept pushing the same node. → `extraction_stagnation`
- **No value-level concepts extracted**: After 12 turns, not a single instrumental_value or terminal_value node was produced. The laddering never reached values — the defining purpose of MEC.

### Behavioral Pattern Summary

- **Tangents**: 0 — interviewer stays on-thread (too tightly)
- **Contradictions**: 0
- **Resistance**: 0
- **System state leak**: None

### Strengths

- Opening question is concrete and experiential: "Can you tell me about a recent time you chose a drink like ZeroFizz over something else?"
- Turn 10 (ground): "What about the way a company presents those details tells you whether they actually understand what you want?" — good question probing the brand-trust inference
- Turn 11 (close): Natural wrap-up that synthesizes the taste → brand trust thread

---

## 2. Focus Node Fidelity

Fidelity Rate: 5/10 — **concern**

### Critical Failure

"acceptable taste despite no sugar" was selected as focus node on 5 of 10 active turns (Turns 3, 4, 6, 8, 9). This is a structural failure — `branching_deficit` fires at 100% but only identifies a single node as needing branching. Once branch fires on that node and the respondent provides new material, the system should detect the branch is resolved and move on. Instead, it re-selects the same node.

### Mismatches

- **Turn 6 [branch]**: Third branch on same node. The question "What specifically makes the taste of a sugar-free soda acceptable or not to you?" re-asks what Turns 1-5 already covered.
- **Turns 8-9 [branch, branch]**: Fourth and fifth branches on same node. The respondent had to generate new angles ("brand philosophy," "usability details") because the repeated probing forced them to.

---

## 3. Strategy Assessment

### Distribution: Severe branch monoculture

| Strategy | Count | % | Assessment |
|----------|-------|---|------------|
| branch | 7 | 70% | **MONOTONY** — same node targeted 5 times |
| ground | 2 | 20% | Only strategy to produce L3 nodes |
| ascend | 1 | 10% | Single use, gated on 41/46 nodes |
| close | 1 | 10% | Correct phase placement |
| bridge | 0 | 0% | Gated on 48 nodes |
| anchor | 0 | 0% | Gated on 46 nodes |

### Root cause: `branching_deficit` always-on + exhausted gates for others

`branching_deficit` fires at 100% (always true for all eligible nodes). Meanwhile:
- `gap_above` fires on only 46/46 nodes — 100% fire rate but 41 gated (only 5 eligible)
- `gap_below` fires on only 4 nodes
- `is_orphan` fires on 14 nodes but all 46 gated
- `level_skip` fires on 0 eligible nodes (48 gated)

Branch has the most eligible nodes and the least structural competition. The gates for ascend, ground, bridge, and anchor are so restrictive that only branch consistently finds targets.

### Budget decomposition

| Strategy | Positive | Negative | Net |
|----------|----------|----------|-----|
| branch | 56.858 | -9.300 | 47.558 |
| ascend | 23.932 | -8.300 | 15.632 |
| anchor | 7.000 | -3.000 | 4.000 |
| ground | 2.200 | -0.720 | 1.480 |
| revitalize | 0.000 | -4.847 | -4.847 |
| close | 0.200 | -30.000 | -29.800 |

branch has 3× the net of ascend and 32× ground. The budget is not competitive — branch is mathematically dominant.

### Structural Fidelity: Failure

**Zero chains reach L4 (instrumental_value) or L5 (terminal_value).** The MEC methodology's purpose is to ladder from attributes to values. After 12 turns with a cooperative respondent, the graph contains no value-level nodes at all. This is a structural failure — the extraction pipeline is not producing value concepts, and the strategy selector can't target what doesn't exist.

---

## 4. Causal Chain Quality

### Structural Completeness

- **Full chains**: 0/18 (0%)
- **Advanced chains**: 0/18 (0%)
- **Developing**: 18/18 (100%) — **everything stalls at L3**
- **Started**: 0

All chains stop at psychosocial_consequence (L3) or below. The longest chain (Chain 1, 7 nodes) reaches "brand trustworthiness and consumer understanding" (psychosocial_consequence, L3) but never connects to instrumental_value (L4) or terminal_value (L5).

### Chain-by-Chain Assessment

| Chain | Length | Max Level | Coherence | Key Issue |
|-------|--------|-----------|-----------|-----------|
| Chain 1 [surface] | 7 | L3 | strong | Longest chain; attribute→functional→psychosocial arc is clean |
| Chain 2 [surface] | 6 | L3 | strong | Taste quality → brand trust via "real consumer testing" inference |
| Chain 3 [surface] | 6 | L3 | strong | Same arc as 2 but via "brand prioritizing people" node |
| Chain 4 [surface] | 5 | L3 | moderate | Convergent with 2-3 on brand trustworthiness endpoint |
| Chains 5-18 | 3-4 | L2-L3 | weak | Fragments; many are attribute→attribute pairs + one functional_consequence |

### Chain Convergence

All chains converge on one of two endpoints:
1. `brand trustworthiness and consumer understanding` (psychosocial_consequence, L3)
2. `authentic soda experience` (functional_consequence, L2)

The interview discovered one insight (good taste signals brand competence) and never moved past it.

### Business Insights

1. **"Taste quality is a brand competence signal"**: The respondent infers brand trustworthiness from taste execution — "they made it actually taste okay" translates to "they tested it with real people instead of just checking a box." Supported by Chains 1-4. Actionable for positioning: market the care put into taste as proof of brand integrity.
2. **"No aftertaste = no artificial taste = brand gets what consumers want"**: The absence of artificial sweetener aftertaste is not just a sensory preference — it's interpreted as evidence that the brand understands consumer priorities. Supported by Chains 2-3.

### Methodology-Specific Assessment

- **MEC's defining chain structure (attribute → functional → psychosocial → instrumental → terminal) is absent.** The extraction pipeline never produces instrumental_value or terminal_value nodes. Without L4/L5 nodes, the chain builder can never produce "full" or "advanced" chains.
- **L3 is the ceiling**: psychosocial_consequence ("brand trustworthiness") is the highest level reached. The extraction LLM is not inferring the values that brand trust serves.
- **Canonical chains**: 16 developing — the canonical layer mirrors the surface in its inability to reach values. Not a concern per canonical-slots.md (sparse by design), but the complete absence of value nodes in both layers points to extraction, not compression.

---

## 5. Graph Health

- **Growth**: 31 surface nodes over 12 turns (2.6/turn avg) — healthy
- **Node types present**: attribute (L1), functional_consequence (L2), psychosocial_consequence (L3) — **missing instrumental_value (L4) and terminal_value (L5) entirely**
- **Orphans**: Not reported in chain output (no orphan section)
- **Density**: 40 chain edges / 31 nodes = 1.29 edge/node — healthy
- **Canonical compression**: 31 → 6 (81%) — within normal range

The absence of L4/L5 nodes is the defining graph health issue. The graph is well-connected but truncated — it's a 3-level graph when the methodology requires 5 levels for chain completion.

---

## 6. Actionable Recommendations

### High Priority

1. **Extraction never produces value-level nodes (L4/L5)** → `src/llm/prompts/extraction.py` and/or `config/methodologies/means_end_chain_v2_strict.yaml`
   - Evidence: 31 nodes, zero instrumental_value or terminal_value. After 12 turns with a cooperative respondent, MEC's defining output (attribute→value chains) is completely absent.
   - Fix: Check the extraction prompt's methodology-specific section for MEC. The `extraction_guidelines` in the MEC YAML should include explicit instruction to infer instrumental and terminal values from psychosocial content. Example: when the respondent says "I trust a brand that gets what people want," the extraction should infer instrumental_value ("being discerning about product quality") and terminal_value ("feeling respected as a consumer").
   - Expected impact: 2-4 value-level nodes per interview, enabling chain completion.

2. **branch monoculture — `branching_deficit` at 100% fire rate** → `config/methodologies/means_end_chain_v2_strict.yaml`, `strategies.branch.signal_weights`
   - Evidence: branch won 7/10 turns, targeting the same node 5 times. `branching_deficit` fires on every eligible node. The strategy has 3× the net budget of the next competitor.
   - Fix: Add `interview.strategy.self_count: -0.30` to branch (currently has no repetition brake). Reduce `branching_deficit` weight from its current value to make room for other strategies when the deficit is mild.
   - Expected impact: branch drops to 3-4 uses per interview, ascend and ground gain 2-3 more selections.

### Medium Priority

3. **`acceptable taste despite no sugar` selected 5 times** → `src/services/turn_pipeline/stages/strategy_selection_stage.py` or `src/services/node_state_tracker.py`
   - Evidence: Same node re-selected across Turns 3, 4, 6, 8, 9. `focus.streak.none` and `focus.count.none` should penalize re-selection but are clearly not doing so.
   - Fix: The post-generation honesty check bead (`interview-system-v2-7hs1`) would partially address this. Additionally, check whether `exhaustion` signal (dead at 0% fire, weight 0.80) is firing — if exhaustion never triggers, the re-selection penalty is missing.

4. **Gates are too restrictive** → `config/methodologies/means_end_chain_v2_strict.yaml`
   - Evidence: bridge (48 gated), ground (47), anchor (46), ascend (41) all have most nodes gated. Only branch (35) has meaningful eligibility. With valid_when gates blocking 89-100% of nodes for 4 of 5 active strategies, branch wins by default.
   - Fix: Review valid_when gate conditions. If gates are correct but the graph lacks the signal conditions (e.g., no gap_above because L4/L5 nodes don't exist), the fix is #1 (extraction) not the gates. If gates are too narrow even with full graphs, reduce gate thresholds.

### Low Priority

5. **MEC chain_rules uses `leads_to: unconstrained`** — the strict schema enforcement is in the YAML's `permitted_connections` on the edge definition, not in chain_rules. Verify that the extraction LLM is respecting permitted_connections (attribute→functional_consequence, functional_consequence→psychosocial_consequence, etc.) and not creating invalid edges that the chain builder rejects.
