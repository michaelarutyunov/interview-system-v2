# Signals for Interview Moderators

A practical guide to understanding what the system's signals mean for conducting and analyzing qualitative interviews.

---

## Overview

The interview system uses **signals** to understand what's happening in the conversation. Think of signals as the system's "senses" — they detect patterns in responses, track topic exploration, and guide questioning strategy. This document translates those technical signals into **moderator-friendly interpretations**.

Signals are organized into categories based on what they measure:

| Category | Purpose | Questions It Answers |
|----------|---------|---------------------|
| **LLM Signals** | Response quality | Are they engaged? How detailed are their answers? |
| **Graph Signals** | Knowledge structure | What concepts have we covered? How are they connected? |
| **Node Signals** | Per-topic exploration | Have we exhausted this specific topic? |
| **Meta Signals** | Interview-level insights | Where are we in the interview? Is the conversation drying up? |
| **Temporal Signals** | Pattern detection | Are we repeating ourselves? |

---

## LLM Signals: Response Quality

**What they measure:** The quality and nature of each response, scored on normalized scales.

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **response_depth** | How much information is being shared | An LLM evaluates the response and assigns it a 1-5 score, mapped to categories: 1=surface, 2=shallow, 3=moderate, 4-5=deep | surface/shallow = brief, minimal; moderate = some substance; deep = good detail and reasoning. Bins used in YAML: `surface`, `shallow`, `moderate`, `deep` |
| **specificity** | How concrete vs abstract the response is | An LLM assigns a 1-5 score, normalized to 0.0–1.0 using (score−1)/4. Bins: `low` ≤0.25 (scores 1-2), `mid` 0.25-0.75 (scores 2-4), `high` ≥0.75 (scores 4-5) | low (0.0-0.25) = vague generalities; high (0.75-1.0) = specific examples, details, named entities |
| **certainty** | How confident the respondent sounds | An LLM assigns a 1-5 score, normalized to 0.0–1.0. Bins: `low` ≤0.25 (scores 1-2 — hedging/uncertain), `mid` 0.25-0.75 (mixed), `high` ≥0.75 (scores 4-5 — confident) | low = hedging, "maybe", "I guess"; high = unqualified statements |
| **valence** | Emotional tone of response | An LLM assigns a 1-5 score, normalized to 0.0–1.0. Bins: `low` ≤0.25 (negative), `mid` 0.25-0.75 (neutral), `high` ≥0.75 (positive) | low = negative/critical; mid (~0.5) = neutral; high = positive/enthusiastic |
| **intellectual_engagement** | Presence of reasoning and "why" | An LLM assigns a 1-5 score, normalized to 0.0–1.0. Bins: `low` ≤0.25 (bare facts), `mid` 0.25-0.75 (some reasoning), `high` ≥0.75 (rich motivation/tradeoff reasoning) | low = bare facts; high = explains motivations, tradeoffs, value hierarchies |
| **engagement** | Willingness to participate | An LLM assigns a 1-5 score, normalized to 0.0–1.0. Bins: `low` ≤0.25 (score 1-2 — minimal effort, deflection), `mid` 0.25-0.75 (adequate), `high` ≥0.75 (score 4-5 — enthusiastic) | low = minimal effort, deflections; high = enthusiastic, extends beyond question |
| **global_response_trend** | How quality is changing over time | Classified from the last 4 response_depth values: if most are deepening → `deepening`; if 4+ are shallow → `fatigued`; otherwise `stable` or `shallowing` | `deepening` = more engaged; `stable` = consistent; `shallowing` = declining; `fatigued` = disengaged |

**Moderator Use Cases:**
- **Low depth + low engagement** → Consider building rapport or closing
- **High specificity + high certainty** → Good time to probe deeper
- **Fatigued trend** → Time to switch topics or wrap up
- **Negative valence** → Handle with care, may need rapport repair

**Phase Configuration Note:** The interview phase (early/mid/late) is automatically calculated from the turn boundaries configured in `config/interview_config.yaml`. The YAML uses descriptive phase names (exploratory/focused/closing) that map to signal outputs (early/mid/late) for backward compatibility with existing methodology configurations.

---

## Graph Signals: Knowledge Structure

