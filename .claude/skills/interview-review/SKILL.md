---
name: interview-review
description: Review a simulated interview export folder to produce qualitative insights. Reads pre-generated transcript, scoring summary, causal chains, and graph data from reports/interviews/<timestamp>/ and writes 06_insights.md with transcript quality, focus fidelity, strategy assessment, causal chain quality, graph health, and actionable recommendations. No CSV/JSON parsing required.
---

# Interview Review

Qualitative review of a simulated interview export. Reads pre-generated artifacts and produces actionable insights.

## Input

An export folder: `reports/interviews/<timestamp>/`

**Required files:**
- `00_meta.yaml` — metadata for context
- `01_transcript.md` — Q&A with strategies and focus nodes
- `02_causal_chains.md` — chain extraction with tier classification
- `04_scoring_summary.md` — aggregated signal tables
- `config/methodologies/<methodology>.yaml` — strategy definitions, node_binding, focus_mode, phases, ontology

**Context docs (reference, not re-read every time):**
- `.claude/context/canonical-slots.md` — canonical chain expectations (sparse by design)
- `.claude/context/chain-rules.md` — chain tier definitions and methodology-specific rules
- `.claude/context/strategy-scoring.md` — signal weight routing, node_binding behavior
- `.claude/context/pipeline-contracts.md` — stage contracts, focus_concept flow
- `.claude/context/methodology-parameter-flow.md` — calibration principles (read §Calibration Principles before making any weight tuning recommendation)

**Optional files (enrich analysis if present):**
- `03_graph.mmd` — graph visualization
- `05_latency/summary.md` — performance data
- `99_session.log` — raw session log

## Output

`06_insights.md` in the same export folder, with six sections:

1. **Transcript Quality** — openness, followership, naturalness, leading, contradictions, tangents, resistance
2. **Focus Node Fidelity** — does each question align with its declared focus node?
3. **Strategy Assessment** — distribution, streaks, phase alignment, score separation, structural failures
4. **Causal Chain Quality** — chain meaningfulness, evidence grounding, business actionability, methodology-specific structural checks
5. **Graph Health** — growth trajectory, orphan dynamics, density, compression
6. **Actionable Recommendations** — specific fixes with module/config pointers

## Usage

```
/interview-review reports/interviews/20260424_183601/
```

If no folder is specified, use the most recent export:
```bash
ls -td reports/interviews/*/ | head -1
```

## Procedure

### Step 1 — Load context

Read `00_meta.yaml` to understand:
- Methodology name (e.g., `jobs_to_be_done_v2`) — this determines which YAML to read
- Concept and persona
- Total turns and status

**Read the methodology YAML** (`config/methodologies/<methodology>.yaml`) to discover:
- **Strategy names and descriptions** — the actual strategy set for this methodology (do NOT assume MEC strategies like `ascend`/`ground`/`bridge` for non-MEC methods)
- **`node_binding`** per strategy (`required` vs `none`) — strategies with `node_binding: none` are conversation-level, not node-bound; they may have empty focus concepts by design
- **`focus_mode`** per strategy (`recent_node`, `summary`, `topic`) — determines how focus is resolved
- **`generates_closing_question`** — strategies that end the interview (e.g., `validate`)
- **Phase signal weights** (`phases.early/mid/late.signal_weights`) — which strategies get phase multipliers and when
- **Ontology node types and levels** — the expected chain structure (terminal types, level ordering)

Read `01_transcript.md` for the full Q&A.

Read `04_scoring_summary.md` for quantitative backing.

### Step 2 — Transcript Quality (Section 1)

Evaluate moderation quality through four diagnostic tiers. Tiers 1–3 apply per-turn; Tier 4 is an end-of-interview structural audit.

---

#### Tier 1 — Structural Integrity (Non-Negotiable)

**Openness**: Is the question open-ended? Flag yes/no or assumed-answer questions → `closed_question`.

**Single-question discipline**: Does each turn ask only one thing? Double-barreled questions split the respondent's attention and contaminate both answers → `double_barreled`.

