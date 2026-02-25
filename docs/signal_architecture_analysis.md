# Signal Architecture Analysis: Roles, Effectiveness, and Design Implications

**Date:** 2026-02-25
**Scope:** All signal types across MEC, JTBD, and Critical Incident methodologies
**Evidence:** Cross-run analysis (20260225_cross_run_analysis.md), codebase exploration, scoring decomposition CSVs

---

## 1. Signal Taxonomy

The system uses 5 signal families, each with distinct scope, cost, and refresh semantics.

### 1.1 Complete Signal Map

| Family | Signal | Type | Scope | Cost | Differentiates Strategies? |
|--------|--------|------|-------|------|---------------------------|
| **LLM** | `llm.response_depth` | Categorical (string) | Global | High | Only via asymmetric weights |
| | `llm.engagement` | Float [0,1] | Global | High | Only via asymmetric weights |
| | `llm.valence` | Float [0,1] | Global | High | Only via asymmetric weights |
| | `llm.certainty` | Float [0,1] | Global | High | Only via asymmetric weights |
| | `llm.specificity` | Float [0,1] | Global | High | Only via asymmetric weights |
| | `llm.intellectual_engagement` | Float [0,1] | Global | High | Only via asymmetric weights |
| | `llm.global_response_trend` | Categorical (string) | Global | Low | Only via asymmetric weights |
| **Graph** | `graph.node_count` | Int | Global | Free | No (not used in weights) |
| | `graph.edge_count` | Int | Global | Free | No (not used in weights) |
| | `graph.orphan_count` | Int | Global | Free | No (not used in weights) |
| | `graph.max_depth` | Float [0,1] | Global | Free | Only via asymmetric weights |
| | `graph.chain_completion` | Float/Bool | Global | Free | Only via asymmetric weights |
| | `graph.canonical_*` | Various | Global | Low | No (not used in weights) |
| **Node** | `graph.node.exhaustion_score` | Float [0,1] per node | Per-node | Low | **Yes** — different per node |
| | `graph.node.focus_streak` | Categorical per node | Per-node | Low | **Yes** — different per node |
| | `graph.node.yield_stagnation` | Bool per node | Per-node | Low | **Yes** — different per node |
| | `graph.node.is_orphan` | Bool per node | Per-node | Low | **Yes** — different per node |
| | `graph.node.has_outgoing` | Bool per node | Per-node | Low | **Yes** — different per node |
| | `graph.node.recency_score` | Float [0,1] per node | Per-node | Low | **Yes** — different per node |
| | `graph.node.edge_count` | Int per node | Per-node | Low | **Yes** — different per node |
| | `graph.node.is_current_focus` | Bool per node | Per-node | Low | **Yes** — different per node |
| | `graph.node.exhausted` | Bool per node | Per-node | Low | **Yes** — different per node |
| | `meta.node.opportunity` | Categorical per node | Per-node | Low | **Yes** — different per node |
| | `technique.node.strategy_repetition` | Categorical per node | Per-node | Low | **Yes** — different per node |
| **Temporal** | `temporal.strategy_repetition_count` | Float [0,1] | Global | Free | Only via asymmetric weights |
| | `temporal.turns_since_strategy_change` | Float [0,1] | Global | Free | Only via asymmetric weights |
| **Meta** | `meta.interview.phase` | Categorical (string) | Global | Free | Via phase multipliers |
| | `meta.interview_progress` | Float [0,1] | Global | Free | Only via asymmetric weights |
| | `meta.conversation.saturation` | Float [0,1] | Global | Low | Only via asymmetric weights |
| | `meta.canonical.saturation` | Float [0,1] | Global | Low | Only via asymmetric weights |

### 1.2 Normalization Paths

Signals reach the scoring engine via two distinct normalization pipelines:

```
LLM Signals (1-5 Likert scale from LLM rubric):
  ├─ response_depth → CATEGORICAL: {1: "surface", 2: "shallow", 3: "moderate", 4: "deep", 5: "deep"}
  └─ all others     → CONTINUOUS:  (score - 1) / 4 → [0.0, 0.25, 0.50, 0.75, 1.0]

Scoring Engine (_get_signal_value):
  ├─ Direct match:     "graph.node_count" → signals["graph.node_count"] (raw value)
  ├─ Threshold binning: "engagement.low" → signals["engagement"] ≤ 0.25 → True/False
  │                     "engagement.mid" → 0.25 < signals["engagement"] < 0.75 → True/False
  │                     "engagement.high" → signals["engagement"] ≥ 0.75 → True/False
  └─ String match:     "response_depth.moderate" → signals["response_depth"] == "moderate" → True/False
```

`★ Insight ─────────────────────────────────────`
**The threshold binning creates a hidden quantization.** A continuous signal like engagement (0.0-1.0) becomes a 3-level categorical (low/mid/high) when used with `.low`/`.mid`/`.high` suffixes. A respondent at engagement=0.74 ("mid") and one at 0.76 ("high") trigger completely different weight sets. This cliff effect means the system's behavior can change dramatically at boundary values, making it hard to reason about gradual transitions.
`─────────────────────────────────────────────────`

