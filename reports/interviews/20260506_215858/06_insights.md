# Interview Review — 20260506_215858

**Concept**: ZeroFizz Sugar-Free Carbonated Beverage (JTBD)  
**Methodology**: `jobs_to_be_done_v2` (V3, 5-level chain-aware)  
**Persona**: Baseline Cooperative Respondent  
**Turns**: 15 (Turn 0 opening + 14 strategy-driven turns)  
**Status**: Closing strategy selected

---

## 1. Transcript Quality

Overall: The interview maintains reasonable conversational flow with good followership — questions consistently build from the respondent's own language. However, several closed/leading questions and one logistics tangent weaken the naturalness. The interviewer correctly avoids system-state leaks.

### Flags
- **Turn 3 [anchor]**: "Who usually stocks the ZeroFizz in your break room fridge?" — logistical tangent, respondent gives brief disengaged answer → **tangent_drift**
- **Turn 6 [ascend]**: "does it matter to you which one you pick?" — closed question, ascend misapplied as preference check rather than laddering → **closed_question**
- **Turn 11 [ground]**: "Has there been a time when someone suggested ZeroFizz to you, and that suggestion made you want it less?" — strongly leading, respondent contradicts ("Not really, no"), zero concepts extracted → **leading_question + missed_extraction**
- **Turn 10→11→12**: T10 surfaces "resenting" theme, T11 probes it and gets denied, T12 returns to control theme without acknowledging the contradiction → **missed_contradiction**

### Behavioral Pattern Summary
- **Tangents**: 1 detected (T3 logistics) → not redirected, interview self-corrects next turn
- **Contradictions**: 1 detected (T10 resent vs T11 no resentment) → unresolved, interviewer pivots away
- **Resistance**: 0 explicit redirects
- **Closed questions**: 4 (T2, T6, T11, T13) — moderate, T2 and T6 are the most problematic since they limit response depth

### Strengths
- Strong followership — questions use the respondent's own phrasing ("3 or 4 o'clock slump," "cold and fizzy," "without thinking")
- T4-T5 and T7-T10 show a natural laddering rhythm: ascend pushes upward, ground pulls back, creating productive tension
- T7 skillfully acknowledges the respondent's low-attachment statement ("even if you'd be fine with coffee") while still probing for meaning
- The closing question (T14) is appropriately open and unpresumptuous

---

## 2. Focus Node Fidelity

**Fidelity Rate**: 10/13 turns faithful (77%) — acceptable

### Mismatches
- **Turn 3 [anchor]**: focus_node="having a headache and running out of usual drink option" but question probes "who stocks the fridge" → The question pivots to a logistical detail unrelated to the focus node's concept of running out of a usual option
  - Likely cause: Question generator attended to the word "usual" (from "usual drink option") and generated a stocking/replenishment question rather than staying with the job story
  - Fix: `src/llm/prompts/question.py` — anchor strategy prompt should emphasize connecting the isolated concept to existing graph structure, not drilling into operational details

- **Turn 6 [ascend]**: focus_node="drink availability at point of need drives consumption without deliberate choice" but question is a preference binary ("does it matter which one you pick?") → The ascend strategy should ladder upward (why does lack of deliberate choice matter?), not ask lateral preference questions
  - Likely cause: Question generator interpreted "without deliberate choice" as indifference between options and probed that angle instead of laddering
  - Fix: `src/llm/prompts/question.py` — ascend prompt should anchor on "why does this matter?" not "what do you prefer?"

- **Turn 11 [ground]**: focus_node="resenting a drink even when it tastes fine if it feels imposed" but question invents a specific scenario (someone suggesting ZeroFizz) → The ground strategy should find antecedents (what leads to resentment?), not test a hypothetical scenario
  - Likely cause: Ground prompt encouraged "find a concrete example" which the LLM over-interpreted as "invent a specific scenario"
  - Fix: `src/llm/prompts/question.py` — ground strategy prompt should ask "what leads to this?" rather than "has this specific scenario happened?"

