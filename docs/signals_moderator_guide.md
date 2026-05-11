# Signals for Interview Moderators

A practical guide to understanding what the system's signals mean for conducting and analyzing qualitative interviews.

---

## Overview

The interview system uses **signals** to understand what is happening in the conversation. Think of signals as the system's "senses" — they detect patterns in responses, track topic exploration, and guide questioning strategy. This document translates those technical signals into **moderator-friendly interpretations**.

Signals are organized into categories based on what they measure. Each category uses a **source prefix** that tells you where the signal originates:

| Category | Prefix | Purpose | Questions It Answers |
|----------|--------|---------|---------------------|
| **Response** | `response.*` | Current utterance quality | Are they engaged? How detailed is this answer? |
| **Conversation Graph** | `convgraph.*` | Surface knowledge structure | What concepts have we covered? How are they connected? |
| **Canonical Graph** | `canongraph.*` | Deduplicated themes | What high-level topics exist after merging paraphrases? |
| **Node** | `convgraph.node.*` | Per-topic exploration | Have we exhausted this specific topic? |
| **Chain Topology** | `convgraph.node.chain.*` | Chain structure (MEC) | Where are the gaps in the "why" chains? |
| **Interview** | `interview.*` | Moderator action history | What strategies have we used? Are we repeating ourselves? |
| **Meta** | `meta.*` | Cross-source composites | Where are we in the interview? Is the conversation drying up? |

---

## Response Signals: Current Utterance Quality

**What they measure:** The quality and nature of each response, scored on normalized scales. These signals describe the **current turn only** — they are snapshots, not history.

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **response.semantic.llm.elaboration** | How developed each specific concept is in this response | LLM scores each extracted concept 1–5. The mean drives `response_depth`; individual scores are routed to the node tracker (→ `convgraph.node.llm.elaboration`). Raw score used, not normalized | surface = barely mentioned; deep = fully reasoned with examples. Watch per-node elaboration for topic-level patterns |
| **response.semantic.llm.engagement.trend** | How response quality is changing over time | Classified from recent response depths: compares the older half vs newer half of depth scores. Requires 4+ turns of history. `deepening` = quality rising, `stable` = consistent, `shallowing` = declining, `fatigued` = 4+ shallow responses | `deepening` = more engaged; `stable` = consistent; `shallowing` = declining; `fatigued` = disengaged |
| **response.semantic.llm.charge** *(per-concept)* | Emotional tone toward each specific concept | LLM scores each extracted concept 1–5, normalized to [0, 1]. Individual scores routed to node tracker (→ `convgraph.node.llm.charge`). Bins: `negative` ≤0.25, `neutral` 0.25–0.75, `positive` ≥0.75 | Negative = concern or reluctance around this topic; positive = enthusiasm or desire |
| **response.semantic.llm.certainty** | How confident the respondent sounds | LLM assigns a 1–5 score, normalized to [0, 1]. Bins: `low` ≤0.25 (hedging), `mid` 0.25–0.75 (mixed), `high` ≥0.75 (confident) | low = "maybe", "I guess"; high = unqualified statements |
| **response.semantic.llm.engagement** | Willingness to participate | LLM assigns a 1–5 score, normalized to [0, 1]. Bins: `low` ≤0.25 (minimal effort, deflection), `mid` 0.25–0.75 (adequate), `high` ≥0.75 (enthusiastic) | low = minimal effort, deflections; high = enthusiastic, extends beyond question |

**Response depth categories** (derived from the mean per-concept `elaboration` score): mean <0.125 → `surface`, <0.375 → `shallow`, <0.625 → `moderate`, ≥0.625 → `deep`. These bins appear in methodology YAML configurations.

**Moderator Use Cases:**
- **Low depth + low engagement** → Consider building rapport or closing
- **High elaboration + high certainty** → Good time to probe deeper
- **Fatigued trend** → Time to switch topics or wrap up
- **Negative charge on a node** → Handle with care, may need rapport repair before probing further

**Phase Configuration Note:** The interview phase (early/mid/late) is automatically calculated from the turn boundaries configured in `config/interview_config.yaml`. The YAML uses descriptive phase names (exploratory/focused/closing) that map to signal outputs (early/mid/late) for backward compatibility with existing methodology configurations.

