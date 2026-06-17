# Interview Review — 20260430_164959

**Concept**: ZeroFizz Sugar-Free Carbonated Beverage (JTBD)
**Persona**: Baseline Cooperative Respondent
**Methodology**: `jobs_to_be_done_v2` (V3.1, 5-level ontology)
**Turns**: 12 | **Status**: Closing strategy selected

---

## 1. Transcript Quality

**Overall**: The interview opens strongly (turns 0-6) with cooperative, substantive responses averaging ~55 words. A steep quality decline occurs at turn 7 when `surface_tension` takes over, driving a 4-turn streak of increasingly granular probing into physical bloating sensations that yield diminishing returns and hedged answers.

**Openness**: The opening question is well-structured -- it asks for a specific recent occasion and an open-ended walkthrough. The respondent engages fully. Through turn 6, questions remain open and avoid yes/no framing.

**Followership**: Turns 1-5 demonstrate good followership -- questions build on the respondent's previous answer and ladder with clear conceptual continuity. The break occurs at turn 7: the `surface_tension` strategy pivots to probing physical sensations ("how does avoiding that sluggish feeling change what you're able to do?"), and when the respondent hedges ("Honestly I'm not sure it makes that big of a difference"), the engine doubles down rather than pivoting. Turns 8-10 continue probing the same physical-sensation vein with increasingly narrow focus (lightness in body, then stomach mechanics, then exact timing).

**Naturalness**: Questions in turns 1-6 read naturally. The `surface_tension` questions (turns 8-10) become mildly clinical ("what specifically happens differently in your stomach compared to regular soda?") -- the respondent's "Honestly not sure what the exact difference is" (turn 9) signals the line has been crossed.

**Leading questions**: None detected. Questions are open-ended probes, not suggestions.

**Contradictions**: A significant unresolved contradiction at turn 7. Turn 6 established that the respondent avoids sugar because of "sluggish" feelings and "sugar crash." Turn 7 the respondent states: "I don't really get the crash thing other people talk about, maybe I'm just used to it." This direct reversal of the premise that had been driving the interview was not addressed. The engine continued probing the physical sensation angle without reconciling the contradiction.

**Tangential drift**: The `surface_tension` streak (turns 7-10) drifts from the core JTBD (emotional job of genuine choice) into granular physical-sensation territory (bloating timeline, stomach fullness). While physical comfort is a legitimate gain point, four consecutive turns on this narrow topic represent over-indexing.

**Resistance signals**: The respondent uses "Honestly" as a hedge prefix in 4 of the last 6 answers (turns 7, 8, 9, 10). "I'm not sure" / "not a big deal" / "I guess" appear across turns 7-10. These are soft pushback signals that the line of questioning is not landing but were not recognized as such by the strategy selector.

**System state leaks**: None detected. No meta-language about pipeline state, phase, or strategy appears in questions.

### Behavioral Pattern Summary

| Pattern | Count | Turns |
|---------|-------|-------|
| Cooperative/engaged | 6 | 0, 1, 2, 3, 4, 5 |
| Hedging answers ("Honestly...", "I guess") | 4 | 7, 8, 9, 10 |
| Direct contradiction | 1 | 7 vs 6 |
| Soft pushback ("not a big deal") | 3 | 3, 7, 8 |
| Tangential drift | 1 streak | 7-10 |
| Conceptual resolution attempt | 1 | 11 (close) |

---

## 2. Focus Node Fidelity

**Fidelity Rate**: 6/6 for turns with recorded focus nodes. Four turns (7-10) have unrecorded focus nodes annotated as "pre-fix run" -- these cannot be assessed.