### High-Fidelity Turns
- **Turn 4 [ascend]**: focus_node="drink choice driven by proximity and availability", question="Why does having ZeroFizz just sitting there make a difference to how your afternoon goes?" — clean ladder from availability to impact
- **Turn 7 [ascend]**: focus_node="feeling reassured knowing a suitable drink option is available", question acknowledges the coffee alternative while probing why ZeroFizz specifically matters — excellent followership + laddering
- **Turn 9 [ascend]**: focus_node="valuing having drink options available", question="Why does it feel important to have that choice—ZeroFizz or coffee—rather than just picking one and sticking with it?" — precise ladder on the options/choice theme
- **Turn 10 [ascend]**: focus_node="feel in control of personal choices without compromise", question="Why does it matter to you that you're the one deciding what to drink?" — continues the autonomy ladder cleanly

---

## 3. Strategy Assessment

### Distribution: issues

| Strategy | Count | % | Assessment |
|----------|-------|---|------------|
| ascend | 7 | 50% | Monotony risk — dominates mid-phase |
| anchor | 3 | 21% | Appropriately concentrated in early phase |
| ground | 3 | 21% | Underweight for a methodology that needs grounding to build full chains |
| close | 1 | 7% | Correctly fires once in late phase |
| surface_tension | 0 | 0% | Dead — structurally cannot compete |
| revitalize | 0 | 0% | Dead — negative net mass |

**Ascend monoculture**: The 5-turn ascend streak (T6-T10) shows the strategy lacks effective competition in mid-phase. While the YAML weights ascend and ground equally in mid (both 1.3x), ascend's structural signal mass (net 256.828) overwhelms ground (net 216.692) because ascend benefits from `gap.above.true` (46% firing rate, 0.50 weight = 0.23 avg contribution) while ground's `gap.below.true` fires less often (35%, 0.50 weight = 0.175 avg).

**Dead surface_tension**: Net mass is 15.600 vs ascend's 256.828 — an order of magnitude gap. The strategy's primary gate (`certainty.low`, 0.40 weight) fires at 45% rate, so the opportunity exists. But the positive mass is too weak to ever win a joint-scoring round. The strong `self_count` brake (-1.00) is irrelevant since it never fires.

**Dead revitalize**: Net mass is -0.065 — literally negative. Its primary gate `engagement.low` fires at only 10%, so the strategy is almost always suppressed. When it could fire, `canonical.saturation` (-0.30) and `self_count` (-0.50) crush the remaining signal.

### Phase Alignment: misaligned

The YAML specifies equal mid-phase multipliers for ascend (1.3) and ground (1.3), suggesting balanced depth/breadth. Actual distribution: ascend 6, ground 2 in mid-phase — a 3:1 ratio.

- Early phase: anchor-heavy (3/5 turns) — acceptable, anchor has 1.2 early multiplier + 0.25 phase bonus, but ground (also 1.2) should have fired more than once in early phase
- Mid phase: ascend dominates (6/8) when ground should fire equally often — the structural signal mass asymmetry (ascend 256.8 vs ground 216.7 net) overrides the phase balance intent
- Late phase: close fires correctly on T14 with 1.5 multiplier + 0.2 bonus

### Score Separation: healthy

Most turns show the same strategy winning across different nodes (winner = runner-up for different candidates), indicating strong score separation between strategies. The phase multiplier differential table shows only 2/14 turns where the multiplier changed the outcome (T3: anchor over ascend by 0.302, T14: close over ascend by 1.000). The primary selection driver is signal weights, not phase multipliers — this is correct system behavior.

### Structural Fidelity: failure

**Only 2 full chains (11%) reach solution_approach (L4)** after 15 turns. The methodology defines solution_approach as the terminal node type. The ascend strategy consistently ladders to emotional_job (L3) — "feeling reassured," "feel in control," "feel autonomous" — but rarely pushes the final step to "so what do you hire?" The 16 advanced chains terminate at L3, one level short of completion.

**0 social_job nodes extracted**: The ontology includes both emotional_job and social_job at L3. Zero social_job nodes across 15 turns suggests either the baseline_cooperative persona doesn't express social concerns, or the extraction has a systematic blind spot for social dimensions.