---

## Conversation Graph Signals: Knowledge Structure

**What they measure:** The structure of concepts and relationships extracted from the conversation. The **conversation graph** (`convgraph`) is the surface representation — every concept and connection as extracted, before deduplication.

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **convgraph.state.node.count** | Total distinct concepts extracted | Count of active (non-superseded) nodes in the knowledge graph | Low (<5) = early exploration; High (>10) = substantial coverage |
| **convgraph.state.edge.count** | Total relationships found | Count of directed edges between nodes in the knowledge graph | Indicates how well-connected concepts are |
| **convgraph.state.node.orphan_count** | Concepts with no connections | Count of nodes that have zero incoming AND zero outgoing edges | High count = opportunities to clarify relationships |
| **convgraph.state.max_depth** | Length of longest causal chain | BFS from root nodes (nodes with no incoming edges), counting nodes in the longest path, then divided by the ontology's level count (e.g., 5 for Means-End Chain) | How deep we've gone into "why" chains |
| **convgraph.state.avg_depth** | *(Not implemented — always returns 0.0. Do not rely on this signal.)* | - | - |
| **convgraph.chain.completion.ratio** | Fraction of complete "why" chains | For each level-1 node (top-level concept), BFS searches for a path to a "terminal" node type (e.g., a value in MEC). Ratio = level-1 nodes reaching terminal / total level-1 nodes | 0 = no complete chains; 1 = all chains reach terminal values |
| **convgraph.chain.completion.has_complete** | Does at least one chain reach terminal? | Boolean companion to `completion.ratio`: true if at least one level-1 node has a complete path to a terminal node | True = interview has produced at least one full causal chain; False = no complete chains yet |
| **convgraph.chain.structure.frontier_count** | How many topics are stuck at a dead end | Count of nodes where `gap.above` is true — non-terminal nodes with no outgoing edge to a higher ontology level. Only computed for chain methodologies (MEC). Returns empty dict for non-chain methodologies | High = many chains stop short of terminal values; the ascend strategy will target these |
| **convgraph.chain.structure.ungrounded_count** | How many topics lack a foundation | Count of nodes where `gap.below` is true — nodes above the origin level with no incoming edge from a lower level. Only computed for chain methodologies (MEC). Returns empty dict for non-chain methodologies | High = many concepts float without grounding attributes; the ground strategy will target these |

**Moderator Use Cases:**
- **High orphan_count** → Ask "How are X and Y related?" to connect concepts
- **Low max_depth** → Use laddering strategies to go deeper
- **Low chain completion** → Continue probing incomplete chains
- **High node count but low depth** → Pivot from breadth to depth

### Limitations of Graph Depth and Chain Completion Signals

These signals are most meaningful for **Means-End Chain (MEC)** methodology, where the ontology has a clear layered structure (attributes → consequences → values). Be aware of the following limitations:

- **Depth is normalized against ontology levels**, not raw graph distance. For MEC with 5 levels, a raw depth of 3 gives `max_depth = 0.6`. This makes the signal methodology-relative — you cannot compare depth values across methodologies with different ontology structures.
- **Depth counts nodes, not meaningful reasoning steps.** A chain of 3 paraphrased surface nodes that map to the same canonical concept will report depth=3 even though they represent one conceptual level. Deduplication happens in the canonical graph, but depth is computed on the surface graph.
- **Chain completion is brittle with small N.** Early in an interview, there may be only 1–2 level-1 nodes, so a single complete chain makes `convgraph.chain.completion.has_complete = true` while `convgraph.chain.completion.ratio` can swing between 0.0 and 1.0 on a single turn. Treat this signal as noisy until 5+ level-1 nodes exist.
- **Chain completion depends on extraction quality.** If the LLM doesn't extract intermediate linking nodes, a chain that exists in the respondent's reasoning will appear incomplete in the graph. A low ratio may reflect extraction gaps, not shallow interviewing.
- **`convgraph.state.avg_depth` is not implemented** — it always returns 0.0. Do not rely on this signal for decision-making.
- **For non-MEC methodologies** (e.g., Jobs-To-Be-Done), chain completion and depth are less meaningful because the ontology doesn't have the same linear causal structure. Use saturation signals (`meta.saturation.*`) instead.

