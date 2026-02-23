# Deepen Strategy Analysis

## Executive Summary

The **deepen** strategy implements "laddering" in means-end chain methodology — asking progressive "why" questions to move respondents from concrete product attributes up through consequences and values to terminal life goals. The strategy uses a combination of content signals (response depth, chain progress), emotional signals (engagement, valence), and diversity mechanisms to decide when laddering is appropriate and safe.

---

## 1. Conceptual Purpose

**What is "deepen"?**
Deepen applies laddering, the core technique of means-end chain interviews: exploring the causal chain from attributes → consequences → values through repeated "why is that important?" questions.

**When should it be used?**
- Respondent gives concrete, detailed answers about product features
- The conversation has not yet reached abstract values or life goals
- The respondent is engaged and emotionally positive
- We haven't been using the same strategy repeatedly

**Expected outcome:**
- Move the interview up the abstraction ladder
- Expand graph depth (max_depth increases)
- Increase chain completion (more nodes linked in sequence)
- Reveal respondent's terminal values and life goals

---

## 2. Signal Architecture

### 2.1 Global Signals (Interview-Level)

| Signal | Type | Weight | Trigger | Meaning |
|--------|------|--------|---------|---------|
| `llm.response_depth.low` | Threshold (≤ 0.25) | **0.8** ⬆️ HIGH | Minimal elaboration (Likert 1-2) | Respondent gave brief answer; good time to probe deeper why |
| `llm.response_depth.mid` | Threshold (0.25-0.75) | **0.3** ⬆️ | Moderate elaboration (Likert 3) | Some detail provided; deepen to understand underlying reasons |
| `graph.max_depth` | Continuous [0,1] | **-0.3** ⬇️ PENALTY | Per-node metric | Already exploring deep; avoid redundant deepening |
| `graph.chain_completion.has_complete.false` | Boolean | **1.0** ⬆️ STRONG | No complete chain yet | Active trigger: laddering not finished |
| `llm.engagement.high` | Threshold (≥ 0.75) | **0.7** ⬆️ | Respondent is engaged (Likert 4-5) | **Safety gate**: Safe to ask probing "why" questions |
| `llm.engagement.low` | Threshold (≤ 0.25) | **-0.5** ⬇️ PENALTY | Respondent is disengaged (Likert 1-2) | **Safety gate**: Avoid laddering when respondent is passive |
| `llm.valence.high` | Threshold (≥ 0.75) | **0.4** ⬆️ | Positive emotion (Likert 4-5) | **Safety gate**: Safe to probe when emotionally positive |
| `temporal.strategy_repetition_count` | Integer [0+] | **-0.3** ⬇️ PENALTY | Times deepen was used | Penalize overuse; encourage strategy diversity |

### 2.2 Node-Level Signals (Graph-Specific)

| Signal | Type | Weight | Meaning |
|--------|------|--------|---------|
| `graph.node.exhaustion_score.low` | Threshold (≤ 0.25) | **1.0** ⬆️ STRONG | Node hasn't been exhausted; good candidate for deepening |
| `graph.node.focus_streak.low` | Threshold (≤ 0.25) | **0.5** ⬆️ | Fresh node; not recently targeted | Prefer exploring new nodes |

### 2.3 Signal Normalization

All LLM signals (response_depth, engagement, valence) are **normalized at source**:
- Original LLM rating: Likert 1-5 scale
- Normalized: `(score - 1) / 4` → Float [0, 1]
- Mapping: 1→0.0, 2→0.25, 3→0.5, 4→0.75, 5→1.0
- Threshold binning applied: `.low` (≤0.25), `.mid` (0.25-0.75), `.high` (≥0.75)

---

## 3. Scoring Mechanism

### 3.1 Base Score Calculation

```
base_score = sum of all signal contributions
```

