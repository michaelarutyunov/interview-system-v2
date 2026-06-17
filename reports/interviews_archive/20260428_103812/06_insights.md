# Interview Review — 20260428_103812

**ZeroFizz Sugar-Free Carbonated Beverage — JTBD (jobs_to_be_done_v2)**
Baseline Cooperative Respondent | 11 turns | Maximum turns reached

---

## 1. Transcript Quality

Overall: The question generator produces natural, conversational questions that generally follow the respondent's thread — but it only has access to 2 of 7 strategies (elaborate + revitalize), so the interview feels like a series of situation-exploration questions with occasional topic shifts rather than a structured laddering interview.

Flags:
- Turn 5 [elaborate]: "what does ZeroFizz need to do for you in that moment?" — mildly leading, introduces the product by name in a way that suggests it already meets the need. Category: *leading question*
- Turn 7 [elaborate]: "Are there times when you're *not* thinking about that guilt thing—like when ZeroFizz just feels like a normal choice?" — assumes ZeroFizz is already part of the respondent's life. Category: *presumptive framing*
- Turn 10 [validate]: "So when ZeroFizz helps you stay sharp during those long work pushes, is that the main reason you reach for it?" — respondent explicitly rejects this framing ("Not really the main reason, honestly"). Category: *misframed validation*

Behavioral Pattern Summary:
- Tangents: 0 detected — respondent stays cooperative and on-topic throughout
- Contradictions: 1 detected → unresolved. Respondent says in Turn 5 that they want "the caffeine kick without feeling like I'm doing something bad," but in Turn 10 says caffeine isn't the main reason. The validate question picks the wrong thread.
- Resistance: 1 explicit redirect → partially adapted. Turn 10 respondent says "Not really the main reason" and shifts to "habit of having something to sip on," but the interview ends — no chance to follow up.

Strengths:
- Strong followership in early turns — Turn 1 picks up "not really thinking" from Turn 0's answer cleanly
- Natural transitions between health/guilt theme and situational exploration
- Questions are open-ended with no yes/no traps except Turn 10's validate framing

---

## 2. Focus Node Fidelity

**Fidelity Rate: N/A** — focus nodes were not recorded for any turn ("not recorded (pre-fix run)"). This is a pre-fix simulation run where the focus node tracking was not yet implemented. Without focus nodes, the question generator had no structural anchor for targeted probing, which compounds the strategy-gating problem below.

The absence of focus nodes means the elaborative questions default to broad situation-exploration rather than targeted node development. This is visible in the transcript: questions cover new ground each turn rather than drilling into specific concepts.

---

## 3. Strategy Assessment

**Distribution: structural failure — 4 of 7 strategies never fire.**

| Strategy | Count | % | Assessment |
|----------|-------|---|------------|
| elaborate | 6 | 55% | **Monoculture risk** — dominates despite repetition brake (-0.7) |
| revitalize | 3 | 27% | Fires when elaborate exhausts novelty |
| validate | 1 | 9% | Only at turn 10 (generates closing question) |
| ascend | 0 | 0% | **Gated out** — `convgraph.node.chain.gap.above` never true |
| ground | 0 | 0% | **Gated out** — `convgraph.node.chain.gap.below` never true |
| anchor | 0 | 0% | **Gated out** — `convgraph.node.is_orphan` never true |
| probe_pain | 0 | 0% | **Gated out** — `convgraph.node.is_orphan` never true |

**Phase Alignment: broken** — all 10 turns show phase=`unknown`. The phase multiplier differential table shows multipliers varying per turn (elaborate ranges from 0.80 to 1.40), so some phase logic is running, but the label is never set. JTBD phase boundaries are `early_max_turns: 4, mid_max_turns: 12` — with 11 turns we should see early→mid→late progression.

**Score Separation: unhealthy** — with only 2 conversation-level strategies competing (elaborate + revitalize), the system degenerates into a binary toggle. validate only enters at turn 10 when its late-phase multiplier kicks in.