---

## Canonical Graph Signals: Deduplicated Themes

**What they measure:** High-level thematic structure after merging paraphrases. Where the conversation graph tracks every surface mention ("coffee at work", "coffee at my desk", "coffee on the way" as three nodes), the **canonical graph** (`canongraph`) collapses these into a single theme ("work coffee consumption").

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **canongraph.state.node.count** | Deduplicated high-level topics | Count of canonical slots — groups of surface nodes that share the same high-level theme (similarity ≥ 0.60) | Lower than `convgraph.state.node.count` because paraphrases are merged |
| **canongraph.state.edge.density** | How interconnected deduplicated topics are | Edge-to-concept ratio in the canonical graph: `canonical_edge_count / canonical_node_count`. Higher = more relationships between stable high-level concepts. **UNBOUNDED above 1.0** (dense graphs can exceed 1.0). Returns `{}` (absent) if canonical graph not initialized | Low (<0.5) = isolated topics with few links; High (>1.0) = well-connected structure where topics relate to each other. Use bare-key weights only (not `.low`/`.mid`/`.high`) |
| **canongraph.state.exhaustion** | Overall interview exhaustion, filtering out paraphrases | Average of `exhaustion` values across all canonical slots. Aggregates the same exhaustion formula as node-level scores but at the deduplicated concept level, so re-phrasing the same topic doesn't inflate freshness | 0.0 = all canonical topics still fresh; 0.7+ = most high-level themes have been thoroughly explored across the interview |

**Moderator Use Cases:**
- **Large gap between `convgraph.state.node.count` and `canongraph.state.node.count`** → The respondent is rephrasing the same ideas in different words; not necessarily a problem, but confirms breadth is narrower than it appears
- **High `canongraph.state.exhaustion`** → Most underlying themes have been thoroughly explored; time to shift to validation or close

---

## Node Signals: Per-Topic Exploration