**Contribution calculation per signal:**
- Boolean signals: `weight if signal_true else 0.0`
- Numeric signals: `weight * normalized_value`
- Missing signals: ignored (skip, don't penalize)

**Example: High engagement + high depth**
```
llm.response_depth = 5 (Likert)
  → normalized: (5-1)/4 = 1.0
  → matches .high (≥0.75): True
  → contribution: 0.8 * 1 = 0.8

llm.engagement = 4 (Likert)
  → normalized: (4-1)/4 = 0.75
  → matches .high (≥0.75): True
  → contribution: 0.7 * 1 = 0.7

temporal.strategy_repetition_count = 0
  → contribution: -0.3 * 0 = 0.0

Total base_score = 0.8 + 0.7 + 0.0 = 1.5
```

### 3.2 Phase Modifiers

Deepen score is adjusted based on interview phase:

| Phase | Multiplier | Bonus | Final Formula | Rationale |
|-------|-----------|-------|---------------|-----------|
| **early** | 0.5x | 0.0 | `base * 0.5` | Prioritize breadth (explore) over depth initially |
| **mid** | 1.3x | **+0.3** | `base * 1.3 + 0.3` | **Prime time for deepen**: Build depth and connections |
| **late** | 0.5x | 0.0 | `base * 0.5` | Switch to validation (reflect, revitalize) |

**Key insight:** Deepen is **the only strategy** that gets both a multiplier AND bonus in mid-phase, making it the dominant strategy when conditions are right.

---

## 4. Safety Guards and Constraints

### 4.1 Engagement Gate

| Engagement | Signal Match | Weight | Effect |
|------------|-------------|--------|--------|
| High (4-5) | `.high: True` | +0.7 | Actively encourage deepening |
| Medium (3) | `.mid: True` | 0.0 (no weight) | Neutral; OK if other signals positive |
| Low (1-2) | `.low: True` | -0.5 | **Penalize** deepening when passive |

**Interpretation:** A respondent giving short, disengaged answers shouldn't be pushed with "why" questions — that creates interview friction. The -0.5 penalty prevents deepen from dominating even with strong response_depth signals.

### 4.2 Valence Gate

| Valence | Signal Match | Weight | Effect |
|---------|-------------|--------|--------|
| Positive (4-5) | `.high: True` | +0.4 | Safe emotional state for probing |
| Neutral (3) | `.mid: True` | 0.0 | No specific guidance |
| Negative (1-2) | `.low: True` | 0.0 (no weight) | Not penalized, but also not encouraged |

**Interpretation:** Asking "why?" to someone emotionally positive (enthusiasm, satisfaction) is safer than asking someone emotionally negative (frustration, disappointment). However, negative emotion doesn't prevent deepen; it just doesn't actively encourage it.

### 4.3 Depth Penalty

| Scenario | graph.max_depth | Contribution | Effect |
|----------|----------------|--------------|--------|
| Shallow graph (few layers) | 0.2 | -0.3 * 0.2 = -0.06 | Minimal penalty; deepen OK |
| Medium depth | 0.5 | -0.3 * 0.5 = -0.15 | Moderate penalty |
| Deep graph (many layers) | 0.9 | -0.3 * 0.9 = -0.27 | Stronger penalty; discourage further deepening |

**Interpretation:** The system avoids redundant deepening. If the graph is already deep, that signal is already captured elsewhere (chain_completion would show completion). This prevents infinite "why" loops.

### 4.4 Diversity Penalty

| Repetition Count | Contribution | Effect |
|------------------|--------------|--------|
| First use (count=0) | 0.0 | No penalty |
| Second use (count=1) | -0.3 * 1 = -0.3 | Noticeable penalty |
| Third use (count=2) | -0.3 * 2 = -0.6 | Strong penalty |

**Interpretation:** Repeated use of the same strategy on the same node is penalized, encouraging alternation between deepen/clarify/explore/reflect.

---

## 5. Interaction with Other Strategies

### 5.1 Competition During Mid-Phase

When in **mid-phase** with strong signals:

**Scenario A: Optimal deepen conditions**
```
response_depth = 2 (brief answer) → Low
engagement = 4 (actively engaged) → High
valence = 5 (enthusiastic) → High
chain_completion = false → Complete chain not found
repeat_count = 0 → Fresh strategy

deepen score = (0.8 + 0.3 + 0.7 + 1.0 - 0.0) * 1.3 + 0.3 = 3.52
```

Deepen dominates. Other strategies would score much lower:
- `explore` (needs uncertainty, fresh nodes): ~0.5
- `clarify` (needs vagueness): ~0.0
- `reflect` (needs completion): ~0.0
- `revitalize` (needs fatigue): ~0.0

**Scenario B: High engagement but already deep**
```
response_depth = 1 (very brief) → Low
engagement = 4 (actively engaged) → High
valence = 4 (positive) → High
chain_completion = true → Chain completed
graph.max_depth = 0.9 → Already very deep
repeat_count = 1 → Used once

deepen score = (0.8 + 0.7 + 0.4 + 0.0 - 0.27 - 0.3) * 1.3 + 0.3 ≈ 2.08
```

`reflect` might now score higher (chain complete, max_depth high), triggering validation instead.

### 5.2 Role in Early Phase

In **early-phase**, deepen has a **0.5x multiplier**, making it subordinate to explore (1.5x):

```
Deepen in early-phase = base_score * 0.5 + 0.0
Explore in early-phase = similar_base * 1.5 + 0.2
```

**Meaning:** System prioritizes breadth (finding multiple attributes/branches) before depth (probing why any single one matters).

### 5.3 Contrast with Clarify

| Strategy | Trigger | When | Safety Gates |
|----------|---------|------|--------------|
| **deepen** | Brief but clear responses | Respondent understands but gives short answer | Engagement + valence gates |
| **clarify** | Vague or uncertain responses | Respondent unclear or confused | Engagement gate (low-mid OK) |

If respondent is **vague (low specificity) AND passive (low engagement)**, system chooses `clarify` (rephrase) over `deepen` (ask why).

---

## 6. Interview Phase Dynamics

### 6.1 Early Phase (Turns 0-4)

**Phase strategy weights:**
- `explore: 1.5x` ← Dominant
- `clarify: 1.2x`
- `deepen: 0.5x` ← Suppressed
- `reflect: 0.2x`

**Expected pattern:**
1. Interviewer asks opening question about product attributes
2. System uses `explore` to branch out (find multiple attributes)
3. If response unclear, `clarify` refines understanding
4. Deepen is available but less likely to be selected
5. Graph builds breadth: many nodes, shallow connections

**Example:** "What do you like about oat milk?"
- Response: "The texture and the taste"
- Depth: mid (mentioned two things)
- Engagement: high (volunteered detail)
- System response: `explore` "What else appeals to you?" (not deepen "why is texture important?")

### 6.2 Mid Phase (Turns 5-12)

**Phase strategy weights:**
- `deepen: 1.3x + 0.3` ← **Dominant with bonus**
- `clarify: 0.8x`
- `explore: 0.8x`
- `reflect: 0.7x`

**Expected pattern:**
1. Initial attributes identified and documented
2. System now probes each attribute's consequences and values
3. Deepen dominates when engagement/valence are positive
4. Graph builds depth: chains from attributes up to values
5. Multiple "why" probes on same nodes (laddering)

**Example:** "The creamy texture is really important"
- Depth: low (one attribute, no elaboration)
- Engagement: high (speaking freely)
- Valence: high (positive tone)
- System response: `deepen` "Why is creaminess important to you?"
- Expected response might move toward consequences ("feels more satisfying")

### 6.3 Late Phase (Turns 13+)

**Phase strategy weights:**
- `reflect: 1.2x + 0.2` ← Dominant
- `revitalize: 1.2x + 0.2` ← Equally dominant
- `deepen: 0.5x` ← Suppressed
- `explore: 0.3x`

**Expected pattern:**
1. Laddering complete; most chains explored
2. System validates understanding (reflect) or re-engages if fatigue detected (revitalize)
3. Deepen rarely selected (chains are complete)
4. Interview winds down toward conclusion

---

## 7. Mathematical Properties

### 7.1 Score Range

Deepen score can theoretically range from **-0.6** to **3.5+** (before phase modifiers):

**Minimum scenario (all negative):**
- `response_depth.low: False` → 0
- `engagement.low: True` → -0.5
- Graph depth very high → -0.27
- Repeated 2x → -0.6
- **Total: -1.37** → After mid-phase 1.3x: **-1.78** (strong discouragement)

**Maximum scenario (all positive):**
- `response_depth.low: True` → 0.8
- `response_depth.mid: True` → 0.3
- `chain_completion.false: True` → 1.0
- `engagement.high: True` → 0.7
- `valence.high: True` → 0.4
- Fresh node (no penalties) → 0
- **Total: 3.2** → After mid-phase 1.3x + 0.3 bonus: **4.46** (very strong encouragement)

### 7.2 Sensitivity Analysis

**What if engagement drops from high to mid?**
```
Loses: 0.7 (engagement.high lost)
Gains: 0.0 (engagement.mid has no weight)
Impact: -0.7 to final score

Example: 1.5 → 0.8 (still positive, but deepen less likely)
```

**What if response_depth is high instead of low?**
```
Loses: 0.8 (response_depth.low lost)
Gains: 0.0 (no weight for response_depth.high)
Impact: -0.8 to final score

Interpretation: Respondent already elaborated; no need to deepen further
```

**What if graph.max_depth = 1.0 (maximum depth)?**
```
Impact: -0.3 * 1.0 = -0.3 penalty
Typical mid-phase score with good engagement: ~3.2 - 0.3 = 2.9 → still positive
```

The -0.3 penalty is calibrated to discourage but not prevent deepening on already-deep graphs.

---

## 8. Edge Cases and Considerations

### 8.1 The Engagement Paradox

**Observation:** Respondents who are least engaged might benefit most from a new strategy.

**Current behavior:** Disengaged respondents (low engagement, low valence) still receive the -0.5 engagement penalty on deepen.

**Implication:** System will switch to `revitalize` (designed to re-engage) rather than push deeper with `deepen`.

**Design philosophy:** This is intentional—don't probe deeper (aggressive) when respondent is withdrawing. Instead, shift topics (`revitalize`).

### 8.2 The Chain Completion Signal

`graph.chain_completion.has_complete.false` with weight **1.0** is the strongest non-engagement signal.

**Impact:** Even with poor engagement/valence, if chains aren't complete, deepen can still score decently (~1.0 base, reduced by engagement penalty but not eliminated).

**Question:** Is this too aggressive? Should incomplete chains be lower priority than respondent wellbeing (engagement)?

**Current design answer:** Yes—incomplete chains are a proxy for "there's still laddering work to do." The engagement gate (0.7 for high, -0.5 for low) provides the safety rail.

### 8.3 Response Depth as Primary Trigger

Deepen is triggered most strongly by **low response_depth (0.8 weight)**, not by any graph signal.

**Implication:** System says "brief answer → deepen." But is this always correct?

**Scenarios where it might be wrong:**
- Respondent gives brief answer because they're deliberate/minimalist (minimal speaker)
- Respondent gave brief answer because they're disengaged (but engagement signal should catch this)
- Respondent's brief answer is sufficient for their thinking pattern

**Safety mechanism:** Engagement and valence gates should catch disengaged or negative brief answers. But they don't catch genuinely minimal speakers.

**Potential future refinement:** Add `llm.articulateness` signal to distinguish "quiet by nature" from "quiet by disengagement."

### 8.4 Node-Level Exhaustion

`graph.node.exhaustion_score.low` (weight 1.0) means deepen strongly prefers fresh nodes.

**Implication:** Even if global conditions are right for deepen, the system will pick a less-exhausted node.

**Example:** Three nodes available, all eligible for deepening.
- Node A: exhaustion_score = 0.1 (fresh) → gets +1.0 boost
- Node B: exhaustion_score = 0.5 (medium) → no boost
- Node C: exhaustion_score = 0.9 (exhausted) → negative contribution in D1 architecture

**Result:** Deepen applies to Node A, avoiding exhausted nodes.

**Design philosophy:** Prevents interview monotony and encourages exploring the full graph before re-probing the same nodes.

---

## 9. Recommended Analysis Points

Before making changes to deepen weights, consider analyzing:

1. **Interview transcripts:** Do deepen responses actually move up the value ladder, or do they stall?

2. **Graph structure:** In mid-phase interviews, what's the ratio of depth to breadth? Is it appropriate for means-end chain?

3. **Strategy distribution:** What percentage of questions use each strategy? Is deepen underused or overused?

4. **Respondent feedback:** Do frequent deepen questions feel repetitive or probing in a helpful way?

5. **Chain completion:** What % of interviews reach chain completion? If low, is deepen insufficient, or are other factors (concept difficulty, respondent type) responsible?

6. **Phase transition:** Are interviews spending appropriate time in each phase, or does deepen suppress/extend phase boundaries?

---

## 10. Summary: Mental Model

**Deepen embodies the interviewer's thinking:**

> "The respondent gave a brief but clear answer about why they like this attribute. They seem engaged and positive. The chain isn't complete yet, so there's more laddering to do. And we haven't focused on this node yet. I should ask 'why is that important?' to understand the deeper consequences and values."

The strategy balances:
- **Opportunity:** Brief answer + incomplete chain = "there's something to dig into"
- **Safety:** Engagement + valence = "is it safe/appropriate to probe deeper?"
- **Sustainability:** Node freshness + diversity = "are we being repetitive?"
- **Phase-appropriateness:** Mid-phase boost = "is this the right time for depth?"

The mathematical weights translate this judgment into quantitative scoring.