**Structural Fidelity: FAILURE**
- **JTBD-specific**: Zero chains reaching `emotional_job` or `social_job` through laddering. The methodology requires at least 2 chains reaching emotional/social jobs after 8+ turns. We have 1 advanced chain reaching emotional_job via `supports` edge (no quote) — far below threshold.
- No `ascend` or `ground` strategies fired, so no laddering occurred. The interview stayed at L0-L2 (context/trigger → pain/gain → job_statement) without progressing to L3 (emotional/social) or L4 (solution).
- The causal chain data confirms: 8 started chains (L0-L1 only) vs. 3 full chains (all short, all ungrounded).

**Root cause**: Chain topology signals (`convgraph.node.chain.gap.above`, `convgraph.node.chain.gap.below`, `convgraph.node.is_orphan`) return nothing for any surface node. The `valid_when` gate in `src/methodologies/scoring.py` checks `node_signal_dict.get(gate_signal)`, which returns `None` (falsy) for every node. All 4 node-bound strategies are excluded from scoring before any weights are applied.

This matches the known failure mode in CLAUDE.md: "Canonical slot nodes always gated on chain topology signals." But here it extends to surface nodes as well — 32 node-level gate failures across 10 turns (see Gate Analysis table). The `ChainTopologySignalDetector` appears not to be producing chain topology signals for any node in this JTBD run.

**Possible causes to investigate:**
1. `config/chain_rules/jobs_to_be_done_v2.yaml` permitted connections may filter all existing edges, leaving zero chain edges for topology analysis
2. The chain topology detector may require `chain_relevant` edges with specific permitted node-type pairs that don't match the actual extracted graph edges
3. The ontology level mapping (L0-L4) in `ChainTopologySignalDetector` may not align with the JTBD node type names in the YAML

**Anomalies:**
- Phase detection broken for all turns → investigate `src/signals/session/` phase detection logic
- Focus nodes not recorded → pre-fix run; expected behavior for this simulation version

---

## 4. Causal Chain Quality

### Structural Completeness
- Full chains: 3/12 (25%) — insufficient for 11-turn interview
- Surface vs. Canonical: 39 surface nodes compressed to 3 canonical nodes (13:1 ratio). This is **aggressive dedup** — only `unconscious_consumption`, `preference_alignment`, and `health_conscious_identity` survive as canonical slots. All surface-level nuance (specific situations, pain points, gain points) is collapsed.
- `over_aggressive_dedup` flag: the canonical layer has zero full chains, hiding the 3 surface full chains. If downstream analysis relies on canonical chains, it sees nothing.
- `low_chain_completion` flag: 8 started chains that never progress past L0-L1. With no ascend/ground strategies firing, the interviewer never laddered these chains upward.

### Chain-by-Chain Assessment

| Chain | Tier | Coherence | Evidence | Actionable | Key Issue |
|-------|------|-----------|----------|------------|-----------|
| Chain 1 [surface] | full | moderate | weak | partial | `ungrounded_chain` — 2 edges, both "(no quote)" |
| Chain 2 [surface] | full | moderate | weak | partial | `ungrounded_chain` — 1 edge, "(no quote)"; minimal chain (2 nodes) |
| Chain 3 [surface] | full | strong | weak | partial | `ungrounded_chain` — 1 edge, "(no quote)"; minimal chain (2 nodes) |
| Adv 1 [surface] | advanced | moderate | weak | partial | Stops at emotional_job, doesn't reach solution |
| Adv 1 [canonical] | advanced | weak | weak | no | `ungrounded_chain` + `over_abstracted` — canonical nodes lose all specificity |

### Meaningful Chains (highlight)

- **Chain 1 [surface]**: `avoid loading up on sugar after prior consumption` → `feel like I'm not adding to the day's indulgences` → `ZeroFizz avoids artificial aftertaste`
  - Causal narrative: guilt from cumulative consumption drives the choice of a product that doesn't add to the guilt tally
  - Strengths: Coherent narrative arc — connects a behavioral trigger to an emotional job to a solution feature
  - Gaps: No quotes backing either edge; chain is only 3 nodes and misses the situational trigger (afternoon slump, work context) that initiates the sequence

