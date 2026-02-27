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

**What they measure:** The quality and nature of each response, scored on 1-5 scales.

| Signal | Moderator Meaning | What to Look For |
|--------|------------------|------------------|
| **response_depth** | How much information is being shared | 1-2 = brief, minimal detail; 3-4 = good substance; 5 = rich, multi-faceted |
| **specificity** | How concrete vs abstract the response is | Low = vague generalities; High = specific examples, details, named entities |
| **certainty** | How confident the respondent sounds | Low = hedging, "maybe", "I guess"; High = unqualified statements |
| **emotional_valence** | Emotional tone of response | 1-2 = negative/critical; 3 = neutral; 4-5 = positive/enthusiastic |
| **intellectual_engagement** | Presence of reasoning and "why" | Low = bare facts; High = explains motivations, tradeoffs, value hierarchies |
| **engagement** | Willingness to participate | Low = minimal effort, deflections; High = enthusiastic, extends beyond question |
| **global_response_trend** | How quality is changing over time | `deepening` = more engaged; `stable` = consistent; `shallowing` = declining; `fatigued` = disengaged |

**Moderator Use Cases:**
- **Low depth + low engagement** → Consider building rapport or closing
- **High specificity + high certainty** → Good time to probe deeper
- **Fatigued trend** → Time to switch topics or wrap up
- **Negative valence** → Handle with care, may need rapport repair

---

## Graph Signals: Knowledge Structure

**What they measure:** The structure of concepts and relationships extracted from the conversation.

| Signal | Moderator Meaning | What to Look For |
|--------|------------------|------------------|
| **graph.node_count** | Total distinct concepts extracted | Low (<5) = early exploration; High (>10) = substantial coverage |
| **graph.edge_count** | Total relationships found | Indicates how well-connected concepts are |
| **graph.orphan_count** | Concepts with no connections | High count = opportunities to clarify relationships |
| **graph.max_depth** | Length of longest causal chain | How deep we've gone into "why" chains |
| **graph.avg_depth** | Average depth across all topics | Below 2 = surface-focused; 2-3 = balanced; Above 3 = consistently deep |
| **graph.chain_completion.ratio** | Fraction of complete "why" chains | 0 = no complete chains; 1 = all chains reach terminal values |
| **graph.canonical_concept_count** | Deduplicated high-level topics | Lower than node_count because paraphrases are merged |

**Moderator Use Cases:**
- **High orphan_count** → Ask "How are X and Y related?" to connect concepts
- **Low max_depth** → Use laddering strategies to go deeper
- **Low chain_completion** → Continue probing incomplete chains
- **High node_count but low depth** → Pivot from breadth to depth

---

## Node Signals: Per-Topic Exploration

**What they measure:** For each specific topic/node, how much has it been explored?

| Signal | Moderator Meaning | What to Look For |
|--------|------------------|------------------|
| **graph.node.exhausted** | Topic has been explored without yield | True = move to a different topic |
| **graph.node.exhaustion_score** | 0-1 score of exploration depth | Higher = more thoroughly explored |
| **graph.node.yield_stagnation** | No new information for 3+ turns | True = time to switch topics |
| **graph.node.focus_streak** | Consecutive turns on same topic | none/low = fine; medium = monitor; high = consider rotating |
| **graph.node.is_current_focus** | Which topic is currently active | Used for strategy targeting |
| **graph.node.recency_score** | How recently topic was discussed | 1.0 = just now; 0.0 = 20+ turns ago |
| **graph.node.is_orphan** | Topic has no connections to others | True = opportunity to connect to other concepts |
| **graph.node.edge_count** | How connected this topic is | Higher = more central to the discussion |
| **graph.node.has_outgoing**** | Whether topic has been explored downstream | False = may be an unexplored leaf |

**Moderator Use Cases:**
- **High focus_streak** → Consider switching topics for variety
- **High exhaustion_score** → Avoid re-probing this topic
- **is_orphan true** → Ask how this relates to other concepts mentioned
- **Low recency_score** → Opportunity to return to a previously discussed topic

---

## Meta Signals: Interview-Level Insights

**What they measure:** Higher-level patterns that span the entire interview.

| Signal | Moderator Meaning | What to Look For |
|--------|------------------|------------------|
| **meta.interview.phase** | Current stage of interview | `early` = explore broadly; `mid` = build depth; `late` = validate and close |
| **meta.interview_progress** | How complete the interview is | 0 = just started; 1 = near completion (based on chains and depth) |
| **meta.conversation.saturation** | Are responses drying up? | 0 = extracting at peak rate; 1 = zero extraction (regardless of quality) |
| **meta.canonical.saturation** | Are we in redundant territory? | 0 = all new themes; 1 = pure elaboration on existing themes |
| **meta.node.opportunity** | What's the best action for each topic? | `exhausted` = skip; `probe_deeper` = extraction opportunity; `fresh` = explore |

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

**meta.conversation.saturation** measures extraction yield ratio — how many new concepts we're getting compared to the best turn in this interview.

| Value | Meaning | Moderator Action |
|-------|---------|------------------|
| 0.0 | At or above peak extraction | Keep going — productive |
| 0.3-0.6 | Moderate extraction | Normal |
| 0.7-1.0 | Little to no new concepts | Time to change approach or close |

**Important:** High saturation doesn't mean low engagement! A respondent can give long, thoughtful answers (high engagement) that don't yield new concepts (high saturation). This is the "elaboration without exploration" pattern.

---

## Temporal Signals: Pattern Detection

**What they measure:** Patterns in questioning strategy over time.

| Signal | Moderator Meaning | What to Look For |
|--------|------------------|------------------|
| **temporal.strategy_repetition_count** | How often we've used the current strategy recently | High (3+) = overuse, need variety |
| **temporal.turns_since_strategy_change** | How long since we switched strategies | High (3+) = time to try something different |
| **technique.node.strategy_repetition** | How many times same strategy used on a specific topic | high = 5+ consecutive — avoid repetitive questioning |

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
- **focus_streak = high** (4+ on same topic)
- **exhaustion_score rising**
- **saturation increasing**
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
| **signal_name** | One-line moderator meaning | What to look for (ranges/values) | Moderator actions |
|-----------------|---------------------------|----------------------------------|-------------------|
```

The key is to answer: **"What does this tell a moderator about the interview?"** rather than **"How is this calculated?"**

---

## Quick Reference Card

| Signal | High Value Means... | Low Value Means... |
|--------|-------------------|-------------------|
| response_depth | Rich, multi-faceted answers | Brief, minimal detail |
| specificity | Concrete examples | Vague generalities |
| engagement | Enthusiastic participation | Minimal effort |
| intellectual_engagement | Shows reasoning/motivation | Bare facts only |
| global_response_trend (fatigued) | Disengaged (4+ shallow) | Stable or deepening |
| graph.node_count | Broad coverage | Narrow focus |
| graph.edge_count | Well-connected concepts | Isolated concepts |
| graph.orphan_count | Missed connections | Well-integrated |
| graph.max_depth | Deep causal chains | Surface exploration |
| conversation.saturation | Low extraction yield | High extraction yield |
| canonical.saturation | Redundant themes | Fresh themes |
| node.exhaustion_score | Thoroughly explored | Fresh territory |
| node.focus_streak | Persistent questioning | Varied focus |
| strategy_repetition | Overused strategy | Good variety |
| interview_progress | Near completion | Just started |
| node.opportunity (probe_deeper) | Extraction opportunity | Not ready to probe |
| node.opportunity (exhausted) | Move on | Has potential |
| node.opportunity (fresh) | Ready to explore | May need attention |