**High-fidelity turns**:
- Turn 1 (`ascend` to "sugar-free choice driven by availability not intention"): Question directly echoes the concept -- "Why does it matter to you that the sugar-free option is just there waiting for you?"
- Turn 2 (`ground` to "no noticeable taste difference from regular soda"): Grounding question about taste difference -- clear conceptual link.
- Turn 4 (`ascend` to "feel like I'm not sacrificing anything"): "Why does it matter to you that grabbing a diet soda feels like the same choice as regular?" -- faithfully ascends from the emotional job.
- Turn 5 (`ascend` to "avoid feeling like I'm settling for a lesser option"): Ascend question about genuine choice vs. compromise -- well-targeted.

**Medium-fidelity turns**:
- Turn 3 (`ground` to "no noticeable taste difference from regular soda"): Second ground on same node -- reasonable but partially redundant with turn 2.
- Turn 6 (`ground` to "low attachment to sugar-free over regular soda"): Question shaped by focus node but reads as a generic "what's different?" probe rather than a precise ground.

**Node-binding assessment**: `ascend` and `ground` (both `node_binding: required`) correctly identify and target specific nodes. `surface_tension` (`node_binding: required`) has unrecorded focus nodes -- the fidelity of those selections is unknown. `close` (`node_binding: none`) fulfills its purpose adequately with a conversational summary question at turn 11 -- no focus node is expected.

---

## 3. Strategy Assessment

### Distribution

| Strategy | Count | Turns | % of Turns |
|----------|-------|-------|------------|
| surface_tension | 4 | 7, 8, 9, 10 | 36% |
| ascend | 3 | 1, 4, 5 | 27% |
| ground | 3 | 2, 3, 6 | 27% |
| close | 1 | 11 | 9% |
| anchor | 0 | -- | 0% |
| revitalize | 0 | -- | 0% |

### Streak Analysis

- **surface_tension 4-turn streak (turns 7-10)**: This is the dominant failure mode. The strategy fires on vague/uncertain answers, which the respondent begins giving at turn 7 -- creating a self-reinforcing loop where surface_tension's probing produces more hedging, which keeps surface_tension scores high. This mirrors the known "escape valve positive feedback" failure mode documented in CLAUDE.md.
- **ascend 2-turn streak (turns 4-5)**: Appropriate -- ascend is laddering through emotional jobs. The gap between turns 1 and 4 is filled by ground probes (turns 2-3), which is structurally sound.
- **ground 2-turn streak (turns 2-3)**: Both target the same node ("no noticeable taste difference from regular soda"), making turn 3 partially redundant.

### Phase Alignment vs. YAML Multipliers

JTBD phase multipliers: early(ground:1.2, anchor:1.2, ascend:1.0), mid(ascend:1.3, ground:1.3), late(close:1.5, revitalize:1.2).

| Phase | Turns | Strategies Used | Alignment |
|-------|-------|----------------|-----------|
| Early | 1-4 | ascend, ground, ground, ascend | Good -- ground benefits from 1.2x, ascend operates at base 1.0 |
| Mid | 5-8 | ascend, ground, surface_tension x2 | Poor -- surface_tension has no phase multiplier; ascend/ground boosted but not winning |
| Late | 9-11 | surface_tension x2, close | Partial -- close fires correctly at turn 11 with 1.5x, but surface_tension occupies two late turns unbooted |

The phase multiplier differential table confirms: surface_tension wins relied entirely on raw score (0.000 multiplier effect in 4 of its wins). Only turn 11's close win and turns 2, 5, 8 show meaningful multiplier contributions.

### Score Separation Analysis

`surface_tension` has by far the highest net positive mass (327.03) of any strategy -- 22% higher than `ascend` (268.36) and 2.8x higher than `ground` (116.03). This is a structural imbalance:

- `surface_tension` positive mass (369.65) comes largely from `convgraph.node.focus.streak.none` and `convgraph.node.focus.count.none` (always-firing at 98% and 92%) plus `convgraph.node.novelty.high` (41%) and `response.semantic.llm.certainty.low` (76%). These signals reward nodes that have not been focused before -- so surface_tension perpetually finds fresh targets.
- `ascend` negative mass (-96.48) includes the `meta.saturation.canonical.high` suppressor (-0.300 at 78% firing) -- this correctly penalizes ascend when canonical saturation is high, but surface_tension lacks equivalent suppression.
- `ground` negative mass (-210.86) is the highest of all strategies, largely from saturation suppressors -- ground is effectively penalized for doing its job.