**What they measure:** The structure of concepts and relationships extracted from the conversation.

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **graph.node_count** | Total distinct concepts extracted | Count of active (non-superseded) nodes in the knowledge graph | Low (<5) = early exploration; High (>10) = substantial coverage |
| **graph.edge_count** | Total relationships found | Count of directed edges between nodes in the knowledge graph | Indicates how well-connected concepts are |
| **graph.orphan_count** | Concepts with no connections | Count of nodes that have zero incoming AND zero outgoing edges | High count = opportunities to clarify relationships |
| **graph.max_depth** | Length of longest causal chain | BFS from root nodes (nodes with no incoming edges), counting nodes in the longest path, then divided by the ontology's level count (e.g., 5 for Means-End Chain) | How deep we've gone into "why" chains |
| **graph.avg_depth** | Average depth across all topics | *Not yet implemented — always returns 0.0. Treat as placeholder.* | Below 2 = surface-focused; 2-3 = balanced; Above 3 = consistently deep |
| **graph.chain_completion.ratio** | Fraction of complete "why" chains | For each level-1 node (top-level concept), BFS searches for a path to a "terminal" node type (e.g., a value in MEC). Ratio = level-1 nodes reaching terminal / total level-1 nodes | 0 = no complete chains; 1 = all chains reach terminal values |
| **graph.canonical_concept_count** | Deduplicated high-level topics | Count of canonical slots — groups of surface nodes that share the same high-level theme (similarity ≥ 0.60) | Lower than node_count because paraphrases are merged |
| **graph.canonical_edge_density** | How interconnected deduplicated topics are | Edge-to-concept ratio in the canonical graph: `canonical_edge_count / canonical_concept_count`. Higher = more relationships between stable high-level concepts. **UNBOUNDED above 1.0** (dense graphs can exceed 1.0). Returns `{}` (absent) if canonical graph not initialized | Low (<0.5) = isolated topics with few links; High (>1.0) = well-connected structure where topics relate to each other. Use bare-key weights only (not .low/.mid/.high) |
| **graph.canonical_exhaustion_score** | Overall interview exhaustion, filtering out paraphrases | Average of `exhaustion_score` values across all canonical slots. Aggregates the same exhaustion formula as node-level scores but at the deduplicated concept level, so re-phrasing the same topic doesn't inflate freshness | 0.0 = all canonical topics still fresh; 0.7+ = most high-level themes have been thoroughly explored across the interview |

**Moderator Use Cases:**
- **High orphan_count** → Ask "How are X and Y related?" to connect concepts
- **Low max_depth** → Use laddering strategies to go deeper
- **Low chain_completion** → Continue probing incomplete chains
- **High node_count but low depth** → Pivot from breadth to depth

### Limitations of Graph Depth and Chain Completion Signals

These signals are most meaningful for **Means-End Chain (MEC)** methodology, where the ontology has a clear layered structure (attributes → consequences → values). Be aware of the following limitations:

- **Depth is normalized against ontology levels**, not raw graph distance. For MEC with 5 levels, a raw depth of 3 gives `max_depth = 0.6`. This makes the signal methodology-relative — you cannot compare depth values across methodologies with different ontology structures.
- **Depth counts nodes, not meaningful reasoning steps.** A chain of 3 paraphrased surface nodes that map to the same canonical concept will report depth=3 even though they represent one conceptual level. Deduplication happens in the canonical graph, but depth is computed on the surface graph.
- **Chain completion is brittle with small N.** Early in an interview, there may be only 1–2 level-1 nodes, so a single complete chain makes `has_complete = true` while `ratio` can swing between 0.0 and 1.0 on a single turn. Treat this signal as noisy until 5+ level-1 nodes exist.
- **Chain completion depends on extraction quality.** If the LLM doesn't extract intermediate linking nodes, a chain that exists in the respondent's reasoning will appear incomplete in the graph. A low ratio may reflect extraction gaps, not shallow interviewing.
- **`avg_depth` is not yet implemented** — it always returns 0.0. Do not rely on this signal for decision-making.
- **For non-MEC methodologies** (e.g., Jobs-To-Be-Done), chain completion and depth are less meaningful because the ontology doesn't have the same linear causal structure. The `interview_progress` signal (which uses chain completion) is already deprecated for JTBD in favor of saturation signals.

---

## Node Signals: Per-Topic Exploration

