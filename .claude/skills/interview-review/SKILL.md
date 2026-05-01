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

For each turn, assess:

**Openness**: Is the question open-ended? Flag yes/no or assumed-answer questions.

**Followership**: Does the interviewer follow the respondent's thread?

**Naturalness**: Are transitions smooth? Conversation vs. survey feel. **Critical check**: Does the question contain meta-language about the system state ("concept field", "focus node", "cannot generate")? If yes → `system_state_leak` — the LLM received bad input and improvised a meta-response.

**Leading**: Does phrasing suggest the expected answer?

**Strategy-intent fit**: Does the question match the selected strategy's purpose? Use the strategy `description` from the methodology YAML (discovered in Step 1) as the ground truth for what each strategy is supposed to do. Do NOT use hardcoded MEC strategy definitions — each methodology defines its own strategy purposes.

**Contradiction handling**: When the respondent contradicts themselves across turns, does the next question acknowledge it? If not → flag `missed_contradiction`.

**Tangent management**: When the respondent goes off-topic, does the interviewer redirect? 3+ consecutive tangents without redirecting → `tangent_captured`.

**Resistance adaptation**: When the respondent explicitly redirects ("that's not the main thing"), does the interviewer adapt? 2+ ignored redirects → `resistance_ignored`.

Output format:
```
## 1. Transcript Quality

Overall: [1-2 sentence summary]

Flags:
- Turn N [strategy]: [issue] — [category]

Behavioral Pattern Summary:
- Tangents: [N] detected → [redirected/ignored/captured]
- Contradictions: [N] detected → [resolved/unresolved]
- Resistance: [N] explicit redirects → [adapted/ignored]

Strengths:
- [What worked]
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

From `04_scoring_summary.md` and the methodology YAML (discovered in Step 1):

**Distribution**: Use the actual strategy names from the methodology YAML. Any strategy > 50% of turns = monotony risk. Note strategies that never fired — cross-reference with their signal weights to check for dead signals.

**Streaks**: Same strategy 4+ consecutive turns without penalty = stale.

**Phase alignment**: Check the methodology YAML's `phases` section for per-phase strategy multipliers. The transcript's turn-by-turn strategy list shows which strategies fired in each phase. Compare against the phase descriptions — e.g., early phase should prioritize breadth/grounding strategies, mid phase should prioritize depth/laddering strategies, late phase should prioritize validation/closing strategies. The specific strategy names and their phase-appropriate roles are defined in the methodology YAML.

**`node_binding` awareness**: Strategies with `node_binding: none` (check YAML) are conversation-level — they compete on global signals only. Their node-scoped weights are stripped before scoring. If a `node_binding: none` strategy has `convgraph.node.*` weights, those weights are dead. Flag as `node_binding_mismatch`.

**Score separation**: Top-2 scores within 0.30 consistently = near-random selection.

**Methodology fidelity audit**: Use the ontology from the methodology YAML to determine what constitutes structural success:
- Check the terminal node type(s) from the ontology (nodes with `terminal: true`)
- After 8+ turns, at least one chain should reach a terminal node type
- If the methodology has chain-aware strategies (check `valid_when` gates in YAML), verify those strategies fired at least once
- If the methodology has flat ontology (no chain topology), laddering strategies are not expected — breadth strategies should dominate

Output format:
```
## 3. Strategy Assessment

Distribution: [aligned / issues]
| Strategy | Count | % | Assessment |
|----------|-------|---|------------|
... (use actual strategy names from methodology YAML)

Phase Alignment: [aligned / misaligned]
- [specific issues, referencing phase weights from YAML]

Score Separation: [healthy / unstable]

Structural Fidelity: [pass / failure]
- [methodology-specific finding, referencing ontology from YAML]

Anomalies:
- [finding] → [module or config to investigate]
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

Consolidate all findings into prioritized fixes. When pointing to a fix location, use the methodology YAML for config changes and reference relevant `.claude/context/` docs for subsystem context.

```
## 6. Actionable Recommendations

### High Priority
1. [Issue] → Fix in [file path]
   - Evidence: [specific turn or metric]
   - Expected impact: [what changes if fixed]

### Medium Priority
...

### Low Priority / Verify
...
```

## Rules

1. **No Python, no pandas, no CSV parsing.** All quantitative data comes from `04_scoring_summary.md` tables.
2. **Read the methodology YAML first.** Before assessing any strategy, read `config/methodologies/<methodology>.yaml` to discover the actual strategy names, descriptions, `node_binding` settings, `focus_mode`, `generates_closing_question`, phase weights, and ontology structure. Never assume MEC strategy names for a non-MEC methodology.
3. **Reference context docs for subsystem behavior.** `.claude/context/canonical-slots.md` governs canonical chain expectations. `.claude/context/chain-rules.md` governs chain tier definitions. `.claude/context/strategy-scoring.md` governs signal weight routing. When in doubt about subsystem behavior, check the context doc rather than inventing an assumption.
4. **Cross-reference transcript turns with scoring data.** The same turn appears in both `01_transcript.md` (qualitative) and `04_scoring_summary.md` (quantitative).
5. **Be specific with fix pointers.** "Check config" is not enough — name the file and the key. Use the methodology YAML for config changes, the relevant `.claude/context/` doc for subsystem context.
6. **Flag structural failures loudly.** A methodology that never reaches its terminal node types is a structural failure, not a minor tuning issue.
7. **`node_binding: none` strategies are different.** They don't target specific nodes. Empty/generic focus concepts are expected. Don't flag missing focus nodes for these strategies — flag whether the question fulfills the strategy's described purpose.