**Root cause**: `surface_tension` has high positive mass, low negative mass, no phase-based penalty, and an always-available pool of unvisited nodes. Once the respondent begins hedging (turn 7), surface_tension becomes the highest-scoring strategy in a self-reinforcing loop.

### Structural Fidelity: Chain Reach

- **1 Full chain** reaches `solution_approach` (L4 terminal) -- generated during turn 5's ascend. This is the only chain that completes the L0 to L4 ontology traversal.
- **3 Advanced chains** approach L4 or L3. Two of these also originate from ascend-driven turns.
- **surface_tension chains**: The 4-turn surface_tension streak produced only `gain_point` and `pain_point` nodes (L1) -- no laddering occurred. These chains are all "Started" tier (2-node fragments).

**Key finding**: `ascend` drives chain completion. `surface_tension` drives node proliferation without structural progress. The 4-turn surface_tension streak consumed 36% of interview turns while contributing zero chain advancement beyond L1.

---

## 4. Causal Chain Quality

### Structural Completeness

| Tier | Surface | Canonical |
|------|---------|-----------|
| Full | 1 | 0 |
| Advanced | 3 | 0 |
| Developing | 3 | 1 |
| Started | 11 | 4 |

Canonical chains are expected to be sparse per `.claude/context/canonical-slots.md` -- 1 Developing + 4 Started from 8 canonical nodes is within normal range. Low canonical counts are not a concern here.

### Chain-by-Chain Assessment

| Chain | Tier | Coherence | Evidence Quality | Actionable | Key Issue |
|-------|------|-----------|-----------------|------------|-----------|
| Full 1 (surface) | Full | Strong | Strong (all t=5) | Yes | Best chain -- ascend-driven, all 4 levels present |
| Advanced 1 (surface) | Advanced | Strong | Good (t=1,4) | Yes | Emotional ladder without L4 terminal |
| Advanced 2 (surface) | Advanced | Strong | Good (t=6) | Yes | Afternoon crash to fizzy need to solution |
| Advanced 3 (surface) | Advanced | Medium | OK (t=1,4) | Maybe | Gap at L2 (job_statement missing) |
| Developing 1 (surface) | Developing | Weak | Weak (no turn refs) | No | Cold drink habit chain -- missing turn anchors |
| Developing 2 (surface) | Developing | Medium | Good (t=3) | Limited | Stress/caffeine scenario -- not core JTBD |
| Developing 3 (surface) | Developing | Medium | Good (t=6) | Limited | Afternoon crash variant with reverse edge |

### Meaningful Chains Highlight

**Full Chain 1** (turn 5, ascend-driven): `diet drinks feel like self-punishment` (L1) to `drink what I genuinely want` (L2) to `feel like my choice reflects what I actually want` (L3) to `choosing ZeroFizz as a genuine preference` (L4). This is the gold-standard chain -- it demonstrates that the ascend strategy successfully laddered from a pain point through job statement and emotional job to terminal solution approach. All evidence comes from a single turn's rich response, suggesting the engine's ascend probing at turn 5 elicited the highest-quality material.

**Advanced Chain 2** (turn 6, ground-driven): `drinking soda in the afternoon` (L0) to `feeling sluggish after afternoon soda` (L1) to `get the fizzy sensation without the sugar downsides` (L2) to `choosing ZeroFizz` (L4). This chain is structurally complete but classified as Advanced due to the L3 skip. The L2 to L4 jump suggests the respondent connects functional job directly to solution without emotional mediation -- a finding in itself.

### Business Insights

