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
- Methodology (MEC/JTBD/CIT/RG/CJM)
- Concept and persona
- Total turns and status

Read `01_transcript.md` for the full Q&A.

Read `04_scoring_summary.md` for quantitative backing.

### Step 2 — Transcript Quality (Section 1)

For each turn, assess:

**Openness**: Is the question open-ended? Flag yes/no or assumed-answer questions.

**Followership**: Does the interviewer follow the respondent's thread?

**Naturalness**: Are transitions smooth? Conversation vs. survey feel.

**Leading**: Does phrasing suggest the expected answer?

**Strategy-intent fit**: Does the question match the selected strategy's purpose?
- `ascend` → probe upward (why does this matter?)
- `ground` → probe downward (what specifically?)
- `bridge` → connect levels
- `branch` → explore alternatives
- `anchor` → attach orphan nodes
- `revitalize` → re-engage (not introduce new topics)

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
2. Given the strategy's intent, does the question plausibly execute it on that node?
3. Does the question pivot to unrelated content from the respondent's answer?

Output format:
```
## 2. Focus Node Fidelity

Fidelity Rate: [N/M turns faithful] — [acceptable/concern]

Mismatches:
- Turn N [strategy]: focus_node="X" but question probes "Y"
  → Likely cause: [LLM attended to tangential content / question generator drift]
  → Fix: src/llm/prompts/ [specific prompt file]

High-Fidelity Turns:
- Turn N [strategy]: focus_node="X", question cleanly builds from "X"
```

**Diagnostic rule**: Fidelity rate < 70% → issue is in question generation, not signal tuning.

### Step 4 — Strategy Assessment (Section 3)

From `04_scoring_summary.md`:

**Distribution**: Any strategy > 50% of turns = monotony risk.

**Streaks**: Same strategy 4+ consecutive turns without penalty = stale.

**Phase alignment** (check methodology YAML for boundaries and expected strategies):
- MEC: `branch`/`ground`/`anchor` early → `ascend`/`bridge` mid → `ascend`/`revitalize` late
- JTBD: `explore_situation` early → `dig_motivation`/`uncover_obstacles` mid → `validate_outcome` late
- Read actual YAML for other methodologies

**Score separation**: Top-2 scores within 0.30 consistently = near-random selection.

**Methodology fidelity audit**:
- **MEC**: At least one chain reaching instrumental/terminal value after 8+ turns? If `max_depth < 3` → `structural_failure`.
- **CIT**: Concrete incident with situation/action/outcome? No depth ≥ 3 chain → `structural_failure`.
- **RG**: At least one triadic comparison (3+ elements)? All dyadic → `structural_failure`.
- **CJM**: At least 3 distinct journey stages? All in one stage → `structural_failure`.
- **JTBD**: At least one emotional/social job? No terminal nodes after 8+ turns → `structural_failure`.

Output format:
```
## 3. Strategy Assessment

Distribution: [aligned / issues]
| Strategy | Count | % | Assessment |
|----------|-------|---|------------|
...

Phase Alignment: [aligned / misaligned]
- [specific issues]

Score Separation: [healthy / unstable]

Structural Fidelity: [pass / failure]
- [methodology-specific finding]

Anomalies:
- [finding] → [module or config to investigate]
```

### Step 5 — Causal Chain Quality (Section 4)

Read `02_causal_chains.md`. This is the core analysis — chains are the interview's deliverable. Assess four dimensions:

#### 5a. Structural Completeness

From the Chain completeness summary table:
- **Full chains** (reaching terminal node type) vs. total chains. Ratio < 20% after 8+ turns → `low_chain_completion`.
- **Started-only chains**: Many started chains with no full chains = interviewer can't ladder. Cross-reference with strategy assessment — if `ascend` barely fired, that's the cause.
- **Canonical vs. surface disparity**: If canonical has zero full chains but surface has several, dedup is collapsing meaningful variation. Flag as `over_aggressive_dedup`.

#### 5b. Chain Meaningfulness

For each **full chain** (and the top 3 started chains by length), evaluate:

**Semantic coherence**: Does the chain tell a coherent causal story? A chain like `sluggish afternoon → chose ZeroFizz → avoiding caffeine → feel less guilty → guilt-free indulgence` is coherent. A chain like `afternoon fatigue → chose ZeroFizz → chemical aftertaste` is incoherent (solution→pain_point going backwards).

**Edge plausibility**: For each edge in the chain, does the stated relationship (`triggers`, `enables`, `supports`, `addresses`) match the semantic connection between source and target?
- `triggers` should connect cause → effect
- `enables` should connect enabler → enabled outcome
- `addresses` should connect solution → problem it solves
- Flag implausible edges as `misclassified_edge`.

**Evidence grounding**: Does the chain have source quotes for its edges? All edges showing `(no quote)` = extraction produced relationships without textual evidence. Flag as `ungrounded_chain`. Rate:
- Strong: all edges have supporting quotes that clearly substantiate the relationship
- Moderate: most edges have quotes, some are weak/inferential
- Weak: majority of edges lack quotes or quotes don't substantiate the claimed relationship

**Distinctness**: Do chains represent genuinely different causal narratives, or are they minor variations of the same path? Flag chains sharing ≥ 60% of nodes as `redundant_chains`.

#### 5c. Business Actionability

For each full chain, assess whether the insights could inform a product or marketing decision:

**Specificity**: Does the chain identify a concrete user behavior, context, or pain point? "feel less guilty about drinking a soda" is specific and actionable. "mental shift toward guilt-free indulgence" is vague and tautological.

**Leverage points**: Does the chain reveal where product or positioning changes could influence the outcome? A chain reaching `permission to pause and do nothing without guilt` reveals a ritual/permission job — actionable for positioning. A chain that ends at a generic emotional job with no behavioral anchor is not.

**Competitive differentiation**: Does the chain reveal why this solution vs. alternatives? Chains involving `choosing ZeroFizz over plain water` or `avoiding coffee despite needing a pick-me-up` show competitive framing. Chains that only describe internal states without reference to alternatives don't.

**Business insight summary**: Synthesize the chains into 2-4 distinct business insights. Each insight should be a one-sentence statement a product manager could act on, with the supporting chain(s) cited.

#### 5d. Methodology-Specific Chain Checks

Apply methodology-aware evaluation rules:

- **MEC**: Full chains should follow attribute → functional consequence → psychosocial consequence → instrumental value → terminal value. A chain that skips levels (attribute → terminal value) is structurally valid but analytically thin — flag as `shortcut_chain`. Expected: at least 3 chains of depth ≥ 4 after 10+ turns.

- **JTBD**: Full chains should connect job_trigger/pain_point → solution_approach → gain_point → emotional_job/social_job. Chains ending at gain_point without reaching emotional/social job = incomplete job understanding. Expected: at least 2 chains reaching emotional_job or social_job after 8+ turns. Chains that only connect pain_point → solution_approach → pain_point (circular) = `circular_chain`.

- **CIT**: Full chains should represent incident → action → outcome narrative. Chains that don't include a concrete behavioral action = `no_incident_chain`. Expected: at least 1 chain with situation → behavior → consequence after 8+ turns.

- **CJM**: Full chains should traverse multiple journey stages. Chains staying within one stage = `single_stage_chain`. Expected: at least 2 chains spanning 3+ journey stages.

- **RG**: Full chains should show construct → implication relationships. Chains that only connect elements without revealing underlying constructs = `surface_comparison`. Expected: at least 1 chain revealing a latent construct.

Output format:
```
## 4. Causal Chain Quality

### Structural Completeness
- Full chains: [N/M] ([%]) — [sufficient / insufficient]
- Surface vs. Canonical: [comment on dedup impact]
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
- [methodology-specific finding]
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

Consolidate all findings into prioritized fixes:

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
2. **Read the methodology YAML** for phase boundaries and strategy names. Do not assume MEC strategy names for a JTBD interview.
3. **Cross-reference transcript turns with scoring data.** The same turn appears in both `01_transcript.md` (qualitative) and `04_scoring_summary.md` (quantitative).
4. **Be specific with fix pointers.** "Check config" is not enough — name the file and the key.
5. **Flag structural failures loudly.** A MEC interview that never ladders is a methodology failure, not a minor tuning issue.