**What they measure:** For each specific topic/node, how much has it been explored?

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **convgraph.node.exhaustion** | 0.0-1.0 score of exploration depth. Values ≥0.7 indicate the topic is effectively "exhausted" — move to a different topic. | Weighted sum of three factors: (1) `turns_since_last_yield / 10 × 0.4` + (2) `focus_streak / 5 × 0.3` + (3) `shallow_response_ratio × 0.3`, where `shallow_response_ratio` counts responses with depth category `"surface"` OR `"shallow"` | Higher (0.7+) = thoroughly explored; Lower (0.0-0.3) = fresh territory |
| **convgraph.node.yield_stagnation** | No new information for 3+ turns | Boolean: true when `turns_since_last_yield ≥ 3` for a previously focused node | True = time to switch topics |
| **convgraph.node.focus.streak** | Consecutive turns on same topic | Count of consecutive turns where this node was the focus target, reset to 0 when focus changes to a different node. Bins: `none`=0 turns, `low`=1 turn, `medium`=2-3 turns, `high`=4+ turns | none/low = fine; medium = monitor; high = consider rotating |
| **convgraph.node.is_current_focus** | Which topic is currently active | Boolean: true for the single node targeted by this turn's strategy. **NOTE: Due to pipeline stage ordering, this reflects the PREVIOUS turn's focus node, since the focus update hasn't run yet at signal-detection time.** | Used for strategy targeting (target carries forward from prior turn) |
| **convgraph.node.recency** | How recently topic was discussed | `turns_since_last_focus` converted to a recency score: 1.0 = just now, decaying toward 0.0 as turns pass | 1.0 = just now; 0.0 = 20+ turns ago |
| **convgraph.node.is_orphan** | Topic has no connections to others | Boolean: true when the node has zero incoming AND zero outgoing edges in the knowledge graph | True = opportunity to connect to other concepts |
| **convgraph.node.edge_count** | How connected this topic is | Sum of incoming + outgoing edges for this node | Higher = more central to the discussion |
| **convgraph.node.has_outgoing** | Whether topic has been explored downstream | Boolean: true when the node has at least one outgoing edge (i.e., it leads to another concept) | False = may be an unexplored leaf |
| **convgraph.node.novelty** | How recently a topic was first introduced | Age-based freshness score: 1.0 when a node is first created, decaying linearly to 0.0 over 5 turns. Bins: `high` ≥0.6 (created within the last 2 turns), `medium` 0.3-0.6 (3-4 turns old), `low` <0.3 (5+ turns old) | high = newly surfaced concept worth exploring; low = concept has been in the graph long enough to accumulate its own history |
| **convgraph.node.focus.count** | How many times a topic has been selected for focus across the whole interview | Cumulative count of turns this node was ever chosen as the focus target — never resets, unlike focus.streak. Bins: `none`=0 focuses, `low`=1-2, `medium`=3-4, `high`=5+ | none = never explored; high (5+) = this topic has been revisited many times — consider moving on permanently |
| **canongraph.node.novelty** | Whether this topic introduced a genuinely new theme | Compares the node's canonical slot mapping to a record of which slots have been seen before: `new` = this turn introduced a slot not seen before; `confirming` = maps to a pre-existing slot (elaboration, not exploration); `orphan` = no canonical slot assigned yet (treat as novel) | new = reward with exploration; confirming = topic is redundant unless depth is low; orphan = no deduplication data available yet |
| **convgraph.node.llm.elaboration** | Historical depth of elaboration for this concept across all turns it appeared | Mean of per-turn `response.semantic.llm.elaboration` scores bridged from the LLM batch detector, normalized to [0, 1]. Bins: `low` ≤0.25, `mid` 0.25-0.75, `high` ≥0.75. Returns empty if `convgraph.node.llm.has_quality_data` is false | low = concept consistently mentioned superficially; high = concept repeatedly explored with depth. Use with `has_quality_data` to gate strategies |
| **convgraph.node.llm.charge** | Historical emotional tone toward this concept across all turns | Mean of per-turn `response.semantic.llm.charge` scores bridged from the LLM batch detector, normalized to [0, 1]. Bins: `negative` ≤0.25, `neutral` 0.25-0.75, `positive` ≥0.75. Returns empty if `convgraph.node.llm.has_quality_data` is false | Persistent negative charge = this topic has emotional weight — probe carefully; positive = productive territory |
| **convgraph.node.llm.has_quality_data** | Has this topic accumulated quality tracking data yet? | Boolean gate: true if `NodeState.quality_history` has at least one elaboration or charge score. False on the first turn a node appears, since bridge data arrives at the end of the turn | False = no quality data yet — quality-dependent strategies should not fire. True = scoring and gating can use elaboration/charge history |
| **interview.focus.streak** | Same strategy used consecutively on this topic | Count of consecutive turns where the same strategy was applied to this node, binned: 0=none, 1-2=low, 3-4=medium, 5+=high | High (3+) = avoid repetitive questioning |

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

**Key implication:** A topic can have zero yield despite receiving thoughtful, detailed responses, if those responses only deepen understanding of what's already captured. Conversely, a brief tangential mention that introduces a new concept counts as yield. The `exhaustion` score compensates for this by also weighing focus streak and response shallowness, not just yield alone.

**Moderator Use Cases:**
- **High focus.streak** → Consider switching topics for variety
- **High exhaustion** → Avoid re-probing this topic
- **is_orphan true** → Ask how this relates to other concepts mentioned
- **Low recency** → Opportunity to return to a previously discussed topic

---

## Chain Topology Signals (MEC Only)

**What they measure:** For each topic, structural properties of its position within the "why" chain (attribute → consequence → value). These signals power the chain-aware strategy selection system — they determine *which nodes are eligible* for each strategy via `valid_when` gates, and then influence *scoring* within eligible nodes.

**Scope:** Only computed for chain-based methodologies (MEC). For non-chain methodologies (JTBD, CJM, CIT, Repertory Grid), these signals are absent and contribute zero to scoring.