1. **The emotional core is "genuine choice, not compromise"**: The sole full chain demonstrates that ZeroFizz's emotional value proposition is about agency -- the respondent wants to feel they chose the product because they genuinely prefer it, not because it is the "diet" option they settled for. Marketing should emphasize ZeroFizz as a first-choice beverage, not a healthier alternative.

2. **Taste parity is the non-negotiable enabler**: Multiple chains (Advanced 3, Started 2) center on "no noticeable taste difference." The respondent explicitly states at turn 2 that without taste parity, they would "just drink less of it" and "go back to regular." If taste degrades, the entire emotional ladder collapses -- the functional and emotional jobs become unreachable.

3. **Physical comfort is secondary, not primary**: The `surface_tension` streak explored bloating and physical sensation extensively (turns 7-10), generating multiple `pain_point` nodes but no completed chains. This is a real but low-priority gain. The emotional job (feeling like a genuine chooser) is the primary driver; physical comfort is a supporting benefit.

4. **Habit dominates acquisition; identity retains**: The respondent acquires Diet Coke/ZeroFizz through office availability and habit (turn 0), not deliberate selection. Retention, however, is driven by the emotional job -- they stay because it does not feel like settling. Go-to-market strategy should separate acquisition tactics (placement, sampling) from retention messaging (identity, genuine preference).

### Methodology-Specific Checks

- **Chain-relevant edges used**: `triggers`, `implies`, `supports`, `drives` (upward spine) and `addresses`, `achieves` (reverse). The reverse edges appear in 4 Started chains -- these produce short solution-facing fragments rather than full ladders.
- **Level skipping**: Advanced Chain 2 skips L3 (emotional_job). The "one gap" classification is correct; the chain is structurally sound but incomplete per strict ontology traversal.
- **No revisions detected**: Zero revised edges means no respondent course-corrections were captured in the graph -- consistent with the cooperative persona but also reflecting that the turn 7 contradiction was not resolved.

---

## 5. Graph Health

**Growth trajectory**: Strong initial growth (7 nodes at turn 0), then sustained yield (3-6/turn through turn 6), then declining yield (2-3/turn during surface_tension streak), then terminal zero (turn 11). The decay in node yield after turn 6 correlates with the surface_tension streak and diminishing respondent engagement. Total: 39 surface nodes, 8 canonical nodes.

**Orphan dynamics**: 1 orphan node -- "not noticing a significant energy difference from avoiding sugar" (turn 7). This is the contradiction node where the respondent walked back the "sugar crash" premise. Its orphan status reflects that it contradicted an established chain and was never integrated. This is structurally correct -- the node should be isolated rather than forced into a chain it contradicts.

**Density**: 46 chain edges / 39 nodes = 1.18 edges per node. Moderate density. The graph is not over-connected (which would suggest spurious edges) nor fragmented (which would suggest extraction failure).

**Node type balance**:

| Type | Surface Count | % of Total | Canonical Count |
|------|--------------|------------|-----------------|
| pain_point | ~14 | 36% | 2 |
| gain_point | ~9 | 23% | 2 |
| emotional_job | ~5 | 13% | 1 |
| job_statement | ~4 | 10% | 0 |
| solution_approach | ~5 | 13% | 1 |
| job_context | ~2 | 5% | 1 |
| job_trigger | ~2 | 5% | 0 |
| social_job | 0 | 0% | 0 |

**Concerns**: `pain_point` dominates at 36% -- this is elevated. The `surface_tension` streak contributed disproportionately to pain_point count (halfway-through-can fullness, uncomfortable fullness, discomfort timing). `social_job` (L3) is entirely absent -- the emotional dimension is captured only through `emotional_job` nodes. The L0 types (`job_context`, `job_trigger`) are underrepresented at 10% combined, suggesting the engine is not grounding sufficiently in situational context.

---

## 6. Actionable Recommendations

### High Priority