---

## 2. The Global Signal Problem

### 2.1 Why Global Signals Cannot Differentiate Strategies

The scoring formula for a (strategy, node) pair is:

```
base_score = Σ(signal_value × weight) for each signal in strategy.signal_weights
final_score = (base_score × phase_multiplier) + phase_bonus
```

When signal_value is identical for all candidates at a given turn (global signal), and the weight differs between strategies, the signal creates a **fixed offset** between strategies:

```
Turn 5: engagement = 0.75 → "high" = True

deepen:  contribution = True × 0.5 = +0.5
explore: contribution = True × 0.0 = +0.0  (no weight for engagement.high)
clarify: contribution = True × 0.0 = +0.0
reflect: contribution = True × 0.0 = +0.0

Net effect: deepen gets +0.5 over others. Same every turn engagement is high.
```

This offset is **invariant** — it doesn't change across nodes, only across turns when the signal value changes. Importantly, it cannot influence WHICH node is selected, only which strategy.

### 2.2 When Global Signals Are and Aren't Useful

**Useful** (asymmetric weights create meaningful differentiation):

| Signal | Strategy with unique weight | Others | Delta | Meaningful? |
|--------|---------------------------|--------|-------|-------------|
| `llm.engagement.low` | deepen: -0.5, revitalize: +0.8 | others: 0 | 1.3 swing | **Yes** — safety gate for deepen, trigger for revitalize |
| `llm.valence.low` | uncover_obstacles: +0.9 | explore: +0.3, revitalize: +0.5 | 0.6 over next | **Yes** — strong trigger for obstacle detection |
| `llm.certainty.high` | clarify_assumption: +0.8 | others: 0 | 0.8 unique | **Yes** — unique trigger for challenging confident claims |

**Not useful** (symmetric weights or weights too similar):

| Signal | Weights across strategies | Problem |
|--------|--------------------------|---------|
| `temporal.strategy_repetition_count` | -0.3 on most MEC strategies | Same penalty for all → flat offset, no differentiation |
| `llm.engagement.mid` | +0.3-0.4 on most strategies | Similar weights → near-flat offset |
| `meta.conversation.saturation` | +0.5 on reflect/validate only | Used by only 1-2 strategies — creates flat bonus, not a trade-off |

### 2.3 The "Global Signal Budget" Problem

In cross-run analysis, **21 of 29 signals** used in MEC scoring were identified as global. These consume weight budget (column space in the scoring matrix) without producing ranking differentiation. The global contribution often exceeds the node-level contribution, meaning the overall score is dominated by a signal type that cannot rank candidates.

**Observed in MEC scoring CSV:**
- Global signal contributions: ~70% of total score mass
- Node signal contributions: ~20% of total score mass
- Phase multiplier effect: ~10% swing (but enough to dominate ranking)

This means the system is doing expensive LLM inference to compute signals that primarily add noise to the ranking function.

---

## 3. Signal Roles: What Each Family Should Do

### 3.1 LLM Signals — Respondent State Assessment

**Current role:** Mixed (used for both strategy scoring and safety gating)
**Recommended role:** **Safety gates + strategy triggers** (but NOT node selection)

LLM signals measure the respondent's current cognitive and emotional state. They answer: "Is this person engaged? Comfortable? Deep in thought? Confused?"

**What they're good for:**
- **Safety gates:** "Don't deepen when engagement < 0.25" — prevents pushing a disengaged respondent
- **Strategy triggers:** "Negative valence → surface obstacles" — maps respondent emotion to interviewer intent
- **Phase transitions:** "Shallowing trend → consider reflecting or revitalizing" — detects fatigue

**What they're NOT good for:**
- **Node selection:** LLM signals say nothing about which node to focus on. They describe the respondent's response, not the graph's topology.
- **Fine-grained ranking:** The 5-level Likert scale (quantized to 3 bins via threshold) is too coarse to meaningfully rank 5+ strategies. At best it can gate 2-3 strategies.

**Design implication:** LLM signals should use **binary gating** (enable/disable a strategy) rather than **weighted scoring** (add/subtract fractional points). Example:

```yaml
# Current: fractional weights create false precision
llm.engagement.high: 0.5    # adds +0.5 when engagement ≥ 0.75
llm.engagement.mid: 0.3     # adds +0.3 when 0.25 < engagement < 0.75
llm.engagement.low: -0.5    # subtracts when engagement ≤ 0.25

# Better conceptual model: gates
# IF engagement.low → SUPPRESS deepen (hard gate)
# IF engagement.high → ENABLE deepen (no penalty)
# Otherwise → neutral
```

The current fractional weights (0.3, 0.4, 0.5) suggest precision that doesn't exist. The LLM's rubric score has ~±1 point noise, and the 3-bin quantization collapses the 5-point scale further. The difference between 0.3 and 0.5 weights on a binary True/False signal is 0.2 points — well within scoring noise.

### 3.2 Node Signals — Exploration State