### Per-Node Chain Position

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **convgraph.node.chain.gap.above** | Topic stops at a dead end — no path going deeper | Boolean: true if the node has no outgoing `leads_to` edge to a higher ontology level AND is not a terminal node type (e.g., not a value in MEC) | True = chain frontier — the ascend strategy targets these nodes to extend the "why" chain upward |
| **convgraph.node.chain.gap.below** | Topic floats without a foundation | Boolean: true if the node has no incoming `leads_to` edge from a lower ontology level AND is above the origin level (not an attribute) | True = ungrounded concept — the ground strategy targets these to build a foundation underneath |
| **convgraph.node.chain.level.skip** | Chain has a missing link | Boolean: true if any outgoing edge jumps more than 1 ontology level (e.g., attribute directly connected to value, skipping consequences) | True = the bridge strategy targets these to fill in intermediate steps |
| **convgraph.node.chain.branching_deficit** | Topic has fewer sibling concepts than expected | `1 - (actual_siblings / expected_siblings)`, capped at [0, 1]. Siblings = nodes at the same level sharing a parent. Expected siblings from `chain_completion.expected_branching` in methodology YAML | 0 = enough variety at this level; 1 = no siblings found (only child). The branch strategy targets high-deficit nodes |
| **convgraph.node.chain.fan_in** | How many foundational concepts feed into this topic | Integer count of distinct origin-level (attribute) nodes that have a reachable path to this node via `leads_to` edges, using BFS on reverse adjacency | Higher = this concept synthesizes multiple lower-level attributes; used as a scoring weight for ascend |
| **convgraph.node.chain.level.gap_size** | How far from the chain boundary | Integer: number of ontology levels between this node and the terminal (if `gap.above`) or origin (if `gap.below`). 0 if neither gap signal is true | Higher = longer stretch of chain to build; ascend/ground will take more turns to complete |

### Whole-Chain Properties

These signals describe per-node chain position, computed for each node and aggregated where needed:

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **convgraph.node.chain.role** | Compound per-node chain topology signal | Single traversal computes all 8 chain metrics per node (gap.above, gap.below, level.skip, branching_deficit, fan_in, level.gap_size, has_origin_level_ancestor, has_max_level_ancestor). Returned as a dict keyed by node_id. Individual extractor signals (e.g., `convgraph.node.chain.gap.above`) pull single values from this compound result | Used by strategy selection for valid_when gates and scoring |
| **convgraph.node.chain.has_origin_level_ancestor** | Does this node's chain have a concrete starting point? | Boolean: true if following reverse `leads_to` edges from this node reaches any attribute-level (origin) node via BFS | True = chain is grounded in concrete attributes; False = chain is floating without foundation. Used as a scoring modifier for ascend (boost if grounded, suppress if floating) and ground (prioritize floating chains) |
| **convgraph.node.chain.has_max_level_ancestor** | Does this node's chain reach a core value? | Boolean: true if following forward `leads_to` edges from this node reaches any terminal-value node via BFS | True = this chain already reaches a terminal value; used as a scoring modifier for branch (boost when chain is complete, indicating a productive branching point) |

**Strategy Gate Reference:**

These signals serve as `valid_when` gates for MEC's chain-aware strategies. A strategy is only scored for nodes where its gate is true:

| Strategy | valid_when Gate | What It Means |
|----------|----------------|---------------|
| ascend | `convgraph.node.chain.gap.above` | Node is a chain frontier — extend upward |
| ground | `convgraph.node.chain.gap.below` | Node is ungrounded — build foundation |
| bridge | `convgraph.node.chain.level.skip` | Edge skips levels — fill the gap |
| branch | `convgraph.node.chain.branching_deficit` | Not enough siblings — explore alternatives |
| anchor | `convgraph.node.is_orphan` | Node has no connections — give it a home |
| revitalize | *(none — conversation-level fallback)* | Always eligible |

**Moderator Use Cases:**
- **High frontier_count** → Many chains stop short of values — prioritize ascending
- **High ungrounded_count** → Many concepts lack attributes — prioritize grounding
- **level.skip on a node** → Ask about the intermediate step that was skipped
- **Low branching_deficit** → Sufficient variety at this level; can move on
- **convgraph.node.chain.has_origin_level_ancestor = false** → This concept needs grounding before extending further