**Strategy-intent fit**: Does the question match the selected strategy's purpose? Use the strategy `description` from the methodology YAML (discovered in Step 1) as ground truth — each methodology defines its own strategy purposes. A question that executes the *wrong* strategy's intent → `strategy_mismatch`.

**Exhaustion vs. abandonment**: When the interviewer moves on from a node, did the respondent finish their thought (exhaustion) or was the topic still open (abandonment)? Abandonment is the more damaging pattern — it leaves signal on the table. Flag as `premature_abandonment` when the respondent's last answer on a topic was substantive and still expanding.

---

#### Tier 2 — Depth Mechanisms

**Followership**: Does the question build from the respondent's own language? Paraphrasing or echoing key phrases is good. Generic questions that ignore the respondent's specific wording → `followership_failure`.

**Concrete anchoring**: When the respondent gives an abstract answer ("it's convenient", "I just feel better"), does the next question pull them toward a specific incident or behavior? Abstract answers left unanchored flatten the chain. Flag turns where the moderator accepts an abstraction and moves on → `anchoring_missed`.

**Affect acknowledgment**: Emotional signal (hedging, intensity, dismissiveness, self-correction) in the respondent's answer is often more informative than propositional content. When the respondent shows affect ("I guess... I don't know, having a choice?", "I'd probably resent it"), the next question should probe it, not skip to the next topic. Flag missed probes → `affect_missed`.

**Why-chain completion**: For ascend/laddering strategies, does the question push toward root causes (values, identity, fears) or stop at instrumental explanations? Stopping one level short of the terminal node type consistently is a depth failure. Flag per-turn → `shallow_ladder`.

---

#### Tier 3 — Relationship Management

**Naturalness**: Are transitions smooth? Conversation vs. survey feel. **Critical check**: Does the question contain meta-language about the system state ("concept field", "focus node", "cannot generate")? → `system_state_leak` — the LLM received bad input and improvised a meta-response.

**Tone/rapport**: Is the framing interrogative ("Why did you...?") or collaborative ("Help me understand...")?  Interrogative phrasing on sensitive topics increases defensiveness. Flag turns where the question tone seems likely to produce shorter, more guarded answers → `interrogative_tone`.

**Pacing sensitivity**: High-engagement respondent answers (long, elaborative, self-correcting) warrant depth probes. Short, low-engagement answers warrant breadth shifts. When the interviewer applies depth probing to a low-engagement answer or moves on from a high-engagement one → `pacing_mismatch`.