**What they measure:** For each specific topic/node, how much has it been explored?

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **graph.node.exhausted** | Topic has been explored without yield | Boolean: true if the node has been focused, has had no yield for 2+ turns, and ≥66% of its last 3 responses were shallow | True = move to a different topic |
| **graph.node.exhaustion_score** | 0.0-1.0 score of exploration depth | Weighted sum of three factors: (1) `turns_since_last_yield / 10 × 0.4` + (2) `focus_streak / 5 × 0.3` + (3) `shallow_response_ratio × 0.3` | Higher (0.7+) = thoroughly explored; Lower (0.0-0.3) = fresh territory |
| **graph.node.yield_stagnation** | No new information for 3+ turns | Boolean: true when `turns_since_last_yield ≥ 3` for a previously focused node | True = time to switch topics |
| **graph.node.focus_streak** | Consecutive turns on same topic | Count of consecutive turns where this node was the focus target, reset to 0 when focus changes to a different node. Bins: `none`=0 turns, `low`=1 turn, `medium`=2-3 turns, `high`=4+ turns | none/low = fine; medium = monitor; high = consider rotating |
| **graph.node.is_current_focus** | Which topic is currently active | Boolean: true for the single node targeted by this turn's strategy | Used for strategy targeting |
| **graph.node.recency_score** | How recently topic was discussed | `turns_since_last_focus` converted to a recency score: 1.0 = just now, decaying toward 0.0 as turns pass | 1.0 = just now; 0.0 = 20+ turns ago |
| **graph.node.is_orphan** | Topic has no connections to others | Boolean: true when the node has zero incoming AND zero outgoing edges in the knowledge graph | True = opportunity to connect to other concepts |
| **graph.node.edge_count** | How connected this topic is | Sum of incoming + outgoing edges for this node | Higher = more central to the discussion |
| **graph.node.has_outgoing** | Whether topic has been explored downstream | Boolean: true when the node has at least one outgoing edge (i.e., it leads to another concept) | False = may be an unexplored leaf |
| **graph.node.novelty** | How recently a topic was first introduced | Age-based freshness score: 1.0 when a node is first created, decaying linearly to 0.0 over 5 turns. Bins: `high` ≥0.6 (created within the last 2 turns), `medium` 0.3-0.6 (3-4 turns old), `low` <0.3 (5+ turns old) | high = newly surfaced concept worth exploring; low = concept has been in the graph long enough to accumulate its own history |
| **graph.node.focus_count** | How many times a topic has been selected for focus across the whole interview | Cumulative count of turns this node was ever chosen as the focus target — never resets, unlike focus_streak. Bins: `none`=0 focuses, `low`=1-2, `medium`=3-4, `high`=5+ | none = never explored; high (5+) = this topic has been revisited many times — consider moving on permanently |
| **graph.node.canonical_novelty** | Whether this topic introduced a genuinely new theme | Compares the node's canonical slot mapping to a record of which slots have been seen before: `new` = this turn introduced a slot not seen before; `confirming` = maps to a pre-existing slot (elaboration, not exploration); `orphan` = no canonical slot assigned yet (treat as novel) | new = reward with exploration; confirming = topic is redundant unless depth is low; orphan = no deduplication data available yet |
| **technique.node.strategy_repetition** | Same strategy used consecutively on this topic | Count of consecutive turns where the same strategy was applied to this node, binned: 0=none, 1-2=low, 3-4=medium, 5+=high | High (3+) = avoid repetitive questioning |

### Understanding "Yield"

**Yield** is the system's way of measuring whether focusing on a topic produced **new structural content** in the knowledge graph. Specifically, a node "yields" when any of the following happen while it is in focus:

- A **new node** is added to the graph (a new concept was extracted)
- A **new edge** is added (a new relationship was found)
- An **existing node is modified** (a concept's attributes were updated)

Importantly, yield measures **structural novelty** — whether the graph changed — not **semantic depth** of understanding. This distinction matters in practice:

| Scenario | Response Quality | Yield? | Why |
|----------|-----------------|--------|-----|
| Short answer introduces one new concept | Low engagement, low depth | **Yes** | New node added to graph |
| Detailed answer elaborates on a known concept without new connections | High engagement, high depth | **No** | Graph unchanged — no new nodes or edges |
| Answer adds a relationship between two existing concepts | Moderate | **Yes** | New edge added to graph |

**Key implication:** A topic can have zero yield despite receiving thoughtful, detailed responses, if those responses only deepen understanding of what's already captured. Conversely, a brief tangential mention that introduces a new concept counts as yield. The `exhaustion_score` compensates for this by also weighing focus streak and response shallowness, not just yield alone.

**Moderator Use Cases:**
- **High focus_streak** → Consider switching topics for variety
- **High exhaustion_score** → Avoid re-probing this topic
- **is_orphan true** → Ask how this relates to other concepts mentioned
- **Low recency_score** → Opportunity to return to a previously discussed topic

---

## Meta Signals: Interview-Level Insights

**What they measure:** Higher-level patterns that span the entire interview.

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **meta.interview.phase** | Current stage of interview | Derived from turn count and phase boundaries in `config/interview_config.yaml` (e.g., turns 1-4 = early, 5-12 = mid, 13+ = late) | early = explore broadly; mid = build depth; late = validate and close (**Note**: Phase boundaries configured in `config/interview_config.yaml` as exploratory/focused/closing) |
| **meta.interview_progress** | How complete the interview is | `(chain_completion_ratio × 0.5) + (max_depth / ontology_levels × 0.5)` — equally weights chain coverage and depth reached (**DEPRECATED** for JTBD; use saturation signals instead) | 0.0 = just started; 1.0 = near completion |
| **meta.conversation.saturation** | Are responses drying up? | `1.0 - min(current_turn_new_nodes / best_turn_ever_new_nodes, 1.0)` — compares this turn's new surface node count against the historical peak turn | 0.0 = extracting at peak rate; 1.0 = zero extraction (regardless of quality) |
| **meta.canonical.saturation** | Are we in redundant territory? | `1.0 - min(new_canonical_concepts / new_surface_nodes, 1.0)` — ratio of new high-level themes to new surface nodes this turn | 0.0 = all new themes; 1.0 = pure elaboration on existing themes |
| **meta.node.opportunity** | What's the best action for each topic? | Classified from node state: **exhausted** = focused before + no yield for 3+ turns + ≥66% shallow recent responses; **probe_deeper** = high focus streak (4+) + current response is deep; **fresh** = default | exhausted = skip; probe_deeper = extraction opportunity; fresh = explore |

### Canonical Saturation: A Deeper Look

**Canonical slots** are the system's way of tracking high-level topics. When the respondent mentions "I drink coffee at work", "I have coffee at my desk", and "I grab coffee on the way to the office" — these surface variations get merged into a single canonical topic like "work coffee consumption".

**meta.canonical.saturation** answers: *"Have we discussed this topic enough?"*

| Value | Meaning | Moderator Action |
|-------|---------|------------------|
| 0.0 | All extraction is thematically new | Continue exploring — good territory |
| 0.3-0.6 | Mix of new and redundant themes | Normal exploration |
| 0.7-1.0 | Mostly redundant elaboration | Consider shifting to a fresh topic |

**Key distinction from conversation.saturation:**
- **conversation.saturation**: "Are they saying less overall?" (response volume)
- **canonical.saturation**: "Are they staying within the same themes?" (thematic variety)

### Conversation Saturation: The "Drying Up" Signal

**meta.conversation.saturation** measures extraction yield ratio — how many new surface concepts we're getting this turn compared to the best turn in this interview.

**Formula:** `saturation = 1.0 - min(current_delta / peak_delta, 1.0)`

| Value | Meaning | Moderator Action |
|-------|---------|------------------|
| 0.0 | At or above peak extraction | Keep going — productive |
| 0.3-0.6 | Moderate extraction | Normal |
| 0.7-1.0 | Little to no new concepts | Time to change approach or close |

**Important:** High saturation doesn't mean low engagement! A respondent can give long, thoughtful answers (high engagement) that don't yield new concepts (high saturation). This is the "elaboration without exploration" pattern.

**Key insight:** Saturation measures **extraction yield ratio**, not interview progress. A respondent can be at 1.0 (saturated) in early turns if they produce brief answers, or at 0.0 (unsaturated) in late turns if they're still revealing new concepts.

---

## Temporal Signals: Pattern Detection

**What they measure:** Patterns in questioning strategy over time.

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **temporal.strategy_repetition_count** | How often we've used the current strategy recently (normalized 0.0-1.0) | Count of the current strategy in the last 5 turns, divided by 5. Bin: `high` ≥0.75 (4-5 of the last 5 turns used the same strategy) | High (0.75+) = overuse, need variety |
| **temporal.turns_since_strategy_change** | How long since we switched strategies (normalized 0.0-1.0) | Count of consecutive turns using the same strategy from most recent, divided by 5 (capped at 1.0) | High (0.6+) = time to try something different |
| **technique.node.strategy_repetition** | How many times same strategy used consecutively on a specific topic | Count of consecutive same-strategy turns on this node, binned: 0=none, 1-2=low, 3-4=medium, 5+=high | High (3+) = avoid repetitive questioning |

**Moderator Use Cases:**
- **High repetition** → The system will automatically diversify strategies
- **Stuck on one topic** → Strategy repetition penalties will force rotation
- **Want to maintain variety** → These signals drive that automatically

---

## Signal Combinations: Reading the Room

Signals are most powerful when interpreted together. Here are common patterns:

### Pattern: "The Wandering Respondent"
- **Low depth + Low specificity + High engagement**
- Meaning: They're talking a lot but not saying much concrete
- Action: Use specific examples to ground the discussion

### Pattern: "The Fatigue Signal"
- **global_response_trend = fatigued** (4+ shallow responses)
- **conversation.saturation > 0.7**
- **canonical.saturation > 0.7**
- Meaning: They're done — responses are short and we're in redundant territory
- Action: Wrap up or take a break

### Pattern: "The Deep Well"
- **High depth + High intellectual_engagement + Low saturation**
- **canonical.saturation < 0.3**
- Meaning: We're hitting productive territory — keep digging
- Action: Use deepen/laddering strategies

### Pattern: "The Topic Monologue"
- **graph.node.focus_streak = high** (4+ on same topic)
- **graph.node.exhaustion_score rising** (0.7+)
- **saturation increasing** (0.7+)
- Meaning: We're overworking this topic
- Action: Force topic rotation

### Pattern: "The Orphan Collector"
- **High orphan_count** (>30% of nodes)
- **Low edge_count**
- Meaning: We have floating concepts without connections
- Action: Ask relationship questions: "How does X relate to Y?"

---

## For Developers: Signal Reference

When adding new signals, consider adding a moderator-facing interpretation:

```markdown
| **signal_name** | One-line moderator meaning | How it's computed (plain English) | What to look for (ranges/values) | Moderator actions |
|-----------------|---------------------------|----------------------------------|----------------------------------|-------------------|
```

The key is to answer: **"What does this tell a moderator about the interview?"** while also providing enough computation context for a moderator to reason about edge cases and trust the output.

---

## Quick Reference Card

| Signal | High Value Means... | Low Value Means... |
|--------|-------------------|-------------------|
| response_depth (comprehensive) | Rich, multi-faceted answers | surface/shallow = brief, minimal |
| specificity (0.75-1.0) | Concrete examples | Low (0.0-0.25) = vague |
| engagement (0.75-1.0) | Enthusiastic participation | Minimal effort |
| intellectual_engagement (0.75-1.0) | Shows reasoning/motivation | Bare facts only |
| global_response_trend (fatigued) | Disengaged (4+ shallow) | stable or deepening |
| valence (0.75-1.0) | Positive/enthusiastic | Negative/critical |
| graph.node_count | Broad coverage | Narrow focus |
| graph.edge_count | Well-connected concepts | Isolated concepts |
| graph.orphan_count | Missed connections | Well-integrated |
| graph.max_depth (0.75-1.0) | Deep causal chains | Surface exploration |
| conversation.saturation (0.7-1.0) | Low extraction yield | High extraction yield |
| canonical.saturation (0.7-1.0) | Redundant themes | Fresh themes |
| graph.node.exhaustion_score (0.7-1.0) | Thoroughly explored | Fresh territory |
| graph.node.focus_streak (high) | Persistent questioning | Varied focus |
| temporal.strategy_repetition_count (0.6+) | Overused strategy | Good variety |
| meta.interview_progress (0.75-1.0) | Near completion | Just started |
| meta.node.opportunity (probe_deeper) | Extraction opportunity | Not ready to probe |
| meta.node.opportunity (exhausted) | Move on | Has potential |
| meta.node.opportunity (fresh) | Ready to explore | May need attention |
| graph.canonical_edge_density (>1.0) | Topics are well-interconnected | Isolated themes, few links |
| graph.canonical_exhaustion_score (0.7+) | Most themes thoroughly explored | Fresh canonical territory remains |
| graph.node.novelty (high) | Freshly introduced concept | Well-established node in graph |
| graph.node.focus_count (high, 5+) | Topic has been revisited many times | Topic barely explored |
| graph.node.canonical_novelty (new) | Genuinely new theme introduced | Confirming/elaborating existing theme |