---

## Interview Signals: Strategy & Focus History

**What they measure:** Patterns in questioning strategy over time. These signals track what the **interviewer** (the system) has been doing, not what the respondent said.

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **interview.strategy.self_count** | How often we've used each strategy recently (normalized 0.0-1.0) | Per-strategy dict `{name: count}` counting occurrences in the last 5 turns, normalized by 5. Resolved per-candidate during scoring | High for a given strategy = overuse of that specific strategy |
| **interview.strategy.turns_since_change** | How long since we switched strategies (normalized 0.0-1.0) | Count of consecutive turns using the same strategy from most recent, divided by 5 (capped at 1.0) | High (0.6+) = time to try something different |
| **interview.focus.streak** | Same strategy used consecutively on this topic | Count of consecutive same-strategy turns on this node, binned: 0=none, 1-2=low, 3-4=medium, 5+=high | High (3+) = avoid repetitive questioning |

**Moderator Use Cases:**
- **High repetition** → The system will automatically diversify strategies
- **Stuck on one topic** → Strategy repetition penalties will force rotation
- **Want to maintain variety** → These signals drive that automatically

---

## Meta Signals: Interview-Level Insights

**What they measure:** Higher-level patterns that span the entire interview. Meta signals are **cross-source composites** — they combine inputs from multiple signal pools (e.g., graph state + session history).

| Signal | Moderator Meaning | How It's Computed | What to Look For |
|--------|------------------|-------------------|------------------|
| **interview.phase** | Current stage of interview | Derived dynamically from turn number and `max_turns`. Uses either YAML-configured phase proportions (exploratory/focused/closing) scaled to `max_turns`, or a proportional heuristic (~10% early, last 2 turns late, rest mid) | `early` = explore broadly; `mid` = build depth; `late` = validate and close |
| **interview.phase.is_late_stage** | Is the interview in its final phase? | Boolean: true when `interview.phase` equals `"late"`. Returned as a sub-key of the `interview.phase` signal | True = interview is in validation/closing phase; False = still in exploratory or focused phase |
| **meta.saturation.conversation** | Are responses drying up? | `1.0 - min(current_turn_new_nodes / best_turn_ever_new_nodes, 1.0)` — compares this turn's new surface node count against the historical peak turn | 0.0 = extracting at peak rate; 1.0 = zero extraction (regardless of quality) |
| **meta.saturation.canonical** | Are we in redundant territory? | `1.0 - min(new_canonical_concepts / new_surface_nodes, 1.0)` — ratio of new high-level themes to new surface nodes this turn | 0.0 = all new themes; 1.0 = pure elaboration on existing themes |

### Canonical Saturation: A Deeper Look

**Canonical slots** are the system's way of tracking high-level topics. When the respondent mentions "I drink coffee at work", "I have coffee at my desk", and "I grab coffee on the way to the office" — these surface variations get merged into a single canonical topic like "work coffee consumption".

**meta.saturation.canonical** answers: *"Have we discussed this topic enough?"*

| Value | Meaning | Moderator Action |
|-------|---------|------------------|
| 0.0 | All extraction is thematically new | Continue exploring — good territory |
| 0.3-0.6 | Mix of new and redundant themes | Normal exploration |
| 0.7-1.0 | Mostly redundant elaboration | Consider shifting to a fresh topic |

**Key distinction from conversation saturation:**
- **meta.saturation.conversation**: "Are they saying less overall?" (response volume)
- **meta.saturation.canonical**: "Are they staying within the same themes?" (thematic variety)

### Conversation Saturation: The "Drying Up" Signal

**meta.saturation.conversation** measures extraction yield ratio — how many new surface concepts we're getting this turn compared to the best turn in this interview.

**Formula:** `saturation = 1.0 - min(current_delta / peak_delta, 1.0)`

| Value | Meaning | Moderator Action |
|-------|---------|------------------|
| 0.0 | At or above peak extraction | Keep going — productive |
| 0.3-0.6 | Moderate extraction | Normal |
| 0.7-1.0 | Little to no new concepts | Time to change approach or close |