**Current role:** Node selection within joint (strategy, node) scoring
**Recommended role:** **Primary node selector** — should dominate node choice

Node signals measure each concept's exploration state: how exhausted, how recently focused, how connected. They answer: "Which node needs attention?"

**What they're good for:**
- **Node rotation:** Exhaustion score, focus streak, yield stagnation → rotate away from over-explored nodes
- **Structural targeting:** Orphan nodes, nodes without outgoing edges → target for connection-building
- **Recency awareness:** Recency score → balance between revisiting and exploring

**What they're NOT good for:**
- **Strategy selection:** A node's exhaustion level shouldn't determine whether to deepen vs explore. A fresh node could benefit from either strategy depending on the respondent's engagement level.

**The current conflation problem:** In joint scoring, node signals contribute to BOTH strategy and node ranking simultaneously. Example:

```yaml
# deepen strategy weights
graph.node.exhaustion_score.low: 1.0   # Fresh nodes get +1.0 for deepen
graph.node.focus_streak.low: 0.5       # Low streak gets +0.5 for deepen

# explore strategy weights
graph.node.focus_streak.none: 0.6      # Zero streak gets +0.6 for explore
graph.node.exhaustion_score.low: 0.4   # Fresh nodes get +0.4 for explore
```

A fresh node (exhaustion=0.05, streak=none) scores:
- deepen: +1.0 (exhaustion.low) + 0.0 (streak.low doesn't match "none") = +1.0
- explore: +0.4 (exhaustion.low) + 0.6 (streak.none) = +1.0

The node signals cancel out — the strategies are tied on node contribution. Strategy selection falls back to global signals and phase multipliers, which is exactly the problem we observed.

**Design implication:** Consider **separating node selection from strategy selection**:
1. First: rank strategies based on respondent state (LLM signals, temporal signals, phase)
2. Then: select the best node for the chosen strategy based on node signals

This two-stage approach prevents the conflation where node signals accidentally determine strategy (because deepen has a higher exhaustion bonus) and strategy signals accidentally determine node (because reflect's phase bonus makes a particular node win).

### 3.3 Temporal Signals — Diversity Enforcement

**Current role:** Repetition penalties for strategy diversity
**Recommended role:** **Monotony breakers** — but needs fundamental redesign

Temporal signals measure strategy history. They answer: "Are we being repetitive?"

**Critical design flaw in `temporal.strategy_repetition_count`:**

The signal counts how many times the **most recent** strategy appears in the last 5 turns:

```python
current = strategy_history[-1]  # Most recent strategy
repetition_count = sum(1 for s in recent_history if s == current)
return repetition_count / window_size  # Normalize to [0,1]
```

This means: if `deepen` was selected last turn and appeared 4 times in the last 5, the signal value is 0.8 for **ALL candidate strategies**. When all strategies have a weight of -0.3, this produces -0.24 for everyone — zero differentiation.

**What it SHOULD measure:** For each candidate strategy, "how repetitive would selecting THIS strategy be?" This requires per-candidate computation:

```python
# Hypothetical: candidate-aware repetition counting
for candidate_strategy in all_strategies:
    hypothetical_history = strategy_history + [candidate_strategy.name]
    count = sum(1 for s in hypothetical_history[-5:] if s == candidate_strategy.name)
    repetition_penalty[candidate_strategy.name] = count / 5
```

With candidate-aware counting: if deepen has been selected 4/5 turns, deepen's penalty is 5/5=1.0 but explore's penalty is 1/5=0.2. The penalty correctly differentiates.

**Without this redesign, asymmetric weights are a workaround:**

JTBD compensates by giving `dig_motivation` a -1.5 weight while others get -0.7. This means the same global value (say 0.8) produces -1.2 for dig_motivation but -0.56 for others — creating a 0.64 differential. This works but is brittle and requires per-strategy manual tuning.

### 3.4 Meta Signals — Interview Orchestration

**Current role:** Phase detection + progress tracking + saturation measurement
**Recommended role:** **Phase gating + termination detection**

Meta signals measure where the interview is in its lifecycle. They answer: "What phase are we in? How much have we covered?"

**Phase detection (`meta.interview.phase`) works as designed** — it drives the phase multiplier system which is the single most impactful mechanism for strategy selection. However:

**Phase granularity is too coarse for 20-turn interviews:**

```
Early: turns 0-1  (10% = 1 effective turn)
Mid:   turns 2-17 (80% = 16 turns)
Late:  turns 18-20 (15% = 3 turns)
```

With only 3 phases, mid-phase lasts 16 turns. Any strategy that's advantaged in mid-phase (deepen in MEC, dig_motivation in JTBD) will dominate 80% of the interview.

**A finer-grained approach might work better:**

```
Early:     turns 0-3  (20%) — explore, map landscape
Early-mid: turns 4-7  (20%) — initial deepening, find strong chains
Mid:       turns 8-12 (25%) — deep exploration, build connections
Mid-late:  turns 13-16 (20%) — validation, saturation check
Late:      turns 17-20 (20%) — reflection, wrap-up
```

This would allow strategies like `clarify` and `uncover_obstacles` to have their own "sweet spot" phases rather than competing with `deepen` for the entire mid-phase.

**Progress and saturation signals** are well-designed in principle but have calibration issues:
- `meta.interview_progress` plateaus at 0.10 for 11 turns in MEC (only updates on terminal value completion)
- `meta.conversation.saturation` is better (velocity-based) but currently only triggers reflect/validate
- `meta.canonical.saturation` is a secondary metric that fires alongside conversation.saturation

**Design implication:** Progress/saturation signals should be used for **phase transition triggers** rather than strategy scoring:

```
IF saturation > 0.7 AND phase == mid → transition to late phase
IF progress > 0.5 AND no terminal values → transition to mid-late validation
```

This is more powerful than adding small fractional weights to strategy scores.

---

## 4. Which Signals Should NOT Be Used for Strategy Scoring?

### 4.1 Signals That Add Only Noise

| Signal | Current Use | Problem | Recommendation |
|--------|------------|---------|----------------|
| `graph.node_count` | Not used in weights | Correct — raw count has no scoring meaning | Keep excluded |
| `graph.edge_count` | Not used in weights | Correct — raw count has no scoring meaning | Keep excluded |
| `graph.orphan_count` | Not used in weights | Correct — raw count (use node-level `is_orphan` instead) | Keep excluded |
| `graph.canonical_*` | Not used in weights | Experimental Phase 4 signals — no proven value yet | Keep excluded until validated |
| `graph.avg_depth` | Not used in weights | Ambiguous — high avg could mean "well explored" or "narrow focus" | Keep excluded |
| `graph.depth_by_element` | Not used in weights | Per-element depth — too granular for strategy scoring | Keep excluded |
| `meta.interview.phase_reason` | Not used in weights | Debug/logging string — no scoring value | Keep excluded |

### 4.2 Signals That Should Be Demoted from Scoring to Gating

| Signal | Current Use | Problem | Recommendation |
|--------|------------|---------|----------------|
| `llm.engagement.mid` | +0.3-0.4 on most strategies | Symmetric weights = flat offset. Nearly all turns are "mid" or "high" engagement. | **Demote to gate**: only use `engagement.low` as a suppress gate for aggressive strategies |
| `llm.valence.high` | +0.4 on deepen, reflect | "Positive emotion" is too weak a signal to justify +0.4 points. Most respondents are neutral-to-positive. | **Remove from scoring** or reduce to 0.1 |
| `llm.certainty.mid` | +0.7 on reflect, validate | Fires inconsistently. In MEC, "mid" certainty is rare. | **Demote**: keep `certainty.low` and `certainty.high` as triggers, remove `.mid` |
| `graph.max_depth` | +0.7 on reflect, -0.3 on deepen | Maxes out early in JTBD (turn 2). In MEC, grows slowly. Permanent drag or permanent bonus. | **Remove from strategy scoring**. Use for progress/phase transition only. |
| `meta.interview_progress` | +0.5 on reflect | Plateaus, making it a near-constant. Fires identically across strategies. | **Remove from strategy scoring**. Use for phase transition triggers only. |

### 4.3 Signals With Structural Problems

| Signal | Problem | Impact | Fix Required |
|--------|---------|--------|-------------|
| `temporal.strategy_repetition_count` | Measures PREVIOUS strategy frequency, not candidate's | Same value for all candidates at each turn. Cannot differentiate. | Redesign to candidate-aware counting (see §3.3) |
| `temporal.turns_since_strategy_change` | Same issue — counts consecutive turns of current (previous) strategy | Same value for all candidates | Redesign alongside repetition_count |
| `llm.response_depth.mid`/`.high`/`.low` (MEC YAML) | Naming mismatch — signal emits "moderate"/"deep"/"shallow" but weights use "mid"/"high"/"low" | Dead weights (zero contribution, confirmed in both runs) | Fix YAML keys to match emitted values |
| `graph.chain_completion.has_complete.false` | In MEC, chains are almost never complete until terminal values reached | Fires True for 95%+ of turns → permanent +1.0 bonus for deepen | Either remove or rebalance. Consider using `chain_completion.ratio` (continuous) instead of `.has_complete.false` (binary) |

---

## 5. Strategy-Specific Analysis: Which Signals Make Sense?

### 5.1 Strategy Archetypes and Their Natural Signal Profiles

Each strategy has a natural "archetype" that determines which signal families are relevant:

| Archetype | Strategies | Primary Signal Source | Node Signals? |
|-----------|-----------|----------------------|---------------|
| **Deepening** | deepen (MEC), dig_motivation (JTBD) | LLM (depth, engagement) + Graph (chain_completion) | Yes — target un-exhausted nodes with open chains |
| **Broadening** | explore (MEC), explore_situation (JTBD) | Graph (orphan count, node diversity) + Temporal (repetition) | Yes — target fresh/orphan nodes |
| **Validating** | reflect (MEC), validate_outcome (JTBD) | Meta (progress, saturation) + Node (has_outgoing, well-connected) | Yes — target well-explored nodes |
| **Challenging** | clarify (MEC), clarify_assumption (JTBD) | LLM (certainty, specificity) | Weak — the target is the respondent's claim, not a specific node |
| **Recovering** | revitalize | LLM (engagement, trend) + Temporal | Yes — target fresh nodes, avoid exhausted ones |
| **Probing** | probe_alternatives, uncover_obstacles (JTBD) | LLM (valence, depth) | Yes — target orphan or under-connected nodes |

### 5.2 Strategies That Should NOT Use Node-Level Scoring

**Key insight:** Not all strategies are "about" a specific node. Some strategies target the respondent's state rather than a graph concept.

| Strategy | Node scoring makes sense? | Reasoning |
|----------|--------------------------|-----------|
| deepen | **Yes** | "Go deeper on THIS concept" — node selection is the core decision |
| explore | **Yes** | "Explore breadth from THIS concept" — node is the starting point |
| reflect | **Partially** | Validates understanding of well-explored areas — node helps focus the summary but the reflection is about the overall picture |
| clarify | **No** | Responds to respondent confusion. The confused claim may not map to a single node. Node selection adds noise. |
| revitalize | **Partially** | Should shift to a fresh topic — node selection identifies where to shift, but the trigger is respondent fatigue, not node state |
| uncover_obstacles | **Partially** | Triggered by negative valence — the pain point may not be in the graph yet (it's about to be extracted) |

**Design implication:** For strategies where node scoring doesn't make sense, the system should either:
1. Use a **default node selection** (e.g., "most recently mentioned concept") rather than joint scoring
2. Or **exclude node signals from that strategy's weights** entirely, letting the strategy compete purely on global signals and then inheriting the node from the winning node-aware strategy

### 5.3 Strategies That Need Unique Signal Profiles

The cross-run analysis showed that `clarify` was selected 0% in both MEC simulations. Examining why:

```
clarify signal_weights in MEC:
  llm.specificity.low: 0.8        # Trigger: vague language
  llm.certainty.low: 0.5          # Trigger: uncertainty
  llm.engagement.mid: 0.3         # OK at mid engagement
  temporal.strategy_repetition_count: -0.3  # Same as everyone
  temporal.turns_since_strategy_change: -0.3  # UNIQUE penalty (only clarify has this)
  graph.node.is_orphan.true: 0.7  # Node: orphan nodes
  graph.node.exhaustion_score.low: 0.4  # Node: fresh nodes
  graph.node.focus_streak.none: 0.3  # Node: never-focused nodes
```

**Why it never wins:**
1. Maximum possible score: 0.8 + 0.5 + 0.3 + 0.7 + 0.4 + 0.3 = 3.0 (if all triggers fire)
2. But it has a UNIQUE penalty (`turns_since_strategy_change: -0.3`) that no other strategy carries
3. Phase multiplier in mid-phase: 0.8× (vs deepen's 1.3×)
4. Phase bonus: 0.0 (vs deepen's +0.3)
5. In practice, max observed score ≈ 1.5 vs deepen's 3.5+

**The fix isn't just weight tuning — it's giving clarify a signal profile that UNIQUELY fires.** Clarify should have signals that no other strategy responds to:

```yaml
# Proposed unique triggers for clarify:
llm.valence.low: 0.5           # Respondent pushback = misunderstanding
llm.response_depth.shallow: 0.6  # Brief answer = didn't understand the question
graph.node.is_current_focus.true: 0.4  # Clarify the current topic, don't switch
```

The shallow+low-valence combination uniquely identifies "respondent didn't engage because they didn't understand" — which is clarify's domain.

---

## 6. Phase System Analysis

### 6.1 How Phase Multipliers Actually Work

Phase multipliers are the most impactful scoring mechanism. They multiply the entire base score:

```
final = (base_score × multiplier) + bonus
```

For MEC mid-phase:
- deepen: base × 1.3 + 0.3
- explore: base × 0.6 + 0.0
- clarify: base × 0.8 + 0.0
- reflect: base × 0.7 + 0.0
- revitalize: base × 1.0 + 0.0

Even if explore has a higher base score, deepen wins unless explore's base exceeds deepen's by more than 2.2×. This almost never happens because both strategies share many of the same node signals with similar weights.

### 6.2 Phase Multiplier Dominance by Methodology

| Methodology | Phase | Dominant Strategy | Multiplier | Runner-up | Multiplier | Dominance Ratio |
|-------------|-------|-------------------|------------|-----------|------------|-----------------|
| MEC | mid | deepen | 1.3× + 0.3 | revitalize | 1.0× | ~1.6× |
| MEC | early | explore | 1.5× + 0.2 | clarify | 1.2× | ~1.4× |
| MEC | late | reflect | 1.2× + 0.2 | revitalize | 1.2× + 0.2 | ~1.0× (tied) |
| JTBD | mid | uncover_obstacles | 1.3× + 0.25 | clarify_assumption | 1.3× + 0.15 | ~1.06× |
| JTBD | mid | dig_motivation | 1.2× + 0.15 | uncover_obstacles | 1.3× + 0.25 | ~0.95× (loses!) |
| JTBD | early | explore_situation | 1.5× + 0.2 | probe_alternatives | 1.2× + 0.15 | ~1.3× |

**Key observation:** JTBD's mid-phase is far more competitive than MEC's. Three strategies (dig_motivation, uncover_obstacles, clarify_assumption) have similar multipliers (1.2-1.3×), creating genuine signal-driven competition. MEC's mid-phase is effectively a deepen monopoly.

### 6.3 What Finer-Grained Phasing Would Enable

With 5 phases instead of 3, each strategy could have a "sweet spot":

```
Phase 1 (Mapping):     explore dominates     — build initial graph breadth
Phase 2 (Connecting):  clarify + explore     — resolve confusion, fill gaps
Phase 3 (Deepening):   deepen dominates      — ladder to values
Phase 4 (Validating):  reflect + clarify     — check understanding, surface assumptions
Phase 5 (Closing):     reflect + revitalize  — wrap up, final insights
```

This gives `clarify` a window (phases 2 and 4) where it has a multiplier advantage. Without this, clarify must overcome deepen's 1.6× advantage through signals alone — which, as we've shown, it cannot do with the current signal architecture.

### 6.4 Alternative: Continuous Phase Weighting

Instead of discrete phases with hard boundaries, phase influence could be continuous:

```python
# Hypothetical: sigmoid-based phase curves
progress = meta.conversation.saturation  # [0, 1]

explore_weight = 1.5 * (1 - sigmoid(progress, center=0.2, steepness=8))  # High early, fades
deepen_weight = 1.3 * sigmoid(progress, center=0.3, steepness=5) * (1 - sigmoid(progress, center=0.8, steepness=8))  # Mid bell curve
reflect_weight = 1.2 * sigmoid(progress, center=0.7, steepness=6)  # Rises late
```

This eliminates cliff effects at phase boundaries and creates smooth transitions. A respondent who provides rich early responses (high saturation at turn 3) would naturally transition to deepening earlier, while a sparse respondent would get more exploration turns.

---

## 7. The Joint Scoring Conflation

### 7.1 The Problem

The current architecture scores (strategy, node) pairs jointly:

```
For each strategy × each node:
    score = f(global_signals, node_signals, strategy_weights, phase)
```

This means a 5-strategy × 50-node grid produces 250 candidates ranked by a single score. The winner determines BOTH which strategy and which node.

**Why this creates problems:**

1. **Strategy-node coupling:** The "best" strategy for the interview may not be paired with the "best" node. Example: `reflect` might be the right strategy (high saturation, deep graph), but it wins only for node A (which has high `has_outgoing`). The respondent's context is about node B. The system reflects on node A instead of node B.

2. **Node signals dominate strategy selection:** When node signals have high weights (e.g., exhaustion_score.low: +1.0), the node with the strongest signal profile pulls ALL strategies toward it. The "winning" strategy is then whichever strategy has the highest weight on that dominant node signal.

3. **Scale mismatch:** With 50+ nodes but only 5 strategies, the node dimension dominates. The top-10 candidates might all be the same strategy on different nodes, or 5 strategies on the same node.

### 7.2 Evidence from Cross-Run Data

In both MEC simulations, only 3 nodes were ever selected across 20 turns, despite 54-88 nodes in the graph. The winning (strategy, node) pair was almost always:
- **Strategy:** determined by phase multiplier (deepen in mid, reflect in late)
- **Node:** determined by exhaustion_score.low threshold (first node below 0.25 wins)

The joint scoring didn't produce joint optimization — it produced two independent selections accidentally coupled through a single ranking.

### 7.3 Alternative: Two-Stage Selection

```
Stage A: Select strategy (based on respondent state + interview state)
  Inputs: LLM signals, temporal signals, meta signals, phase
  Output: Ranked strategies

Stage B: Select node for chosen strategy (based on graph state + node state)
  Inputs: Node signals, strategy's node preference profile
  Output: Best node for the chosen strategy
```

**Advantages:**
- Strategy selection is driven by respondent state, not node topology
- Node selection is driven by exploration state, not strategy preference
- Each stage has fewer candidates: 5 strategies, then N nodes (not 5×N pairs)
- Easier to debug: "why was deepen chosen?" and "why was node X chosen?" are separate questions

**Disadvantages:**
- Loses the ability to say "explore orphan node X" as a joint decision (where the orphan status drives both strategy and node)
- Some strategies inherently care about node type (deepening an attribute vs. deepening a value)

**Hybrid approach:** Keep joint scoring but with guardrails:
1. Score strategies first (global signals + phase)
2. If top-2 strategies are within 0.5 points, let node signals break the tie
3. Otherwise, use the winning strategy and select its best node independently

---

## 8. Methodology Design Implications

### 8.1 Signal Budget Allocation

Given the analysis above, methodology designers should allocate their weight budget differently:

| Signal Family | Current % of Weight Budget | Recommended % | Reason |
|---------------|--------------------------|---------------|--------|
| LLM (global) | ~40% | ~20% | Demote to binary gates, reduce fractional precision |
| Node (per-node) | ~30% | ~40% | Primary differentiator in joint scoring |
| Temporal (global) | ~15% | ~10% | Redesign needed; current implementation is broken for differentiation |
| Meta (global) | ~10% | ~5% | Move to phase transition triggers, not scoring |
| Phase multipliers | ~5% (implicit) | ~25% | Make explicit; this is where strategy selection actually happens |

### 8.2 Rules for Adding New Signals

When adding a new signal, apply this checklist:

1. **Is it global or per-node?** If global, it can only differentiate strategies via asymmetric weights. Ask: which strategy should it uniquely trigger?
2. **Is it continuous or categorical?** If continuous, the threshold binning (low/mid/high) loses information. Consider using the raw value with a direct weight.
3. **Does it correlate with existing signals?** If engagement and depth are correlated (they are — r≈0.6 in observed data), adding both to a strategy's weights double-counts the same information.
4. **Does it have a clear action implication?** A signal should answer: "GIVEN this signal value, WHAT should the interviewer do differently?" If the answer is "nothing specific," the signal doesn't belong in scoring.
5. **Is it persona-independent?** If the signal only fires for certain persona types (e.g., `global_response_trend.fatigued` never fires for engaged personas), it wastes weight budget for those sessions.

### 8.3 Weight Tuning Protocol

When tuning weights, follow this priority:

1. **Fix broken signals first** (naming mismatches, structural problems from §4.3)
2. **Ensure asymmetric global weights** — every global signal used in scoring must have meaningfully different weights across strategies
3. **Validate node signal independence** — each node signal used in a strategy should produce different outcomes for different nodes (not always fire True)
4. **Check phase multiplier spread** — the ratio between dominant and runner-up strategy should be < 1.5× to allow signal-driven differentiation
5. **Run comparative simulations** — same concept, different personas, verify the system behaves differently (not identically as observed)

### 8.4 MEC vs JTBD: What JTBD Gets Right

JTBD's signal configuration addresses several MEC problems:

| Issue | MEC (broken) | JTBD (better) | How |
|-------|-------------|---------------|-----|
| response_depth naming | Uses "mid"/"high"/"low" (dead) | Uses "surface"/"shallow"/"moderate"/"deep" (correct) | Matches actual emitted values |
| Repetition penalty | -0.3 symmetric | -1.5 for dig_motivation, -0.7 for others | Asymmetric weights create actual differentiation |
| Mid-phase competition | 1 dominant strategy (deepen 1.3×) | 3 competitive strategies (1.2-1.3×) | Narrower multiplier spread |
| Focus streak penalties | Only `focus_streak.high: +0.5` (reward!) | `medium: -0.4, high: -0.7/-0.8` on most strategies | Active penalties prevent focus lock |
| Strategy count | 5 (too few for 20 turns) | 7 (better coverage) | More strategies = more opportunities for differentiation |

MEC methodology should adopt JTBD's patterns for: asymmetric repetition penalties, response_depth naming, focus_streak penalties, and mid-phase multiplier narrowing.

---

## 9. Recommendations Summary

### Tier 1: Fix What's Broken (no architectural changes)

| # | Change | Files | Impact |
|---|--------|-------|--------|
| 1 | Fix signal naming mismatches in MEC YAML | `config/methodologies/means_end_chain.yaml` | Restores 3 dead signals |
| 2 | Add exhaustion penalties (mid, high) to all MEC strategies | Same | Enables node rotation |
| 3 | Make repetition penalties asymmetric (deepen: -0.5, others: -0.3) | Same | Creates strategy differentiation |
| 4 | Add focus_streak.medium/high penalties to MEC strategies (copy from JTBD) | Same | Prevents focus lock |

### Tier 2: Rebalance (requires careful testing)

| # | Change | Files | Impact |
|---|--------|-------|--------|
| 5 | Narrow mid-phase multiplier spread (deepen 1.3→1.2, explore 0.6→0.8) | YAML | Allows signal-driven strategy selection |
| 6 | Add unique signal profiles to underused strategies (clarify, explore) | YAML | Gives each strategy a "winning condition" |
| 7 | Increase early phase ratio (10%→20%) for 20-turn interviews | `interview_phase.py` | 4 exploration turns instead of 1 |
| 8 | Remove `graph.chain_completion.has_complete.false` from deepen (or reduce to 0.3) | YAML | Removes permanent +1.0 bonus that distorts scoring |

### Tier 3: Architectural Changes (research required)

| # | Change | Files | Impact |
|---|--------|-------|--------|
| 9 | Redesign temporal signals to be candidate-aware | `strategy_history.py`, `scoring.py` | Correct repetition penalty per candidate |
| 10 | Implement two-stage selection (strategy first, then node) | `scoring.py`, `methodology_strategy_service.py` | Decouples strategy and node decisions |
| 11 | Add continuous phase weighting (sigmoid curves) | `interview_phase.py`, YAML schema | Eliminates phase boundary cliff effects |
| 12 | Demote LLM signals from scoring to binary gating | `scoring.py`, YAML schema | Removes false precision, simplifies weight tuning |

### Tier 4: New Signal Development

| # | Signal | Purpose | Why Not Existing |
|---|--------|---------|------------------|
| 13 | `graph.node.chain_depth` (per-node) | How deep is the chain from THIS specific node? | Existing `graph.max_depth` is global — can't target specific chains |
| 14 | `graph.node.type` (per-node) | What ontology level is this node? | Enables type-aware strategies (deepen terminal values differently from attributes) |
| 15 | `temporal.candidate_repetition` (per-candidate) | How repetitive WOULD this candidate be? | Replaces broken global repetition signal |
| 16 | `meta.strategy_coverage` (global) | How many distinct strategies used in last 10 turns? | Direct monotony measurement rather than per-strategy counting |

---

## Appendix A: Signal Flow Diagram

```
                    ┌─────────────────────────────────────────┐
                    │         Turn Pipeline (Stage 6)          │
                    │                                          │
    User Response ──┤  ┌──────────────────┐                   │
                    │  │ Global Detection  │                   │
                    │  │  LLM signals      │──┐                │
                    │  │  Graph signals    │  │                │
                    │  │  Temporal signals │  │  global_signals│
                    │  │  Meta signals     │  │  (21 signals)  │
                    │  └──────────────────┘  │                │
                    │                         │                │
                    │  ┌──────────────────┐  │                │
                    │  │ Node Detection   │  │                │
    Graph State ────┤  │  exhaustion      │  │  node_signals  │
    NodeTracker ────┤  │  focus_streak    │──┤  (11 signals   │
                    │  │  yield_stag.     │  │   × N nodes)   │
                    │  │  orphan/edges    │  │                │
                    │  │  opportunity     │  │                │
                    │  └──────────────────┘  │                │
                    │                         │                │
                    │  ┌──────────────────┐  │                │
                    │  │ Joint Scoring    │◀─┘                │
                    │  │                  │                    │
                    │  │ For each (strategy, node):            │
                    │  │   combined = global ∪ node            │
                    │  │   base = Σ(value × weight)            │
                    │  │   final = base × phase_mult + bonus   │
                    │  │                  │                    │
                    │  │ Sort by final_score descending        │
                    │  │ Winner = rank 1  │                    │
                    │  └────────┬─────────┘                   │
                    │           │                              │
                    │   (strategy, node, score)                │
                    └───────────┼──────────────────────────────┘
                                │
                    ┌───────────▼──────────────────────────────┐
                    │  Question Generation (Stage 8)            │
                    │  Uses: strategy.description + node.label  │
                    └──────────────────────────────────────────┘
```

---

## Appendix B: Signal Effectiveness Matrix (MEC, observed)

Based on scoring CSV decomposition from both cross-run simulations:

| Signal | Fires (%) | Avg Contribution | Differentiates? | Verdict |
|--------|-----------|-----------------|-----------------|---------|
| `graph.node.exhaustion_score.low` | 95% | +0.58 | **Yes** (per-node) | Keep — primary rotation driver |
| `graph.node.focus_streak.none` | 55% | +0.57 | **Yes** (per-node) | Keep — fresh node targeting |
| `graph.node.has_outgoing.true` | 18% | +0.80 | **Yes** (per-node) | Keep — structural targeting |
| `graph.node.yield_stagnation.false` | 19% | +0.50 | **Yes** (per-node) | Keep — yield tracking |
| `graph.chain_completion.has_complete.false` | 95% | +1.00 | **No** (near-constant) | **Remove or reduce** — permanent bonus |
| `temporal.strategy_repetition_count` | 10% | -0.28 | **No** (global) | **Redesign** — same value for all candidates |
| `llm.engagement.high` | 16% | +0.05 | Weak | **Demote to gate** — +0.05 is noise |
| `llm.engagement.mid` | 33% | +0.35 | Weak | **Demote to gate** — symmetric across strategies |
| `llm.valence.low` | 15% | +0.40 | Moderate | Keep — unique trigger for uncover_obstacles |
| `llm.specificity.low` | 13% | +0.80 | Moderate | Keep — unique trigger for clarify |
| `llm.response_depth.moderate` | 13% | +0.15 | Weak | **Reduce weight** — +0.15 is noise |
| `graph.max_depth` | 39% | +0.20 | Weak | **Remove from scoring** — use for progress only |
| `meta.interview_progress` | 20% | +0.16 | **No** (plateaus) | **Remove from scoring** — use for phase transition |
| `meta.conversation.saturation` | 20% | +0.14 | **No** (global) | **Remove from scoring** — use for phase transition |

---

*Analysis authored: 2026-02-25*
*Evidence: 20260225_cross_run_analysis.md, scoring CSVs, codebase exploration*
*Methodologies analyzed: means_end_chain.yaml v3.0, jobs_to_be_done.yaml, scoring.py*