**Leading — three subtypes** (distinguish carefully):
- `leading_direction` — phrasing suggests the expected answer ("Don't you think...?", "Wouldn't you say...?")
- `confirmation_probe` — asking the respondent to confirm what they just said rather than extending the thread (e.g., asking "Does it matter which one you pick?" after the respondent already said they grab whatever's available)
- `projective_overreach` — converting a hypothetical or attitudinal statement from the respondent into a biographical event probe (e.g., respondent says "I'd probably resent it if someone told me what to drink" → interviewer asks "Has there been a time when someone suggested a drink and you wanted it less?" — this mistakes a stated attitude for a lived experience and probes for an event that may never have occurred)

**Contradiction handling**: When the respondent contradicts themselves across turns (or contradicts an earlier turn's concept extraction), does the next question acknowledge the tension? If not → `missed_contradiction`. When the interviewer pivots away from a contradiction to a safer topic → `contradiction_avoided`.

**Tangent management**: When the respondent goes off-topic, does the interviewer redirect? 3+ consecutive tangents without redirecting → `tangent_captured`.

**Resistance adaptation**: When the respondent explicitly redirects ("that's not the main thing"), does the interviewer adapt? 2+ ignored redirects → `resistance_ignored`.

---

#### Tier 4 — Coverage Audit (End-of-Interview Structural Check)

After reviewing all turns, assess:

**Funnel discipline**: Did the interview move through the expected arc — broad exploration → specific probing → validation/closing? Or did it jump to specifics before context was established, or stay stuck in exploration when closure was needed? This is a session-level check, not per-turn.

**Blind spot detection**: Given the concept and methodology ontology, were there obvious adjacent areas that were never touched? For example, a beverage interview that never touches social consumption, health identity, or routine disruption has likely left undiscovered territory. Map the node type distribution against the ontology's expected coverage.

**Over-indexing**: Did one salient concept or node cluster consume a disproportionate share of turns (>40%) at the expense of undiscovered territory? This is structurally different from streaks (which are a strategy-scoring issue) — over-indexing is a breadth failure.

**Social/identity blind spots**: Did the respondent ever signal social, identity, or self-concept dimensions that the interviewer didn't pursue? Flag unprobed social/identity signals → `social_signal_missed`.

---

Output format:
```
## 1. Transcript Quality

Overall: [1-2 sentence summary]

### Flags
- Turn N [strategy]: [issue] — [Tier N: category] [subtype if applicable]

### Behavioral Pattern Summary
- Tangents: [N] detected → [redirected/ignored/captured]
- Contradictions: [N] detected → [resolved/unresolved/avoided]
- Resistance: [N] explicit redirects → [adapted/ignored]
- Affect signals: [N] detected → [probed/missed]
- Abstract answers left unanchored: [N]

### Tier 4 — Coverage Audit
- Funnel discipline: [maintained / jumped early / stuck in exploration]
- Blind spots: [ontology areas never covered]
- Over-indexing: [concept or node cluster that dominated, % of turns]
- Social/identity signals missed: [yes/no + what]

### Strengths
- [What worked, by tier]
```

### Step 3 — Focus Node Fidelity (Section 2)

For each turn with a focus node, cross-reference:
1. Does the question reference or build from the focus node's concept?
2. Given the strategy's intent (from methodology YAML description), does the question plausibly execute it on that node?
3. Does the question pivot to unrelated content from the respondent's answer?

**Special handling for `node_binding: none` strategies**: These strategies (check methodology YAML) are conversation-level — they don't target a specific node. An empty or generic focus concept is expected. Assess whether the question fulfills the strategy's described purpose given the full conversation context, not whether it targets a specific node.

Output format:
```
## 2. Focus Node Fidelity

Fidelity Rate: [N/M turns faithful] — [acceptable/concern]

Mismatches:
- Turn N [strategy]: focus_node="X" but question probes "Y"
  → Likely cause: [LLM attended to tangential content / question generator drift / empty focus concept for node-bound strategy]
  → Fix: src/llm/prompts/ [specific prompt file]

High-Fidelity Turns:
- Turn N [strategy]: focus_node="X", question cleanly builds from "X"
```

**Diagnostic rule**: Fidelity rate < 70% → issue is in question generation, not signal tuning. However, exclude `node_binding: none` turns from the fidelity rate if they had no focus node by design.

### Step 4 — Strategy Assessment (Section 3)

From `04_scoring_summary.md` and the methodology YAML (discovered in Step 1).

**Primary: Missed Strategy Opportunities**

This is the evidence-based assessment. For each turn where the transcript quality
assessment (Step 2) flagged `resistance_ignored`, `affect_missed`, `anchoring_missed`,
or `contradiction_avoided`, check: given what the respondent actually said, which
strategy SHOULD have been selected?

For each candidate missed opportunity, provide:
1. The specific turn number
2. The respondent's own words (quote them)
3. Which strategy should have been selected instead
4. Why the selected strategy was wrong for this response

If no transcript quality flags correlate with strategy failures, state this explicitly —
the strategy distribution may be appropriate for this interview.

**Secondary: Pattern Checks**

These are observations, not calibration findings. They warrant investigation but do
NOT directly justify weight changes without the evidence standard above.

- **Dominance**: Any strategy >50% of turns → cross-reference with missed opportunities
  above. If no missed opportunities were found, dominance may be appropriate.
- **Streaks**: Same strategy 4+ consecutive turns → check whether any of those turns
  showed resistance, fatigue, or hedging that should have triggered a pivot. If the
  respondent stayed on-topic and engaged, the streak may be appropriate.
- **Missing strategies**: Note strategies that never fired. Check `04_scoring_summary.md`
  Dead Signals table — if the strategy's key signal is dead, the fix is signal detection,
  not weight tuning.
- **Phase alignment**: Check the methodology YAML's `phases` section for per-phase
  strategy multipliers. Compare against phase descriptions.
- **`node_binding` awareness**: Strategies with `node_binding: none` are conversation-level.
  If a `node_binding: none` strategy has `convgraph.node.*` weights, flag as
  `node_binding_mismatch` — those weights are dead.
- **Score separation**: Top-2 scores within 0.30 consistently → selection is near-random.
  Use `04_scoring_summary.md` Per-Turn Score Separation table to identify turns where
  the gap was narrow and which signals drove the outcome.

**Methodology fidelity audit**: Use the ontology from the methodology YAML:
- Check the terminal node type(s) from the ontology (nodes with `terminal: true`)
- After 8+ turns, at least one chain should reach a terminal node type
- If the methodology has chain-aware strategies (check `valid_when` gates in YAML),
  verify those strategies fired at least once
- If the methodology has flat ontology, laddering strategies are not expected

Output format:
```
## 3. Strategy Assessment

### Missed Strategy Opportunities
- Turn N: respondent said "[quote]" → [needed strategy] should have been selected
  instead of [selected strategy] because [reason]
- (If none found, state: "No missed strategy opportunities identified — strategy
  selection was consistent with respondent's answers.")

### Distribution
| Strategy | Count | % | Notes |
|----------|-------|---|-------|
... (use actual strategy names from methodology YAML)

Phase Alignment: [aligned / misaligned]
Score Separation: [healthy / unstable]
Structural Fidelity: [pass / failure]

Pattern Observations (verify, do not act without evidence):
- [observation] → investigate with interview-simulation-reviewer Part 4
```

### Step 5 — Causal Chain Quality (Section 4)

Read `02_causal_chains.md`. This is the core analysis — chains are the interview's deliverable. Assess four dimensions:

#### 5a. Structural Completeness

From the Chain completeness summary table:
- **Full chains** (reaching terminal node type) vs. total chains. Ratio < 20% after 8+ turns → `low_chain_completion`.
- **Started-only chains**: Many started chains with no full chains = interviewer can't ladder. Cross-reference with strategy assessment — if laddering strategies barely fired, that's the cause.
- **Canonical chains**: Per `.claude/context/canonical-slots.md`, canonical chains are expected to be sparse and incomplete — they aggregate surface edges through slot mappings, which is inherently lossy. Do NOT flag low canonical chain counts as an issue. Focus chain quality assessment exclusively on surface chains. Only mention canonical chains for cross-persona/multi-run analysis.

#### 5b. Chain Meaningfulness

For each **full chain** (and the top 3 started chains by length), evaluate:

**Semantic coherence**: Does the chain tell a coherent causal story? A chain like `sluggish afternoon → chose ZeroFizz → avoiding caffeine → feel less guilty → guilt-free indulgence` is coherent. A chain like `afternoon fatigue → chose ZeroFizz → chemical aftertaste` is incoherent (solution→pain_point going backwards).

**Edge plausibility**: For each edge in the chain, does the stated relationship match the semantic connection between source and target? Use the edge type definitions from the methodology YAML's `ontology.edges` section as ground truth. Flag implausible edges as `misclassified_edge`.

**Evidence grounding**: Does the chain have source quotes for its edges? All edges showing `(no quote)` = extraction produced relationships without textual evidence. Flag as `ungrounded_chain`. Rate:
- Strong: all edges have supporting quotes that clearly substantiate the relationship
- Moderate: most edges have quotes, some are weak/inferential
- Weak: majority of edges lack quotes or quotes don't substantiate the claimed relationship

**Distinctness**: Do chains represent genuinely different causal narratives, or are they minor variations of the same path? Flag chains sharing ≥ 60% of nodes as `redundant_chains`.

#### 5c. Business Actionability

For each full chain, assess whether the insights could inform a product or marketing decision:

**Specificity**: Does the chain identify a concrete user behavior, context, or pain point? "feel less guilty about drinking a soda" is specific and actionable. "mental shift toward guilt-free indulgence" is vague and tautological.

**Leverage points**: Does the chain reveal where product or positioning changes could influence the outcome? A chain reaching `permission to pause and do nothing without guilt` reveals a ritual/permission job — actionable for positioning. A chain that ends at a generic emotional job with no behavioral anchor is not.

**Competitive differentiation**: Does the chain reveal why this solution vs. alternatives? Chains involving competitive framing show differentiation. Chains that only describe internal states without reference to alternatives don't.

**Business insight summary**: Synthesize the chains into 2-4 distinct business insights. Each insight should be a one-sentence statement a product manager could act on, with the supporting chain(s) cited.

#### 5d. Methodology-Specific Chain Checks

Read the methodology YAML (discovered in Step 1) for the ontology structure. Apply evaluation rules based on the actual ontology levels and terminal node types, not hardcoded assumptions:

- **Chains should progress through ontology levels** toward the terminal node type(s). Check whether full chains reach terminal types.
- **Chains that skip levels** are structurally valid but analytically thin — flag based on methodology expectations.
- **Circular chains** (looping back to lower levels) indicate the interviewer is re-treading ground — flag as `circular_chain`.
- **Shortcut chains** (jumping from L0 directly to terminal) indicate the laddering was too aggressive — flag as `shortcut_chain`.

Derive expected counts from the methodology YAML's `chain_completion` section if present (e.g., `expected_branching`, `score_threshold`).

Output format:
```
## 4. Causal Chain Quality

### Structural Completeness
- Full chains: [N/M] ([%]) — [sufficient / insufficient]
- [flags if applicable]

### Chain-by-Chain Assessment

| Chain | Tier | Coherence | Evidence | Actionable | Key Issue |
|-------|------|-----------|----------|------------|-----------|
| Chain 1 [surface] | full | strong / moderate / weak | strong / moderate / weak | yes / partial / no | [issue or —] |
...

### Meaningful Chains (highlight)
- **Chain N**: [one-line causal narrative] → [business insight]
  - Strengths: [what makes this chain valuable]
  - Gaps: [what's missing that would strengthen it]

### Business Insights
1. [Insight statement] — supported by Chain(s) N, N
2. [Insight statement] — supported by Chain(s) N
...

### Methodology-Specific Assessment
- [methodology-specific finding, referencing ontology from YAML]
- [flags: circular_chain, shortcut_chain, etc.]

### Orphan Analysis
- [N orphan nodes — why they didn't connect into chains]
- [Could the interviewer have connected them? Reference transcript turns where orphans were introduced]
```

**Diagnostic rules**:
- Zero business-actionable insights → interview failed its purpose regardless of other metrics
- All chains ungrounded (no quotes) → extraction quality issue, not interviewer issue
- Chains present but no full chains → interviewer never ascended far enough (cross-ref strategy assessment)

### Step 6 — Graph Health (Section 5)

From the transcript's graph metrics (in `01_transcript.md` Overview or `04_scoring_summary.md`):

**Growth trajectory**: Nodes growing each turn? Stalling = extraction failure.

**Orphan dynamics**: Spikes that resolve = OK. Persistent orphans = dedup threshold issue.

**Density**: Edge/node ratio. < 0.5 = sparse; 1.0–2.0 = healthy.

**Node type balance**: One type > 70% = extraction bias.

Output format:
```
## 5. Graph Health

- Growth: [healthy / stalled at turn N]
- Orphans: [peak=X%, final=X%]
- Density: [X] edge/node
- Node type balance: [balanced / X over-represented]
```

### Step 7 — Recommendations (Section 6)

Consolidate all findings into prioritized fixes, separated by whether they require
quantitative verification before implementation.

**Weight tuning candidates** require evidence from Step 4's missed strategy opportunities.
Each MUST cite a specific turn, respondent quote, and explanation of why the selected
strategy was wrong. Before implementation, cross-reference with
`interview-simulation-reviewer` Part 4 to verify that the needed strategy's signals
actually fired on that turn.

**Prompt/behavior fixes** are transcript quality issues — the strategy was correct but
the question was poorly executed. These don't need verification.

```
## 6. Actionable Recommendations

### Weight Tuning Candidates ⚠ (require quantitative verification)
Each recommendation below identifies a potential strategy selection failure.
BEFORE implementing, verify with interview-simulation-reviewer Part 4 that the
needed strategy's key signals fired on the cited turn. If they didn't fire, the
fix is in signal detection, not weights.

1. **[Needed strategy] should have been selected on Turn N instead of [selected]**
   - Respondent said: "[exact quote]"
   - Why [selected] was wrong: [explanation]
   - Key signals to verify: [signal names]
   - If signals didn't fire → investigate [signal detector file]

### Prompt / Behavior Fixes (no verification needed)
These are question quality issues — the strategy was correct, execution was flawed.

1. Turn N: [leading / contradiction_avoided / projective_overreach / etc.]
   → Fix in [prompt file or methodology YAML section]
   - Evidence: "[respondent quote or question excerpt]"

### Systemic Issues (no verification needed)
Dead signals, always-firing signals, gate blockages from 04_scoring_summary.md.

1. [Dead signal] → investigate [signal detector file]
```

## Rules

1. **No Python, no pandas, no CSV parsing.** All quantitative data comes from `04_scoring_summary.md` tables.
2. **Read the methodology YAML first.** Before assessing any strategy, read `config/methodologies/<methodology>.yaml` to discover the actual strategy names, descriptions, `node_binding` settings, `focus_mode`, `generates_closing_question`, phase weights, and ontology structure. Never assume MEC strategy names for a non-MEC methodology.
3. **Reference context docs for subsystem behavior.** `.claude/context/canonical-slots.md` governs canonical chain expectations. `.claude/context/chain-rules.md` governs chain tier definitions. `.claude/context/strategy-scoring.md` governs signal weight routing. When in doubt about subsystem behavior, check the context doc rather than inventing an assumption.
4. **Cross-reference transcript turns with scoring data.** The same turn appears in both `01_transcript.md` (qualitative) and `04_scoring_summary.md` (quantitative).
5. **Be specific with fix pointers.** "Check config" is not enough — name the file and the key. Use the methodology YAML for config changes, the relevant `.claude/context/` doc for subsystem context.
6. **Flag structural failures loudly.** A methodology that never reaches its terminal node types is a structural failure, not a minor tuning issue.
7. **`node_binding: none` strategies are different.** They don't target specific nodes. Empty/generic focus concepts are expected. Don't flag missing focus nodes for these strategies — flag whether the question fulfills the strategy's described purpose.
8. **Use the leading subtype taxonomy.** Never label a question simply "leading" — distinguish `leading_direction`, `confirmation_probe`, and `projective_overreach`. These have different root causes and different prompt fixes.
9. **Tier 1 failures outrank Tier 2–4.** In the recommendations section, closed questions, double-barreled questions, and strategy mismatches are High Priority. Tier 2 depth failures (missed affect, unanchored abstractions) are Medium Priority. Tier 4 coverage issues are Medium-Low unless a critical blind spot exists.
10. **Exhaustion vs. abandonment requires the respondent's last answer on a topic.** Don't flag abandonment unless the respondent's final answer on that node was still substantive (>15 words, introduced a new concept, or ended with a trailing thought). Short disengaged answers indicate exhaustion, not abandonment.
11. **Weight tuning recommendations require turn-level evidence.** Before recommending any weight change, identify: (a) the specific turn where a different strategy should have been selected, (b) the respondent's own words that demonstrate the need, and (c) why the selected strategy was wrong for that response. If you can't provide all three, the issue is a pattern observation, not a calibration finding — label it "Verify" priority, not "High." Weight changes proposed without this evidence must include a cross-reference to `interview-simulation-reviewer` Part 4 to verify that the needed strategy's signals actually fired on that turn. See `.claude/context/methodology-parameter-flow.md` §Calibration Principles for the full evidence standard.