**Important:** High saturation doesn't mean low engagement! A respondent can give long, thoughtful answers (high engagement) that don't yield new concepts (high saturation). This is the "elaboration without exploration" pattern.

**Key insight:** Saturation measures **extraction yield ratio**, not interview progress. A respondent can be at 1.0 (saturated) in early turns if they produce brief answers, or at 0.0 (unsaturated) in late turns if they're still revealing new concepts.

---

## Signal Combinations: Reading the Room

Signals are most powerful when interpreted together. Here are common patterns:

### Pattern: "The Wandering Respondent"
- **Low depth + Low elaboration (per-concept) + High engagement**
- Meaning: They're talking a lot but responses stay at the surface across every topic
- Action: Use specific examples to ground the discussion

### Pattern: "The Fatigue Signal"
- `response.semantic.llm.engagement.trend` = `fatigued` (4+ shallow responses)
- **meta.saturation.conversation > 0.7**
- **meta.saturation.canonical > 0.7**
- Meaning: They're done — responses are short and we're in redundant territory
- Action: Wrap up or take a break

### Pattern: "The Deep Well"
- **High depth + High elaboration (per-concept) + Low saturation**
- **meta.saturation.canonical < 0.3**
- Meaning: We're hitting productive territory — keep digging
- Action: Use deepen/laddering strategies

### Pattern: "The Topic Monologue"
- **convgraph.node.focus.streak = high** (4+ on same topic)
- **convgraph.node.exhaustion rising** (0.7+)
- **meta.saturation.conversation increasing** (0.7+)
- Meaning: We're overworking this topic
- Action: Force topic rotation

### Pattern: "The Orphan Collector"
- **High convgraph.state.node.orphan_count** (>30% of nodes)
- **Low convgraph.state.edge.count**
- Meaning: We have floating concepts without connections
- Action: Ask relationship questions: "How does X relate to Y?"

### Pattern: "The Floating Chain" (MEC)
- **High convgraph.chain.structure.frontier_count** + **High convgraph.chain.structure.ungrounded_count**
- **convgraph.node.chain.has_origin_level_ancestor = false** on multiple nodes
- Meaning: Chains are neither grounded nor reaching terminal values — the graph is wide but shallow
- Action: Prioritize grounding (build attribute foundations) before ascending to values

### Pattern: "The Near-Complete Chain" (MEC)
- **convgraph.chain.completion.has_complete = true**
- **convgraph.chain.completion.ratio rising** (0.5+)
- **Low convgraph.chain.structure.frontier_count** relative to node count
- Meaning: At least one chain is complete, others are close — shift from building to validating
- Action: Use branch strategy to explore alternatives at well-established levels

---

## For Developers: Signal Reference

When adding new signals, consider adding a moderator-facing interpretation:

```markdown
| **signal_name** | One-line moderator meaning | How it's computed (plain English) | What to look for (ranges/values) | Moderator actions |
|-----------------|---------------------------|----------------------------------|----------------------------------|-------------------|
```

The key is to answer: **"What does this tell a moderator about the interview?"** while also providing enough computation context for a moderator to reason about edge cases and trust the output.

### Namespace Design Reference

Signal names follow a consistent hierarchy:

- **`response.*`** — Signals about the current utterance (single-turn snapshots)
  - `response.semantic.llm.*` — LLM-derived meaning-layer signals
  - `response.semantic.llm.*.trend` — Session-level aggregates (e.g., `.trend` suffix for directional aggregates)
- **`convgraph.*`** — Surface knowledge graph (nodes, edges, topology)
  - `convgraph.state.*` — Global graph metrics
  - `convgraph.chain.*` — Whole-chain topology and completion
  - `convgraph.node.*` — Per-node signals
  - `convgraph.node.chain.*` — Chain-position signals for a node
  - `convgraph.node.llm.*` — LLM-derived quality signals written back to a node
  - `convgraph.node.focus.*` — Focus history (count, streak)
- **`canongraph.*`** — Canonical (deduplicated) graph
  - `canongraph.state.*` — Global canonical metrics
  - `canongraph.node.*` — Per-canonical-slot signals