### Anomalies
- **`convgraph.state.node.orphan_ratio.mid` fires at 98%**: This systemic signal contributes 0.25 to anchor and ground on nearly every turn, effectively becoming baseline noise rather than a discriminative signal → Check if the orphan threshold bands need recalibration for the 5-level JTBD ontology
- **`meta.saturation.canonical.high` fires at 74%**: This suppressor hits all strategies on most turns. Combined with `meta.saturation.conversation.high` (26%), multiple strategies are losing 0.30-0.40 on saturation suppressors → Consider whether these thresholds are calibrated for 15-turn interviews
- **`convgraph.node.focus.count.high` and `convgraph.node.focus.count.medium` are dead**: These signals never fire, meaning no node ever reaches "high" or "medium" focus count. The focus distribution is flat — each node gets selected 1-2 times. This suggests the node selection is spreading too thin rather than depth-building on key nodes

---

## 4. Causal Chain Quality

### Structural Completeness
- **Full chains**: 2/18 (11%) — insufficient for a 15-turn interview. The methodology expects chains reaching solution_approach (L4, terminal node type).
- **Advanced chains**: 16 — all terminate at emotional_job (L3), one level short
- **Canonical chains**: 0 — expected and not flagged per canonical-slots.md (sparse by design)
- **Started-only chains**: 7 orphan nodes from turn 0 never connected — expected, these are superseded by later concepts

### Chain-by-Chain Assessment

| Chain | Tier | Coherence | Evidence | Actionable | Key Issue |
|-------|------|-----------|----------|------------|-----------|
| Full 1 | full | strong | strong | yes | — |
| Full 2 | full | strong | strong | yes | redundant with Full 1 (same terminal path) |
| Adv 1 | advanced | strong | strong | partial | stops at L3, missing solution link |
| Adv 2-7 | advanced | moderate | moderate | partial | redundant permutations through same node cluster |
| Adv 8-9 | advanced | strong | strong | yes | autonomy/control narrative, stops at L3 |
| Adv 10-16 | advanced | moderate | weak | partial | redundant variations on mood/choice/control |

**Redundancy assessment**: The 18 chains collapse into 3 distinct causal narratives:
1. "Afternoon slump → need effortless drink → feel reassured → cold ZeroFizz in fridge" (Full 1-2)
2. "Afternoon fatigue → caffeine crash anxiety → want focus → value options → feel in control" (Adv 1-7)
3. "Mood varies → don't want to be bored/forced → match drink to mood → feel in control" (Adv 8-16)

The combinatorial chain builder inflates the count by finding all edge-permutations through the same node sets. 16 "advanced" chains sound impressive but represent only 2 additional narratives beyond the full chains.

### Meaningful Chains (highlight)

- **Full Chain 1**: *afternoon slump at 3-4pm → need quick effortless drink → feel reassured knowing option is there → cold ZeroFizz ready in fridge* → **"Zero-effort afternoon rescue"**: Consumers hire ZeroFizz to solve the 3pm energy dip without the cognitive load of making coffee or the physiological cost of a caffeine crash. The key feature is *availability at point of need*, not taste or brand.
  - Strengths: Clean causal progression through all 5 ontology levels, strong evidence grounding (every edge has a specific quote)
  - Gaps: Doesn't address why ZeroFizz specifically vs. any cold drink — the competitive differentiation is implied (no sugar crash) but not structurally present in the chain

- **Advanced Chain 8**: *drink preference varies day to day → getting bored from only one option → match drink to current mood and need → feel in control* → **"Mood-matched autonomy"**: Consumers value having options (ZeroFizz + coffee) because different moments call for different drinks — being forced into one choice feels like a loss of autonomy even if the drink tastes fine.
  - Strengths: Surfaces a non-obvious emotional job (autonomy in small choices) that most beverage marketing misses
  - Gaps: Missing the solution link — what does the respondent actually hire to solve this? The chain stops at the emotional job

### Business Insights

1. **"Zero-effort afternoon rescue"** — Consumers don't plan their afternoon drink; they grab whatever's cold and available when the 3pm slump hits. ZeroFizz wins by being *already there and already cold*, not by being the preferred choice. The competitive battle is about fridge stocking, not brand loyalty. → Supported by Full Chains 1-2.

2. **"Autonomy in small choices"** — Choosing between ZeroFizz and coffee isn't about the drinks — it's about feeling in control of a small personal decision. When consumers feel a drink is "imposed" (by availability, by suggestion, by habit), they resent it even if it tastes fine. This is a positioning opportunity: ZeroFizz as "your choice, on your terms." → Supported by Advanced Chains 8-16.