1. **Add `surface_tension` repetition brake in `config/methodologies/jobs_to_be_done_v2.yaml`**: The current signal budget shows `surface_tension` with +369.65 positive mass and only -42.62 negative mass -- an 8.7:1 ratio. The 4-turn monoculture (turns 7-10) is structurally inevitable. Add `interview.strategy.self_count` with a negative weight of at least -0.5 to `surface_tension`. Evidence: turns 7-10 show diminishing returns; turn 8 generated 3 nodes from a 53-word answer, turn 10 generated 3 nodes from 37 words -- the engine is extracting fragmentary pain points from increasingly thin material.

2. **Add `meta.saturation.canonical.high` as a suppressor on `surface_tension`**: `ascend` and `ground` both have saturation suppressors contributing to their negative mass (-96 and -210 respectively). `surface_tension` lacks equivalent suppression. When canonical saturation is high (78% firing rate across this interview), continued probing of surface-level tension is counterproductive. Add `meta.saturation.canonical.high: -0.3` to the `surface_tension` strategy weights in `config/methodologies/jobs_to_be_done_v2.yaml`. Evidence: canonical saturation fired at 78% but did not suppress `surface_tension` at all, allowing the 4-turn streak to continue unchecked.

3. **Verify `surface_tension` self_count resolution in `src/methodologies/scoring.py`**: The `interview.strategy.self_count` signal fires at 57% for interview-level strategy tracking but the scorer resolves it per-candidate. Verify that `surface_tension`'s self_count is actually being resolved to `surface_tension`'s own count (not the last-selected strategy's count) via the `_scoped_signal_names()` resolution logic. If the resolution is correct, the weight is simply too low to brake the streak. If incorrect, this is a scoping bug. Evidence: the 4-turn streak should have produced escalating penalty but the strategy kept winning.

### Medium Priority

4. **Reduce `surface_tension` base score by lowering `convgraph.node.focus.streak.none` weight**: This signal fires at 98% with +0.300 contribution -- it is nearly always-on for `surface_tension` because surface_tension targets unfocused nodes by design. Either lower the weight to +0.15 or change the signal to `convgraph.node.focus.streak.low`. File: `config/methodologies/jobs_to_be_done_v2.yaml`. Evidence: the signal's 98% firing rate means it contributes +0.300 to nearly every candidate, making it a de facto base score inflator rather than a discriminative signal.

5. **Add phase multiplier for `surface_tension` in mid phase**: Currently `surface_tension` has no phase multipliers at all. Adding `mid: 0.8` (a mild penalty) would make ascend/ground more competitive during mid phase when surface_tension's raw score advantage is smallest. This is a tuning change, not a structural fix, and should be tested alongside items 1-2. Evidence: in mid phase (turns 5-8), surface_tension won 3/4 slots despite having no multiplier while ascend and ground have 1.3x boost.

6. **Address contradiction handling in `src/llm/prompts/question.py`**: The contradiction between turn 6's "sugar crash" premise and turn 7's "I don't really get the crash thing" was not acknowledged. Consider adding logic to flag when the respondent contradicts a previously established premise and generate a clarifying question rather than continuing to probe. This is a qualitative improvement, not a scoring fix.

### Low Priority

7. **Reduce `pain_point` extraction dominance during surface_tension streaks**: The `surface_tension` streak produced 6 pain_point nodes vs. 2 gain_point nodes -- a 3:1 ratio. The JTBD methodology benefits from balanced extraction. Consider adding extraction guidance in `config/methodologies/jobs_to_be_done_v2.yaml` under `extraction_guidelines` to prefer gain_point extraction when probing positive outcomes. Evidence: turns 8-10 each produced at least one pain_point from answers that also contained gain language ("no bloat", "feel a bit lighter").

8. **Add `social_job` (L3) extraction encouragement**: Zero `social_job` nodes across 12 turns of a social consumption category (beverages) is notable. Review `src/llm/prompts/extraction.py` for L3 type distribution guidance and consider adding a `social_job` example in the JTBD methodology YAML `extraction_guidelines`. The ontology includes `social_job` at L3 alongside `emotional_job`, but only emotional_job nodes were extracted.