- **Chain 2 [surface]**: `get a caffeine boost` → `grabbing a Coke from the fridge`
  - Causal narrative: basic need-fulfillment: caffeine need drives soda selection
  - Strengths: Clean, simple job→solution mapping
  - Gaps: Minimal chain (2 nodes) — says nothing about why Coke vs. alternatives, what emotional/social drivers are at play, or what contexts shape this choice

- **Advanced Chain 1 [canonical]**: `unconscious_consumption` → `preference_alignment` → `health_conscious_identity`
  - Gaps: Canonical abstraction strips all product-specific and situation-specific detail. "Unconscious consumption" could apply to any beverage study. Not actionable for ZeroFizz specifically.

### Business Insights

1. **Guilt management is the core emotional job** — Respondents don't just want caffeine; they want the functional benefit *without* the emotional cost of "doing something bad." ZeroFizz's value proposition should center on permission: "the boost without the guilt." — supported by Chain 1, Advanced Chain [surface]

2. **The "no aftertaste" requirement is a gate, not a selling point** — Multiple turns and chains reference avoiding chemical/artificial taste. This is table stakes for the category, not a differentiator. Marketing should acknowledge it briefly and move on to emotional territory. — supported by Turn 3, Turn 5, Chain 1

3. **The consumption context splits into two modes** — "Autopilot mode" (at work, grabbing whatever's cold) vs. "Conscious mode" (actively trying to cut back, buying for others). Product positioning needs to work in both contexts: available/frictionless for autopilot, emotionally reassuring for conscious. — supported by Turns 7-9, Started Chains 3-7

4. **Caffeine is a secondary driver, not primary** — Despite being mentioned in Turn 0/Chain 2 as the initial job statement, the respondent explicitly downgrades it in Turn 10. The primary job is "having something to sip on while grinding." Caffeine is a hygiene factor. — supported by Turn 10, Advanced Chain [surface]

### Methodology-Specific Assessment

- **JTBD expected**: at least 2 chains reaching `emotional_job` or `social_job` after 8+ turns. **Actual**: 1 ungrounded advanced chain reaching emotional_job. **Status: FAILURE**.
- **Chain depth**: JTBD full chains should connect trigger/pain_point → job_statement → emotional_job/social_job → solution_approach (4-5 levels). **Actual**: chains are 2-3 nodes deep. All 3 "full" chains reach `solution_approach` via the minimum 2-edge path with no intermediate levels.
- `shortcut_chain` flag: Chain 2 (job_statement → solution_approach) skips L1 (pain/gain) and L3 (emotional/social). Structurally valid but analytically thin.
- `circular_chain` flag: Not present in this run.

### Orphan Analysis
- 4 orphan nodes: `at work in the afternoon` (job_context), `carbonation cuts through heavy food` (gain_point), `lingering weird aftertaste` (pain_point), `caffeine helping maintain mental sharpness` (solution_approach)
- `carbonation cuts through heavy food` is a **high-value orphan** — it's a unique gain point specific to carbonated beverages that differentiates from still drinks. The interviewer never probed this because `anchor` and `probe_pain` strategies were gated out.
- `lingering weird aftertaste` is a critical pain point mentioned across multiple turns. The extraction created it as a node but the chain topology couldn't connect it — `anchor` strategy would have been perfect here.

---

## 5. Graph Health

- Growth: healthy — 39 surface nodes across 11 turns (avg 3.5 new nodes/turn), consistent extraction throughput
- Orphans: peak=4, final=4 (10%) — stable, no orphan spike
- Density: 37 chain edges / 39 nodes = 0.95 edge/node — healthy, within the 0.5-2.0 range for a developing interview
- Node type balance: acceptable spread across all 7 JTBD node types. `job_context` (7) and `gain_point` (8) slightly over-represented vs. `emotional_job` (3) and `social_job` (0). The absence of `social_job` nodes despite extraction guidelines explicitly listing them suggests the LLM extraction is not surfacing social dimensions even when present in responses.
- Canonical compression: 39 → 3 (13:1) — severe. The canonical layer is too sparse to serve as a reliable signal source. This directly impacts `meta.saturation.canonical` (always firing at 100%) since 3 slots saturate immediately.
- Note: `social_job` node type completely absent across all 11 turns — either the respondent never mentioned social considerations or the extraction LLM is biased toward functional/emotional jobs. The Turn 1 answer about "buying for someone else" and "thinking about what they'd actually want" is a textbook social job (`choosing for others' preferences`) but was extracted as `job_context` and `job_statement` instead.

---

## 6. Actionable Recommendations

### High Priority

1. **Chain topology signals not firing for JTBD** → Investigate `src/signals/graph/chain_topology_signals.py` and `config/chain_rules/jobs_to_be_done_v2.yaml`
   - Evidence: Gate Analysis shows 32 nodes gated for all 4 node-bound strategies across 10 turns. Zero chain topology signals produced.
   - Likely cause: The permitted connection pairs in the chain rules YAML may not match the actual edge type + node type combinations in the extracted graph. For example, `drives` with permitted pair `emotional_job → solution_approach` won't match edges like `job_statement → solution_approach` that the extraction actually produces.
   - Expected impact: Unblocking ascend/ground/anchor/probe_pain would give the interview laddering capability, dramatically improving chain depth and business insight quality.

2. **Phase detection broken** → Investigate `src/signals/session/` phase detection logic
   - Evidence: All 10 turns show phase=`unknown` in scoring summary. Phase multipliers vary (suggesting some phase logic runs) but label is never set. JTBD phase config specifies `early_max_turns: 4, mid_max_turns: 12`.
   - Expected impact: Correct phase detection would apply appropriate strategy multipliers, favoring breadth (elaborate) early and depth (ascend/ground) in mid-phase.

3. **All chain edges ungrounded — extraction quotes missing** → Investigate `src/services/extraction_service.py` relationship extraction
   - Evidence: Every edge in all 12 chains shows `(no quote)`. The extraction is producing relationships without linking them to source text spans.
   - Expected impact: Grounded chains enable evidence strength assessment and improve causal chain credibility for business stakeholders.

### Medium Priority

4. **Canonical slot compression too aggressive (39→3)** → Tune `canonical_similarity_threshold` (currently 0.60) upward to preserve more surface variation
   - Evidence: Only 3 canonical slots survive from 39 surface nodes. The canonical advanced chain loses all product-specific and situation-specific detail.
   - Expected impact: More canonical slots would make `meta.saturation.canonical` a meaningful signal (currently always 100%) and improve canonical chain quality.

5. **Elaborate monoculture despite -0.7 repetition brake** → Strengthen brake or add diversity-forcing signal
   - Evidence: elaborate fires 6/10 turns (55%) despite `interview.strategy.self_count: -0.7`. With only 2 conversation-level strategies active, the brake isn't enough to force alternation.
   - Note: This is a *symptom* of the chain topology gating issue. Fixing #1 should naturally diversify strategy selection. Only address directly if diversity doesn't improve after the gate fix.

6. **Social job extraction bias** → Review extraction prompt in `src/llm/prompts/` for social job detection
   - Evidence: Zero `social_job` nodes extracted despite Turn 1 containing clear social-job content ("buying for someone else — thinking about what they'd actually want"). The extraction guidelines include social jobs but the LLM is not producing them.
   - Expected impact: Social job extraction would add a dimension currently missing from all chains.

### Low Priority / Verify

7. **Focus node recording gap** — This simulation pre-dates the focus node tracking fix. Verify on a current run that focus nodes are recorded.
8. **PNG rendering unavailable** — WSL lacks Chrome for mermaid-cli. Graph review is `.mmd`-only. Install puppeteer browsers if PNG output is needed.