- **`interview.*`** — Interview process flow (strategy history, focus tracking)
  - `interview.phase` — Interview stage (early/mid/late)
  - `interview.strategy.*` — Strategy usage patterns
  - `interview.focus.*` — (node, strategy) pair history
- **`meta.*`** — Cross-source composites (genuine combinations of multiple pools)
  - `meta.saturation.*` — Saturation signals combining graph state + history

---

## Quick Reference Card

| Signal | High Value Means... | Low Value Means... |
|--------|-------------------|-------------------|
| response.semantic.llm.elaboration (deep) | Rich, multi-faceted answers | surface/shallow = brief, minimal |
| convgraph.node.llm.elaboration (high, ≥0.75) | Concept well-developed with reasoning | surface = barely mentioned |
| convgraph.node.llm.charge (positive, ≥0.75) | Enthusiasm toward this concept | negative (≤0.25) = concern or reluctance |
| response.semantic.llm.engagement (0.75-1.0) | Enthusiastic participation | Minimal effort |
| response.semantic.llm.engagement.trend (fatigued) | Disengaged (4+ shallow) | stable or deepening |
| convgraph.state.node.count | Broad coverage | Narrow focus |
| convgraph.state.edge.count | Well-connected concepts | Isolated concepts |
| convgraph.state.node.orphan_count | Missed connections | Well-integrated |
| convgraph.state.max_depth (0.75-1.0) | Deep causal chains | Surface exploration |
| meta.saturation.conversation (0.7-1.0) | Low extraction yield | High extraction yield |
| meta.saturation.canonical (0.7-1.0) | Redundant themes | Fresh themes |
| convgraph.node.exhaustion (0.7-1.0) | Thoroughly explored | Fresh territory |
| convgraph.node.focus.streak (high) | Persistent questioning | Varied focus |
| interview.strategy.self_count (high for a strategy) | Overused strategy | Good variety |
| interview.phase.is_late_stage (true) | In validation/closing phase | Still exploring or building depth |
| canongraph.state.edge.density (>1.0) | Topics are well-interconnected | Isolated themes, few links |
| canongraph.state.exhaustion (0.7+) | Most themes thoroughly explored | Fresh canonical territory remains |
| convgraph.node.novelty (high) | Freshly introduced concept | Well-established node in graph |
| convgraph.node.focus.count (high, 5+) | Topic has been revisited many times | Topic barely explored |
| canongraph.node.novelty (new) | Genuinely new theme introduced | Confirming/elaborating existing theme |
| convgraph.node.llm.elaboration (high, ≥0.75) | Concept consistently explored with depth | surface/shallow elaboration history |
| convgraph.node.llm.charge (positive, ≥0.75) | Persistent positive tone toward concept | Persistent negative (≤0.25) = emotional friction |
| convgraph.node.llm.has_quality_data (true) | Quality tracking active for this node | No elaboration/charge data yet |
| convgraph.chain.completion.has_complete (true) | At least one full causal chain | No complete chains yet |
| convgraph.chain.structure.frontier_count (high) | Many chains stop short of values | Most chains extend toward terminals |
| convgraph.chain.structure.ungrounded_count (high) | Many concepts lack attribute foundation | Most concepts are grounded |
| convgraph.node.chain.gap.above (true) | Chain frontier — can extend upward | Chain extends or is terminal |
| convgraph.node.chain.gap.below (true) | Ungrounded concept — needs foundation | Concept has incoming edges from lower level |
| convgraph.node.chain.level.skip (true) | Missing intermediate link in chain | Adjacent ontology levels connected |
| convgraph.node.chain.branching_deficit (1.0) | Only child — no sibling concepts | Sufficient variety at this level |
| convgraph.node.chain.has_origin_level_ancestor (true) | This node's chain is grounded in attributes | Node's chain floats without foundation |
| convgraph.node.chain.has_max_level_ancestor (true) | This node's chain reaches a core value | Node's chain doesn't reach terminal |
| convgraph.node.chain.fan_in (high) | Many attribute-level concepts feed into this node | Few or no attributes reach this node |
| convgraph.node.chain.level.gap_size (high) | Large chain gap to fill (ascend/ground harder) | Small or no chain gap |