3. **"Caffeine crash anxiety is the real competitor"** — The respondent doesn't avoid coffee because they dislike it (they prefer good coffee when available). They avoid it because the afternoon caffeine crash "messes up the rest of my day at work." ZeroFizz isn't competing with soda — it's competing with the *consequences* of the default caffeine habit. → Supported by Advanced Chains 1-7.

### Methodology-Specific Assessment

- **Terminal node reach**: 2/18 chains reach L4 (solution_approach) — structural failure. The ascend strategy ladders to L3 (emotional_job) consistently but rarely pushes the final rung ("so what do you hire?").
- **Level skipping**: Several advanced chains jump from L1 (pain_point) to L3 (emotional_job), skipping L2 (job_statement). Example: "caffeine crash disrupting workday [L1] → valuing having options [L3]" — these are `shortcut_chain` instances. The extraction system connects pain points directly to emotional jobs without articulating the functional job in between.
- **No `circular_chain` detected**: Chains progress directionally — no looping back to lower levels.
- **No revisions**: 0 revises edges — the respondent never contradicts earlier statements in a way the system captures. The T10→T11 contradiction noted in transcript quality is a missed extraction, not a revision.
- **Expected branching**: The methodology expects 2-3 branches at most node types. The actual branching at L3 (emotional_job → *) is much higher because 16 chains converge on the same 2-3 L3 nodes. This suggests the chain builder is enumerating paths rather than selecting the most meaningful ones.

### Orphan Analysis
- **22 orphan nodes** out of 47 total (47%) — 8 from turn 0 (opening concepts that were superseded), 3 from T10, 2 each from T12 and T13
- The T10 orphans ("resenting a drink," "drink choice driven by what feels right," "feel autonomous") are structurally interesting — they represent a rich turn that generated concepts the chain builder couldn't connect
- The anchor strategy targeted some orphans (T1-T3) but didn't connect the later-arriving T10/T12/T13 orphans before close
- Could the interviewer have connected them? T11 (ground) attempted to connect "resenting" but the leading question backfired. T12 returned to "feel in control" instead of trying a different angle on "resenting"

---

## 5. Graph Health

- **Growth**: Healthy — 47 nodes across 15 turns (3.1/turn average), consistent growth without stalling
- **Orphans**: Peak ~50% at turn 0 (expected), final 22/47 = 47%. The 8 turn-0 orphans inflate the baseline; excluding them, 14/39 = 36% from later turns. Moderately high — the anchor strategy connects some but not all
- **Density**: 51 edges / 47 nodes = 1.09 — healthy range
- **Node type balance**: pain_point (12) > job_trigger (7) = gain_point (7) = emotional_job (7) = solution_approach (7) > job_context (6) > job_statement (5) > social_job (0). Pain points at 26% — no single type dominates. **social_job at 0 is a gap** — either persona artifact or extraction blind spot.

---

## 6. Actionable Recommendations

### High Priority

1. **Ascend monoculture (50% of turns, 5-turn streak T6-T10)** → Fix in `config/methodologies/jobs_to_be_done_v2.yaml`
   - Evidence: ascend net mass (256.828) dwarfs ground (216.692), producing 6:2 ascend:ground ratio in mid-phase despite equal 1.3x multipliers
   - Root cause: `gap.above.true` fires at 46% with 0.50 weight while `gap.below.true` fires at 35% — the structural signal opportunity is asymmetric
   - Fix options: (a) Increase ground's mid-phase multiplier from 1.3 to 1.5, (b) increase ascend's `self_count` brake from -0.30 to -0.50, (c) add `convgraph.node.chain.gap.below.true: 0.15` to ascend as a soft counter-weight (ascend should prefer nodes that *don't* need grounding)
   - Expected impact: More balanced ascend/ground alternation, fewer 4+ turn streaks

2. **Dead surface_tension (0 fires, net mass 15.6 vs ascend's 256.8)** → Fix in `config/methodologies/jobs_to_be_done_v2.yaml`
   - Evidence: `certainty.low` fires at 45% so the gate is available, but the strategy's positive mass is an order of magnitude too weak
   - Root cause: surface_tension has only 3 positive node-scoped signals (total 0.60) vs ascend's 7 (total 2.15)
   - Fix: Add `convgraph.node.novelty.high: 0.20` and `convgraph.node.focus.streak.none: 0.20` to give it baseline competitiveness, increase `certainty.low` from 0.40 to 0.50
   - Expected impact: surface_tension fires 1-2 times per interview when respondent shows genuine uncertainty

3. **Dead revitalize (0 fires, net mass -0.065)** → Fix in `config/methodologies/jobs_to_be_done_v2.yaml`
   - Evidence: `engagement.low` fires at only 10% — revitalize's primary gate is almost never open. When it does open, the suppressor chain (`canonical.saturation` -0.30 + `self_count` -0.50) pushes it below zero
   - Fix: Add a baseline structural weight so revitalize has positive mass even without engagement gates open. Options: `convgraph.node.novelty.high: 0.15` (shift to novel topic), `convgraph.state.node.orphan_ratio.mid: 0.15` (many stranded nodes = time to shift). Reduce `self_count` brake from -0.50 to -0.20 since the strategy rarely fires.
   - Expected impact: revitalize activates when engagement dips in mid-phase, preventing fatigue-driven shallowing

### Medium Priority

4. **Only 2 full chains (11%) reach solution_approach after 15 turns** → Fix in `src/llm/prompts/question.py` and `src/llm/prompts/extraction.py`
   - Evidence: ascend consistently ladders to emotional_job (L3) but stops — the question generator never asks the JTBD equivalent of "so what do you hire?"
   - Fix: Add ascend prompt guidance: "When the respondent has articulated an emotional or social driver, ask what solution or behavior they currently use to fulfill it" — this pushes the final rung from L3 to L4
   - Expected impact: 3-5 full chains per 15-turn interview, with clear solution_approach terminals

5. **Chain redundancy: 18 chains collapse into 3 narratives** → Fix in `scripts/reporting/generate_causal_chains.py`
   - Evidence: 16 advanced chains are permutations through the same 3-4 node clusters
   - Fix: Add a deduplication pass that groups chains sharing >=60% of nodes and reports only the most complete (longest) representative, with a note like "(+5 similar variants)"
   - Expected impact: Cleaner reporting, 4-6 distinct chains instead of 18

6. **T11 contradiction (resent vs. no resentment) unexplored** → Fix in `src/llm/prompts/question.py` and `src/signals/llm/`
   - Evidence: T10 extracts "resenting a drink even when it tastes fine if it feels imposed," T11 asks a leading scenario question about this, respondent denies it, T12 returns to control theme without acknowledging the tension
   - Fix: The ground strategy prompt should include: "If the respondent contradicts or partially agrees with the concept you're grounding, explore the boundary — when is this true vs. not true?" Also, the extraction system should detect T10->T11 as a contradiction and flag it for chain revision
   - Expected impact: More nuanced chains that capture conditional truths ("I resent drinks imposed on me... but not when a friend recommends something")

### Low Priority / Verify

7. **T3 logistics tangent ("Who stocks the fridge?")** → Fix in `src/llm/prompts/question.py`
   - Evidence: anchor strategy asks an operational/logistical question unrelated to the focus node's job story
   - Fix: Add guardrail to anchor prompt: "Do not ask about logistics (who stocks, where it's bought, how it's ordered) — stay focused on the respondent's experience and needs"

8. **0 social_job nodes extracted across 15 turns** → Verify against other JTBD simulations
   - Evidence: The YAML defines social_job at L3, but zero were extracted. Possible causes: (a) baseline_cooperative persona doesn't express social concerns, (b) extraction prompt under-weights social dimensions
   - Fix: Run the same concept+persona with MEC methodology and check if social/symbolic nodes appear. If yes → extraction bias. If no → persona artifact.

9. **`orphan_ratio.mid` fires at 98% — non-discriminative** → Fix in `config/methodologies/jobs_to_be_done_v2.yaml` signal thresholds
   - Evidence: This systemic signal contributes 0.25 to anchor and ground on nearly every turn, effectively becoming baseline noise
   - Fix: Widen the `.mid` band or add a `.low` band so the signal varies across turns and actually discriminates between high-orphan and low-orphan states

---

*Review generated by /interview-review skill on 2026-05-06.*
